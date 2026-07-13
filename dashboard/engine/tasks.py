"""biz-ttori AI 회사 — 태스크 상태 집계 (SSOT).

events.jsonl 의 이벤트를 task_id 로 묶어 **태스크 라이프사이클 상태**를 도출한다.
상태 판정을 파이썬 한 곳에 두는 이유: serve.py(`/api/tasks`)와 briefing.py 가
같은 기준을 써야 하는데, JS/Python 두 벌로 나뉘면 어긋난다.

⚠️ 이벤트가 없는 단계는 **건너뛴 것으로 처리**한다(현실 반영).
   실제로 task.created 없이 report.filed 만 있는 태스크가 존재한다(2026-07-11 확인).
   이런 결함을 감추지 않고 `anomaly` 로 드러낸다 — 관전용 대시보드의 가치는 정직함에 있다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from events import read_events

KST = timezone(timedelta(hours=9))

# 진행 단계 — 뒤로 갈수록 진척. 이벤트가 오면 그 단계 이상으로 올린다.
STAGE_ORDER = ["created", "running", "reported", "awaiting_approval", "approved", "done"]

EVENT_STAGE = {
    "task.created":       "created",
    "task.assigned":      "created",
    "bot.spawned":        "running",
    "report.filed":       "reported",
    "approval.requested": "awaiting_approval",
    "approval.granted":   "approved",
    "bot.done":           "done",
}

STATE_META = {
    "created":           {"label": "대기",     "icon": "📌", "color": "#8aa0c8"},
    "running":           {"label": "진행중",   "icon": "🚀", "color": "#00E5FF"},
    "reported":          {"label": "보고됨",   "icon": "📄", "color": "#a78bfa"},
    "awaiting_approval": {"label": "결재대기", "icon": "📋", "color": "#FFD700"},
    "approved":          {"label": "승인",     "icon": "✅", "color": "#28d17c"},
    "done":              {"label": "완료",     "icon": "🏁", "color": "#28d17c"},
    "failed":            {"label": "실패",     "icon": "❌", "color": "#ff5470"},
    "rejected":          {"label": "반려",     "icon": "👤↩", "color": "#ff8a3d"},
    "debate":            {"label": "회의",     "icon": "🏛️", "color": "#00E5FF"},
    "debate_done":       {"label": "회의종료", "icon": "🤝", "color": "#28d17c"},
}

# 종료 상태 — stuck 판정 대상에서 제외
TERMINAL = {"done", "approved", "failed", "rejected", "debate_done"}

STUCK_HOURS = 24   # 이 시간 넘게 진척 없으면 정체로 표시


def _parse_ts(ts: str) -> Optional[datetime]:
    """ISO8601 → aware datetime. tz 없는 값이 한 줄만 섞여도 `now - upd`가
    TypeError로 터져 /api/tasks 전체가 죽으므로 KST로 보정한다."""
    try:
        dt = datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None
    return dt.replace(tzinfo=KST) if dt.tzinfo is None else dt


def _stage_rank(stage: str) -> int:
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return -1


# 한 번 들어가면 일반 이벤트로 덮이지 않는 상태.
# (debate 상태의 rank는 -1이라, 잠그지 않으면 report.filed 같은 이벤트에 덮여버린다)
LOCKED_STATES = {"failed", "rejected", "debate", "debate_done"}


def build_tasks(now: Optional[datetime] = None) -> list[dict[str, Any]]:
    """task_id 별 상태 집계. 최근 갱신 순."""
    now = now or datetime.now(KST)
    tasks: dict[str, dict] = {}

    for e in read_events():
        tid = e.get("task_id")
        if not tid:
            continue
        t = tasks.setdefault(tid, {
            "task_id": tid,
            "dept": e.get("dept"),
            "actor": e.get("actor"),
            "project": None,
            "_projects": set(),   # 내부용 — 불일치 감지 (응답에서 제거)
            "title": None,
            "state": None,
            "created_at": None,
            "updated_at": None,
            "events": [],
            "is_debate": tid.startswith("D-"),
            "participants": [],
            "_upd_dt": None,      # 내부용 (응답에서 제거)
        })

        etype = e.get("type") or ""
        ts = e.get("ts")
        t["events"].append({"ts": ts, "type": etype, "actor": e.get("actor"),
                            "summary": e.get("summary"), "dept": e.get("dept")})
        t["dept"] = e.get("dept") or t["dept"]
        # project = 이벤트 중 첫 명시값 (기존 이벤트엔 필드 없음 → None 유지, 추측 금지).
        # 단 서로 다른 값이 섞이면 감추지 않고 anomaly로 노출한다 (아래).
        if e.get("project"):
            t["project"] = t["project"] or e["project"]
            t["_projects"].add(e["project"])

        # updated_at = 이벤트 중 **가장 늦은 시각**. 파일 순서에 의존하면(append 순서가
        # 어긋나거나 tz offset이 섞이면) idle/정체 판정이 틀어진다 → 파싱해서 max.
        dt = _parse_ts(ts)
        if dt and (t["_upd_dt"] is None or dt > t["_upd_dt"]):
            t["_upd_dt"] = dt
            t["updated_at"] = ts
        elif t["updated_at"] is None:
            t["updated_at"] = ts

        # 제목 = task.created 의 summary 우선 (없으면 첫 유의미 summary)
        if e.get("summary"):
            if etype in ("task.created", "task.assigned"):
                t["title"] = e["summary"]
            elif t["title"] is None:
                t["title"] = e["summary"]

        # ── Debate 는 별도 라이프사이클 ──
        if etype == "debate.started":
            t["created_at"] = ts
            t["state"] = "debate"
            t["actor"] = e.get("actor")
            t["participants"] = list(e.get("refs") or [])
            continue
        if etype == "debate.concluded":
            t["state"] = "debate_done"
            continue
        if etype == "debate.statement":
            continue

        # ── 일반 태스크 ──
        if etype in ("task.created", "task.assigned"):
            t["created_at"] = t["created_at"] or ts
        if etype == "bot.failed":
            t["state"] = "failed"
            continue
        if etype == "approval.rejected":
            t["state"] = "rejected"
            continue

        # 잠금 상태(실패/반려/회의)는 일반 이벤트로 덮지 않는다.
        # ※ bot.failed 후 재시도 성공을 상태에 반영할지는 스펙 미결 — 현재는 실패 유지(sticky).
        if t["state"] in LOCKED_STATES:
            continue

        stage = EVENT_STAGE.get(etype)
        # 단계는 뒤로 가지 않는다 (단조 증가)
        if stage and (t["state"] is None or _stage_rank(stage) > _stage_rank(t["state"])):
            t["state"] = stage

    out = []
    for t in tasks.values():
        t["state"] = t["state"] or "created"
        meta = STATE_META.get(t["state"], STATE_META["created"])
        t["state_label"] = meta["label"]
        t["state_icon"] = meta["icon"]
        t["state_color"] = meta["color"]   # CSS 값 컨텍스트로 들어감 — STATE_META 상수만 허용
        t["n_events"] = len(t["events"])
        # ★ 종료 여부도 서버가 판정한다 — JS가 종료 상태 목록을 하드코딩하지 않게(SSOT)
        t["is_open"] = t["state"] not in TERMINAL

        # ⚠️ 결함 노출 (감추지 않는다)
        anomaly = []
        if not t["is_debate"] and not t["created_at"]:
            anomaly.append("생성 이벤트 없음 (task.created 누락)")
        projs = t.pop("_projects")
        if len(projs) > 1:
            anomaly.append(f"프로젝트 불일치 ({', '.join(sorted(projs))})")

        upd = t.pop("_upd_dt", None)
        idle_h = round((now - upd).total_seconds() / 3600, 1) if upd else None
        t["idle_hours"] = idle_h

        if t["is_open"] and idle_h is not None and idle_h >= STUCK_HOURS:
            anomaly.append(f"{int(idle_h)}시간 무진척 (정체)")

        t["anomaly"] = anomaly
        t["stuck"] = bool(anomaly)
        out.append((upd, t))

    # 최근 갱신 순 — 문자열이 아니라 파싱된 시각으로 정렬(tz offset 혼재 대응)
    out.sort(key=lambda x: (x[0] is not None, x[0]), reverse=True)
    return [t for _, t in out]


def summarize(tasks: list[dict]) -> dict[str, Any]:
    """부서별·상태별 집계 — 대시보드 헤더용."""
    by_state: dict[str, int] = {}
    by_dept: dict[str, int] = {}
    by_project: dict[str, int] = {}
    for t in tasks:
        by_state[t["state"]] = by_state.get(t["state"], 0) + 1
        d = t.get("dept") or "?"
        by_dept[d] = by_dept.get(d, 0) + 1
        p = t.get("project") or "?"   # 필드 없는 과거 이벤트 = 미지정
        by_project[p] = by_project.get(p, 0) + 1
    return {
        "total": len(tasks),
        "by_state": by_state,
        "by_dept": by_dept,
        "by_project": by_project,
        "stuck": sum(1 for t in tasks if t["stuck"]),
        "open": sum(1 for t in tasks if t["is_open"]),
    }


if __name__ == "__main__":
    import json as _j
    ts = build_tasks()
    print(_j.dumps({"summary": summarize(ts), "tasks": ts}, ensure_ascii=False, indent=2))
