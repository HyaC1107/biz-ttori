"""biz-ttori — 봇 spawn 동시 실행 제한 큐 (PM 승인: 상한 2, 2026-07-10).

클또리가 파생봇(Agent/T3)을 띄우기 전 claim, 끝나면 release.
상한 초과 시 claim이 exit 1 → 클또리는 앞선 봇 완료를 기다린 후 재시도.
(젬또리 검토 반영 — "동시 spawn 제한 큐로 봇 폭주 차단")

CLI:
  python3 spawn_queue.py claim T-0001 코더봇A [biz-ttori]   # 슬롯 확보 (실패 시 exit 1, 3번째 인자=project)
  python3 spawn_queue.py release T-0001                     # 슬롯 반납 (project는 claim 때 기억한 값 사용)
  python3 spawn_queue.py status                             # 현황
상태: company/spawn-queue.json
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
QUEUE_PATH = ROOT / "company" / "spawn-queue.json"
CLAUDE_SNAP = Path.home() / ".claude" / ".rate-limits.json"  # health.py._claude()와 동일 소스(실측)
CLAUDE_CREDIT_MIN_PCT = 20.0    # 클또리 5시간 크레딧 하한 (PM 결정 2026-07-15) — 이하면 spawn 차단
LIMIT = 2                      # PM 승인 상한 (2026-07-10)
KST = timezone(timedelta(hours=9))
STALE_MIN = 120                # 2시간 넘은 엔트리는 좀비로 간주·자동 회수

sys.path.insert(0, str(Path(__file__).parent))
try:
    from events import append_event, validate_project
except ImportError:
    append_event = None
    validate_project = None


def check_claude_credit_limit() -> bool:
    """클또리(Claude Code) 5시간 롤링 크레딧 잔량이 하한(20%) 이하면 신규 spawn 차단.

    biz-ttori는 구독형이라 USD 단가 계산은 무의미 — health.py._claude()와 동일하게
    Claude Code statusLine 훅이 기록하는 실측 스냅샷(~/.claude/.rate-limits.json)을 그대로 쓴다.
    (구 버전은 $3/$15/$3.75/$0.3 단가로 일일 $10 계산을 했었는데, 구독형과 안 맞아 폐기 —
    2026-07-15 PM 결정으로 크레딧 잔량% 기준으로 교체.)
    """
    if not CLAUDE_SNAP.exists():
        return True  # 스냅샷 없음(세션 미기동 등) — 판단 불가, 허용

    try:
        snap = json.loads(CLAUDE_SNAP.read_text(encoding="utf-8"))
        used = snap.get("five_hour")
        if used is None:
            return True  # 플랜에 따라 미제공 — 판단 불가, 허용
        remaining = max(0, min(100, 100 - int(used)))
        if remaining <= CLAUDE_CREDIT_MIN_PCT:
            print(f"❌ 클또리 5시간 크레딧 잔량 하한 도달 ({remaining}% ≤ {CLAUDE_CREDIT_MIN_PCT:.0f}%) — spawn 차단")
            return False
    except Exception as e:
        print(f"⚠️ 클또리 크레딧 검사 중 오류 발생: {e} (안전을 위해 허용)")
    return True


def check_gemttori_quota_limit() -> bool:
    health_path = ROOT / "company" / "bot_health.json"
    if not health_path.exists():
        return True
        
    try:
        health_data = json.loads(health_path.read_text(encoding="utf-8"))
        gemttori_health = health_data.get("젬또리")
        if not gemttori_health:
            return True
            
        remaining = float(gemttori_health.get("remaining_pct", 100.0))
        resets_at = gemttori_health.get("resets_at")
        
        if remaining < 15.0:
            if resets_at:
                try:
                    now = datetime.now(KST)
                    reset_time = None
                    if "T" in resets_at:
                        reset_time = datetime.fromisoformat(resets_at)
                    else:
                        parts = resets_at.split(" ")
                        if len(parts) == 2:
                            md = parts[0].split("-")
                            hm = parts[1].split(":")
                            if len(md) == 2 and len(hm) == 2:
                                reset_time = now.replace(
                                    month=int(md[0]), day=int(md[1]),
                                    hour=int(hm[0]), minute=int(hm[1]), second=0, microsecond=0
                                )
                    if reset_time and now >= reset_time:
                        return True
                except Exception:
                    pass
            
            print(f"❌ 젬또리 크레딧 15% 미만 경보 ({remaining:.0f}% 남음) — 리셋 대기 필요")
            return False
    except Exception as e:
        print(f"⚠️ 젬또리 쿼터 검사 중 오류 발생: {e} (안전을 위해 허용)")
    return True


def _load() -> dict:
    try:
        return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"running": {}}


def _save(q: dict) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = QUEUE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, QUEUE_PATH)


def _evict_stale(q: dict) -> None:
    now = datetime.now(KST)
    for tid in list(q["running"]):
        try:
            started = datetime.fromisoformat(q["running"][tid]["started"])
            if (now - started).total_seconds() > STALE_MIN * 60:
                print(f"⚠️ 좀비 회수: {tid} ({q['running'][tid].get('actor')}, {STALE_MIN}분 초과)")
                del q["running"][tid]
        except (KeyError, ValueError):
            del q["running"][tid]


def claim(task_id: str, actor: str, project: str | None = None) -> bool:
    # project 검증은 슬롯 저장 **전에** — append_event에서 터지면 큐만 오염된다
    if validate_project:
        try:
            validate_project(project)
        except ValueError as e:
            print(f"❌ {e}")
            return False
    # 클또리(Claude) 5시간 크레딧 잔량 검사 (20% 이하 차단, PM 결정 2026-07-15)
    if not check_claude_credit_limit():
        return False
    # 젬또리 구독 크레딧 잔량 검사 (15% 미만 차단, PM 결정)
    if not check_gemttori_quota_limit():
        return False
    q = _load()
    _evict_stale(q)
    if task_id in q["running"]:
        print(f"이미 실행 중: {task_id}")
        return True
    if len(q["running"]) >= LIMIT:
        busy = ", ".join(f"{t}({v.get('actor')})" for t, v in q["running"].items())
        print(f"❌ 슬롯 없음 ({len(q['running'])}/{LIMIT} 사용 중: {busy}) — 완료 대기 후 재시도")
        return False
    entry = {"actor": actor, "started": datetime.now(KST).isoformat(timespec="seconds")}
    if project:
        entry["project"] = project   # release가 bot.done에 같은 project를 찍도록 기억
    q["running"][task_id] = entry
    _save(q)
    if append_event:
        append_event("bot.spawned", actor, "hq", f"{task_id} spawn (슬롯 {len(q['running'])}/{LIMIT})",
                     task_id=task_id, project=project)
    print(f"✅ claim: {task_id} ({actor}) — 슬롯 {len(q['running'])}/{LIMIT}")
    return True


def release(task_id: str, failed: bool = False) -> None:
    q = _load()
    info = q["running"].pop(task_id, None)
    _save(q)
    if info and append_event:
        etype = "bot.failed" if failed else "bot.done"
        append_event(etype, info.get("actor", "?"), "hq", f"{task_id} 종료 — 슬롯 반납",
                     task_id=task_id, project=info.get("project"))
    print(f"release: {task_id} — 슬롯 {len(q['running'])}/{LIMIT}")


def status() -> None:
    q = _load()
    _evict_stale(q)
    _save(q)
    print(f"슬롯 {len(q['running'])}/{LIMIT}")
    for t, v in q["running"].items():
        print(f"  {t}: {v.get('actor')} (시작 {v.get('started')})")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(1)
    if a[0] == "claim":
        sys.exit(0 if claim(a[1], a[2] if len(a) > 2 else "bot",
                            a[3] if len(a) > 3 else None) else 1)
    elif a[0] == "release":
        release(a[1], failed="--failed" in a)
    elif a[0] == "status":
        status()
    else:
        print(__doc__); sys.exit(1)
