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
LIMIT = 2                      # PM 승인 상한 (2026-07-10)
STALE_MIN = 120                # 2시간 넘은 엔트리는 좀비로 간주·자동 회수
KST = timezone(timedelta(hours=9))

sys.path.insert(0, str(Path(__file__).parent))
try:
    from events import append_event, validate_project
except ImportError:
    append_event = None
    validate_project = None


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
