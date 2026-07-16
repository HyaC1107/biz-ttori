"""봇별 '남은 체력' — 구독 한도 잔량 + 활동량.

타겟 사용자가 **AI 구독자**라, 각 봇이 얼마나 더 일할 수 있는지(=남은 쿼터)가 핵심 지표다.
게임 HP바처럼 보여주되 **없는 데이터를 지어내지 않는다.**

## 데이터 출처 (2026-07-11 조사)

| 봇 | 남은 한도 | 근거 |
|----|-----------|------|
| 👑 클또리 (Claude Code) | ✅ **실측** | Claude Code가 statusLine 훅 stdin으로 `rate_limits.five_hour/seven_day.used_percentage`를 준다. `~/.claude/statusline.py`가 `~/.claude/.rate-limits.json`에 스냅샷 기록. |
| ✅ 챗또리 (Codex) | ✅ **실측** | 세션 로그(`~/.codex/sessions/**/rollout-*.jsonl`)에 API가 내려준 `rate_limits.primary{used_percent, window_minutes, resets_at}`가 그대로 남는다. |
| 🔍 젬또리 (Antigravity) | 🟡 **자기 보고** | 로컬에 쿼터가 안 남는다(대화 DB가 protobuf, CLI에 usage 서브커맨드 없음). **하지만 젬또리 자신은 `/usage`로 자기 잔량을 안다.** → 봇이 직접 보고하게 한다. |

## 핵심 설계: 봇이 자기 체력을 직접 보고한다

클또리가 남의 쿼터를 **긁어오려는 게 애초에 이상하다.** 잔량은 그 봇만 아는 정보다.
(실제로 `agy -p "/usage"` 는 대화형 전용이라 안 먹는다 — 긁는 길이 막혀 있다.)

→ **어느 봇이든 자기 체력을 보고할 수 있는 경로**를 연다:

```bash
python3 tool-spec/biz-ttori/engine/health.py report \
    --bot 젬또리 --remaining 62 --window "5시간" --resets "07-12 04:00" --note "/usage 기준"
```

보고된 값은 `company/bot_health.json`에 쌓이고, 대시보드가 **'자기 보고'로 명시**해 표시한다
(자동 실측과 구분 — 언제 보고된 값인지도 함께 보여준다).

→ 자동 실측도 없고 자기 보고도 없는 봇은 **가짜 게이지를 그리지 않는다.** '측정 불가'로 둔다.
"""
from __future__ import annotations

import glob
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

KST = timezone(timedelta(hours=9))
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

CLAUDE_SNAP = Path.home() / ".claude" / ".rate-limits.json"
CODEX_SESSIONS = os.path.expanduser("~/.codex/sessions/**/*.jsonl")
AGY_HISTORY = Path.home() / ".gemini" / "antigravity-cli" / "history.jsonl"
SELF_REPORT = ROOT / "company" / "bot_health.json"              # 봇이 직접 보고한 체력

STALE_MIN = 30          # 스냅샷이 이보다 오래되면 '오래된 값'으로 표시
CODEX_SCAN_FILES = 8    # 최근 세션 몇 개까지 훑을지 (전체 스캔 방지)
SELF_STALE_HOURS = 12   # 자기 보고가 이보다 오래되면 '오래된 보고'로 표시


# ── 자기 보고 (봇이 직접 자기 잔량을 알려준다) ──────────────────
def load_self_reports() -> dict[str, Any]:
    if not SELF_REPORT.exists():
        return {}
    try:
        return json.loads(SELF_REPORT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def report(bot: str, remaining: float, window: str = "",
           resets: str = "", note: str = "", windows: list[dict] = None) -> dict[str, Any]:
    """봇이 자기 체력을 보고한다. (긁어오는 게 아니라 **본인이 말해주는** 값)"""
    SELF_REPORT.parent.mkdir(parents=True, exist_ok=True)
    data = load_self_reports()
    rec = {
        "note": note or None,
        "reported_at": datetime.now(KST).isoformat(timespec="seconds"),
    }
    if windows:
        rec["windows"] = windows
        if len(windows) > 0:
            rec["remaining_pct"] = windows[0]["remaining_pct"]
            rec["window"] = windows[0]["label"]
            rec["resets_at"] = windows[0].get("resets_at")
    else:
        rem_pct = max(0, min(100, round(float(remaining))))
        rec["remaining_pct"] = rem_pct
        rec["window"] = window or "?"
        rec["resets_at"] = resets or None

    data[bot] = rec
    tmp = SELF_REPORT.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SELF_REPORT)
    return rec


