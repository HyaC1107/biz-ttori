"""biz-ttori AI 회사 — 이벤트 로그 헬퍼 (SSOT: company/events.jsonl).

스키마: tool-spec/biz-ttori/spec.md §1 참조.
append-only JSONL. watcher 데몬·클또리 세션·spawn 큐가 공유.

CLI:
  python3 events.py append --type mail.in --actor watcher --dept ops --summary "..." [--task-id T-0001] [--project biz-ttori] [--refs a,b] [--approval]
  python3 events.py tail [N]

project 필드 (2026-07-12, 스프린트 "프로젝트 축"):
  값은 company/projects.json 에 등록된 프로젝트 id 만 허용 (유령 프로젝트 방지 — PM 결정).
  기존 이벤트는 백필하지 않는다 — 필드 없음 = 미지정("?")으로 읽는다 (추측 백필 금지).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

def _find_root() -> Path:
    """레포 루트를 마커(CLAUDE.md)로 찾는다.

    ⚠️ parent.parent.parent 로 깊이를 세면 폴더를 한 번 옮길 때마다 전부 깨진다.
       (실제로 biz-ttori/harness 분리 때 7개 모듈이 동시에 깨졌다.)
    """
    for p in Path(__file__).resolve().parents:
        if (p / "CLAUDE.md").exists():
            return p
    return Path(__file__).resolve().parents[3]


ROOT = _find_root()
EVENTS_PATH = ROOT / "company" / "events.jsonl"
PROJECTS_PATH = ROOT / "company" / "projects.json"   # 레지스트리 경로 정본 — serve.py도 이걸 import
KST = timezone(timedelta(hours=9))

VALID_TYPES = {
    "project.genesis",
    "task.created", "task.assigned",
    "bot.spawned", "bot.done", "bot.failed",
    "mail.in", "mail.out",
    "approval.requested", "approval.granted", "approval.rejected",
    "report.filed",
    "org.changed",       # 봇 추가/수정/삭제 (현황판 API)
    "project.updated",   # 프로젝트 상태/메모 수정 (현황판 API)
    # Debate 패턴 (2026-07-11): task_id=D-nnnn 공유, started의 refs=참여 봇 이름 목록
    "debate.started",    # actor=발제자, summary=주제
    "debate.statement",  # actor=발언자, summary=발언 요지
    "debate.concluded",  # actor=중재자(클또리), summary=결론
    # 검증관 게이트 (2026-07-12): 결재 올리기 직전 자동 검증. audit.py 참조
    "audit.passed",      # actor=검증관, 결함 없음 → approval.requested 로 이어짐
    "audit.failed",      # actor=검증관, blocker 있음 → 결재 차단 (PM에게 안 올라감)
}


def registry_projects() -> set[str]:
    """company/projects.json 에 등록된 프로젝트 id 집합.

    매번 새로 읽는다 — serve.py 같은 장수 프로세스에서 캐시하면
    새로 등록한 프로젝트가 재시작 전까지 거부된다.
    레지스트리가 없거나 깨졌으면 빈 set — 단 **무음이면 안 된다**(검증이 조용히
    꺼진 채 유령 project가 append-only 로그에 영구히 남는다) → stderr 경고.
    """
    try:
        data = json.loads(PROJECTS_PATH.read_text(encoding="utf-8"))
        return {p["id"] for p in data.get("projects", []) if p.get("id")}
    except (OSError, json.JSONDecodeError, TypeError) as e:
        print(f"⚠️ projects.json 못 읽음({e.__class__.__name__}) — project 검증 생략됨",
              file=sys.stderr)
        return set()


def validate_project(project: str | None) -> None:
    """project 값 검증 단일 정본 — 미등록 id면 ValueError.

    append_event 와 spawn_queue.claim 이 같이 쓴다. 두 벌로 복사하면
    거부 기준이 어긋난다(검수 지적 2026-07-12).
    """
    if not project:
        return
    known = registry_projects()
    if known and project not in known:
        raise ValueError(f"unknown project: {project} — projects.json에 먼저 등록할 것 "
                         f"(등록됨: {', '.join(sorted(known))})")


def append_event(type: str, actor: str, dept: str, summary: str,
                 task_id: str | None = None, refs: list[str] | None = None,
                 requires_approval: bool = False,
                 project: str | None = None) -> dict:
    """이벤트 1건 append. 성공 시 이벤트 dict 반환.

    project 는 projects.json 등록 id 만 허용 — 아니면 ValueError (오타 = 유령 프로젝트 원천 차단).
    """
    assert type in VALID_TYPES, f"unknown event type: {type}"
    validate_project(project)
    
    # 🚨 위험 행동 블랙리스트 패턴 감지 및 결재 요구 강제 (Phase 0 가드레일)
    import re
    danger_patterns = [r"git\s+push", r"rm\s+-rf", r"\bdeploy\b", r"\bpublish\b", r"\bdelete\b", r"\bdrop\b"]
    for pat in danger_patterns:
        if re.search(pat, summary, re.IGNORECASE):
            requires_approval = True
            print(f"⚠️ 위험 행동 감지: '{summary}' — 결재 승인 강제 적용 (requires_approval=True)")
            break
            
    ev = {
        "ts": datetime.now(KST).isoformat(timespec="seconds"),
        "type": type, "actor": actor, "dept": dept,
        "summary": summary[:1000],
    }
    if project:
        ev["project"] = project
    if task_id:
        ev["task_id"] = task_id
    if refs:
        ev["refs"] = refs
    if requires_approval:
        ev["requires_approval"] = True
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return ev


def read_events(last_n: int | None = None) -> list[dict]:
    """이벤트 전체(또는 마지막 N개) 읽기. 깨진 줄은 건너뜀."""
    if not EVENTS_PATH.exists():
        return []
    out = []
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out[-last_n:] if last_n else out


def _cli():
    args = sys.argv[1:]
    if not args or args[0] not in ("append", "tail"):
        print(__doc__)
        sys.exit(1)
    if args[0] == "tail":
        n = int(args[1]) if len(args) > 1 else 10
        for ev in read_events(n):
            print(json.dumps(ev, ensure_ascii=False))
        return
    # append
    kw = {"requires_approval": False}
    it = iter(args[1:])
    for a in it:
        if a == "--approval":
            kw["requires_approval"] = True
        elif a.startswith("--"):
            key = a[2:].replace("-", "_")
            val = next(it)
            if key == "refs":
                val = val.split(",")
            kw[key] = val
    ev = append_event(**kw)
    print(json.dumps(ev, ensure_ascii=False))


if __name__ == "__main__":
    _cli()