def _self_reported(bot: str) -> Optional[dict[str, Any]]:
    rec = load_self_reports().get(bot)
    if not rec:
        return None
    try:
        age_h = (datetime.now(KST) - datetime.fromisoformat(rec["reported_at"])).total_seconds() / 3600
    except (KeyError, ValueError):
        age_h = None
        
    stale = bool(age_h is not None and age_h > SELF_STALE_HOURS)
    result = {
        "source": "self",
        "age_hours": round(age_h, 1) if age_h is not None else None,
        "stale": stale,
        "note": rec.get("note"),
        "reported_at": rec.get("reported_at"),
    }
    
    if "windows" in rec:
        windows_list = []
        for w in rec["windows"]:
            rem = w["remaining_pct"]
            windows_list.append({
                "label": w["label"],
                "remaining_pct": rem,
                "used_pct": 100 - rem,
                "level": _level(rem),
                "resets_at": w.get("resets_at")
            })
        result["windows"] = windows_list
        if len(windows_list) > 0:
            result["window"] = windows_list[0]
    else:
        rem = rec.get("remaining_pct", 100)
        w = {
            "label": rec.get("window") or "?",
            "remaining_pct": rem,
            "used_pct": 100 - rem,
            "level": _level(rem),
            "resets_at": rec.get("resets_at"),
        }
        result["window"] = w
        result["windows"] = [w]
        
    return result


def _level(remaining: float) -> str:
    return "good" if remaining > 50 else ("warn" if remaining >= 20 else "danger")


def _fmt_reset(epoch: Optional[int]) -> Optional[str]:
    if not epoch:
        return None
    return datetime.fromtimestamp(epoch, KST).strftime("%m-%d %H:%M")


# ── 클또리 ──────────────────────────────────────────────────────
def _claude() -> dict[str, Any]:
    h: dict[str, Any] = {"bot": "클또리", "icon": "👑", "cli": "Claude Code",
                         "measurable": True, "windows": [], "note": None}
    if not CLAUDE_SNAP.exists():
        h.update(measurable=False,
                 note="스냅샷 없음 — Claude Code 세션이 한 번 돌면 기록된다")
        return h
    try:
        snap = json.loads(CLAUDE_SNAP.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        h.update(measurable=False, note="스냅샷 읽기 실패")
        return h

    age = (time.time() - float(snap.get("ts", 0))) / 60
    h["age_min"] = round(age, 1)
    h["model"] = snap.get("model")
    h["context_used_pct"] = snap.get("context_used_pct")

    for key, label in (("five_hour", "5시간"), ("seven_day", "7일")):
        used = snap.get(key)
        if used is None:
            continue
        rem = max(0, min(100, 100 - int(used)))
        h["windows"].append({"label": label, "remaining_pct": rem,
                             "used_pct": int(used), "level": _level(rem),
                             "resets_at": None})
    if not h["windows"]:
        h.update(measurable=False, note="rate_limits 미제공 (플랜에 따라 없을 수 있음)")
    elif age > STALE_MIN:
        h["note"] = f"{int(age)}분 전 값 — 세션이 안 돌면 갱신되지 않는다"
    return h


# ── 챗또리 ──────────────────────────────────────────────────────
def _find_rate_limits(obj: Any) -> Optional[dict]:
    if isinstance(obj, dict):
        if "rate_limits" in obj:
            return obj["rate_limits"]
        for v in obj.values():
            r = _find_rate_limits(v)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_rate_limits(v)
            if r:
                return r
    return None


def _codex() -> dict[str, Any]:
    h: dict[str, Any] = {"bot": "챗또리", "icon": "✅", "cli": "Codex",
                         "measurable": True, "windows": [], "note": None}
    files = sorted(glob.glob(CODEX_SESSIONS, recursive=True),
                   key=os.path.getmtime, reverse=True)[:CODEX_SCAN_FILES]
    latest = None
    latest_mtime = 0.0
    for f in files:
        best = None
        try:
            for line in open(f, encoding="utf-8", errors="replace"):
                if '"rate_limits"' not in line:
                    continue
                try:
                    rl = _find_rate_limits(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if rl and rl.get("primary"):
                    best = rl          # 파일 내 마지막 유효값
        except OSError:
            continue
        if best:
            latest, latest_mtime = best, os.path.getmtime(f)
            break                       # 최신 파일부터 봤으니 첫 히트가 최신

    if not latest:
        h.update(measurable=False,
                 note="세션 로그에 한도 정보 없음 — codex를 한 번 실행하면 기록된다")
        return h

    h["plan"] = latest.get("plan_type")
    h["age_min"] = round((time.time() - latest_mtime) / 60, 1)

    for key, name in (("primary", "주 한도"), ("secondary", "보조 한도")):
        w = latest.get(key)
        if not w or w.get("used_percent") is None:
            continue
        rem = max(0, min(100, 100 - float(w["used_percent"])))
        mins = w.get("window_minutes") or 0
        label = f"{mins // 1440}일" if mins >= 1440 else f"{mins // 60}시간"
        h["windows"].append({
            "label": label,
            "remaining_pct": round(rem),
            "used_pct": round(float(w["used_percent"])),
            "level": _level(rem),
            "resets_at": _fmt_reset(w.get("resets_at")),
        })

    if not h["windows"]:
        h.update(measurable=False, note="한도 필드가 비어 있음")
    elif h["windows"][0]["remaining_pct"] == 0:
        r = h["windows"][0]["resets_at"]
        h["note"] = f"⛔ 한도 소진 — {r} 복구 예정" if r else "⛔ 한도 소진"
    return h


# ── 젬또리 ──────────────────────────────────────────────────────
def _agy() -> dict[str, Any]:
    """로컬엔 쿼터가 안 남는다 → **젬또리 본인이 보고한 값**을 쓴다(`/usage` 기준).

    긁어올 수 없다고 포기하지 않는다. 잔량은 그 봇만 아는 정보이니 **본인에게 물어본다.**
    """
    h: dict[str, Any] = {
        "bot": "젬또리", "icon": "🔍", "cli": "Antigravity",
        "measurable": False,          # 자기 보고가 있으면 아래에서 True로
        "windows": [],
        "note": "로컬에 쿼터 기록이 없다 — 젬또리가 `/usage`로 직접 보고해야 표시된다",
    }

    # ★ 자기 보고 우선
    sr = _self_reported("젬또리")
    if sr:
        h["measurable"] = True
        h["source"] = "self"
        h["windows"] = sr["windows"]
        h["reported_at"] = sr["reported_at"]
        note = f"본인 보고 ({sr['reported_at'][5:16].replace('T',' ')})"
        if sr.get("note"):
            note += f" · {sr['note']}"
        if sr["stale"]:
            note += f" · ⚠️ {int(sr['age_hours'])}시간 전 값"
        h["note"] = note

    if not AGY_HISTORY.exists():
        return h

    today = datetime.now(KST).date()
    calls_today, last_ts = 0, None
    try:
        for line in AGY_HISTORY.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = d.get("timestamp")
            if not ts:
                continue
            dt = datetime.fromtimestamp(ts / 1000, KST)
            if dt.date() == today:
                calls_today += 1
            if last_ts is None or ts > last_ts:
                last_ts = ts
    except OSError:
        return h

    h["activity"] = {
        "calls_today": calls_today,
        "last_call": datetime.fromtimestamp(last_ts / 1000, KST).strftime("%m-%d %H:%M")
        if last_ts else None,
    }
    return h


def bots_health() -> dict[str, Any]:
    # 챗또리(_codex)는 현재 미사용(보류)이라 체력판에서 제외한다. 재도입 시 _codex() 다시 추가.
    bots = [_claude(), _agy()]

    # 자동 실측이 안 되는 봇은 **자기 보고**로 폴백 (어느 봇이든 가능)
    for b in bots:
        if b["measurable"] or b.get("source") == "self":
            continue
        sr = _self_reported(b["bot"])
        if not sr:
            continue
        b["measurable"] = True
        b["source"] = "self"
        b["windows"] = sr["windows"]
        b["reported_at"] = sr["reported_at"]
        note = f"본인 보고 ({sr['reported_at'][5:16].replace('T', ' ')})"
        if sr.get("note"):
            note += f" · {sr['note']}"
        if sr["stale"]:
            note += f" · ⚠️ {int(sr['age_hours'])}시간 전 값"
        b["note"] = note

    return {
        "bots": bots,
        "source_note": "한도는 ①CLI가 실제로 노출하거나 ②봇이 직접 보고한 경우에만 표시한다. "
                       "둘 다 없으면 가짜 게이지 대신 '측정 불가'로 둔다.",
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="봇 체력 — 조회 / 자기 보고")
    sub = ap.add_subparsers(dest="cmd")

    r = sub.add_parser("report", help="봇이 자기 체력을 보고한다")
    r.add_argument("--bot", required=True, help="봇 이름 (예: 젬또리)")
    r.add_argument("--remaining", type=float, required=True, help="남은 %% (0~100)")
    r.add_argument("--window", default="", help="한도 창 (예: 5시간, 일일)")
    r.add_argument("--resets", default="", help="리셋 시각 (예: 07-12 04:00)")
    r.add_argument("--note", default="", help="비고 (예: /usage 기준)")
    r.add_argument("--windows-json", default="", help="여러 한도 창 정보의 JSON string (예: '[{\"label\": \"5시간\", \"remaining_pct\": 99}]')")

    a = ap.parse_args()
    if a.cmd == "report":
        windows_list = None
        if a.windows_json:
            try:
                windows_list = json.loads(a.windows_json)
            except Exception as e:
                print(f"❌ JSON 파싱 실패: {e}", file=sys.stderr)
                sys.exit(1)
        rec = report(a.bot, a.remaining, a.window, a.resets, a.note, windows=windows_list)
        print(f"✅ {a.bot} 체력 보고 접수: {rec.get('remaining_pct')}% 남음"
              f" ({rec.get('window')})" + (f" · 리셋 {rec['resets_at']}" if rec.get("resets_at") else ""))
    else:
        print(json.dumps(bots_health(), ensure_ascii=False, indent=2))
