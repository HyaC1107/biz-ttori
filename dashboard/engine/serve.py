"""biz-ttori 대시보드 서버 — 정적 서빙 + 쓰기 API (http.server 승격판).

기존 `python3 -m http.server 8787` 대체. 127.0.0.1 전용 (로컬 PM만).

API (모두 POST, JSON body):
  /api/event     {type, actor, dept, summary, task_id?, project?, refs?, requires_approval?}
                 → events.jsonl append (결재 승인/반려, PM 지시 등)
                 project는 projects.json 등록 id만 허용 (미등록 → 400)
  /api/bots      {bots: [{name, dept, role}, ...]}   → projects.json bots 교체
  /api/projects  {id, patch: {status?|phase?|note?|details?}} → 해당 프로젝트 수정

실행: python3 tool-spec/biz-ttori/engine/serve.py   (포트 8787)
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in HERE.parents if (p / "CLAUDE.md").exists()),
            HERE.parent.parent.parent)
PORT = 8787

sys.path.insert(0, str(HERE))
# PROJECTS_PATH 정본은 events.py — 경로 리터럴을 두 벌 두지 않는다 (검수 지적 2026-07-12)
from events import append_event, VALID_TYPES, KST, PROJECTS_PATH   # noqa: E402

_write_lock = threading.Lock()

# ── 오늘 토큰 사용량 실측 (~/.claude 트랜스크립트 집계, 60s 캐시) ──
TRANSCRIPTS = Path.home() / ".claude" / "projects"
_cost_lock = threading.Lock()                  # ThreadingHTTPServer 동시 GET 가드
_cost_cache = {"t": 0.0, "data": None, "day": None}
_file_cache: dict = {}                         # path → (mtime, size, 부분합) — 대용량 재파싱 방지


def _parse_file(f: Path, today) -> dict:
    from datetime import datetime
    part = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "msgs": 0}
    seen: set[str] = set()   # 스트리밍 중복 라인 방지 (파일 내 메시지 id 단위 1회)
    with f.open(encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if '"usage"' not in line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = obj.get("timestamp", "")
            try:   # 트랜스크립트 ts는 UTC — KST 날짜로 환산해 오늘만
                if datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(KST).date() != today:
                    continue
            except ValueError:
                continue
            msg = obj.get("message") or {}
            u = msg.get("usage")
            if not isinstance(u, dict):
                continue
            mid = msg.get("id")
            if mid:
                if mid in seen:
                    continue
                seen.add(mid)
            part["input"] += u.get("input_tokens", 0) or 0
            part["output"] += u.get("output_tokens", 0) or 0
            part["cache_read"] += u.get("cache_read_input_tokens", 0) or 0
            part["cache_write"] += u.get("cache_creation_input_tokens", 0) or 0
            part["msgs"] += 1
    return part


def _today_usage() -> dict:
    from datetime import datetime
    today = datetime.now(KST).date()
    tot = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "msgs": 0}
    # 트랜스크립트는 Claude Code가 깔린 환경에만 있다. 없는 환경(제품 배포본)에서
    # 0을 그대로 주면 "오늘 토큰 0"으로 보여 실측처럼 읽힌다 → available=False로 구분해 HUD를 숨긴다.
    if not TRANSCRIPTS.exists():
        return {**tot, "available": False}
    for f in TRANSCRIPTS.glob("*/*.jsonl"):
        try:   # 오늘 안 건드린 파일엔 오늘 라인이 없다 — mtime으로 1차 컷
            st = f.stat()
            if datetime.fromtimestamp(st.st_mtime, KST).date() != today:
                continue
            key = str(f)
            cached = _file_cache.get(key)
            if cached and cached[0] == st.st_mtime and cached[1] == st.st_size:
                part = cached[2]   # 안 바뀐 파일은 부분합 재사용
            else:
                part = _parse_file(f, today)
                _file_cache[key] = (st.st_mtime, st.st_size, part)
        except OSError:
            continue
        for k in tot:
            tot[k] += part[k]
    return {**tot, "available": True}


def _load_projects() -> dict:
    return json.loads(PROJECTS_PATH.read_text(encoding="utf-8"))


def _save_projects(data: dict) -> None:
    tmp = PROJECTS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, PROJECTS_PATH)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, fmt, *args):   # 액세스 로그 소음 제거 (에러만 stderr)
        pass

    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            # 봇별 남은 체력(구독 한도 잔량). 실측 가능한 봇만 게이지를 준다.
            try:
                from health import bots_health
                return self._json(200, {"ok": True, **bots_health()})
            except Exception:
                import traceback
                traceback.print_exc()
                return self._json(500, {"ok": False, "error": "체력 조회 실패"})
        if self.path == "/api/procs":
            # 로컬 프로세스/포트 관제 — 화이트리스트(procs.REGISTRY)만 다룬다.
            # serve.py가 127.0.0.1 바인딩이라 외부에서 이 API를 못 부른다.
            try:
                from procs import list_procs
                return self._json(200, {"ok": True, **list_procs()})
            except Exception:
                import traceback
                traceback.print_exc()
                return self._json(500, {"ok": False, "error": "프로세스 조회 실패"})
        if self.path == "/api/tasks":
            # 태스크 라이프사이클 상태 — 판정 SSOT는 tasks.py (JS 중복 금지)
            try:
                from tasks import build_tasks, summarize
                items = build_tasks()
                return self._json(200, {"ok": True, "summary": summarize(items), "tasks": items})
            except Exception:
                import traceback
                traceback.print_exc()          # 상세는 stderr — 클라이언트엔 고정 문구
                return self._json(500, {"ok": False, "error": "태스크 집계 실패"})
        if self.path == "/api/cost":
            with _cost_lock:
                now = time.time()
                if _cost_cache["data"] is None or now - _cost_cache["t"] > 60:
                    try:
                        _cost_cache["data"] = _today_usage()
                        _cost_cache["t"] = now
                    except Exception as e:
                        return self._json(500, {"ok": False, "error": str(e)})
                data = dict(_cost_cache["data"])
            return self._json(200, {"ok": True, **data})
        return super().do_GET()

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"ok": False, "error": "잘못된 JSON"})

        with _write_lock:
            try:
                if self.path == "/api/event":
                    return self._api_event(body)
                if self.path == "/api/bots":
                    return self._api_bots(body)
                if self.path == "/api/depts":
                    return self._api_depts(body)
                if self.path == "/api/projects":
                    return self._api_projects(body)
                if self.path == "/api/procs":
                    return self._api_procs(body)
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})
        self._json(404, {"ok": False, "error": "unknown api"})

    def _api_event(self, b: dict):
        t = b.get("type")
        if t not in VALID_TYPES:
            return self._json(400, {"ok": False, "error": f"unknown type: {t}"})
        for f in ("actor", "dept", "summary"):
            if not b.get(f):
                return self._json(400, {"ok": False, "error": f"{f} 필수"})
        is_order = (t == "task.created" and b["actor"] == "PM"
                    and b["summary"].startswith("[PM지시]"))
        tid = b.get("task_id")
        if is_order and not tid:
            tid = f"T-auto-{time.time_ns()}"   # 지시↔지시봇 보고 연결 고리 (ns — 같은 초 지시 2건 충돌 방지)
        try:
            ev = append_event(t, b["actor"], b["dept"], b["summary"],
                              task_id=tid, refs=b.get("refs"),
                              requires_approval=bool(b.get("requires_approval")),
                              project=b.get("project"))
        except ValueError as e:   # 미등록 project — 유령 프로젝트 차단
            return self._json(400, {"ok": False, "error": str(e)})
        # [PM지시] → 지시봇(헤드리스 클또리) 즉시 기동 (PM 요청 2026-07-10: "전송=바로 처리")
        spawned = False
        if is_order:
            spawned = self._spawn_order_worker(b["summary"], tid, b.get("project"))
        self._json(200, {"ok": True, "event": ev, "worker_spawned": spawned})

    def _spawn_order_worker(self, summary: str, tid: str, project: str | None = None) -> bool:
        """지시 1건당 헤드리스 claude 1회. spawn 큐로 동시≤2 강제, 만석이면 대기 이벤트만."""
        claim_cmd = [sys.executable, str(HERE / "spawn_queue.py"), "claim", tid, "지시봇"]
        if project:
            claim_cmd.append(project)   # bot.spawned/bot.done도 같은 project로 스탬프
        claim = subprocess.run(claim_cmd, capture_output=True, text=True)
        if claim.returncode != 0:
            append_event("bot.failed", "지시봇", "hq",
                         f"슬롯 만석 — 지시는 기록됨, 다음 세션 처리: {summary[:60]}",
                         task_id=tid, project=project)
            return False
        order = summary.removeprefix("[PM지시]").strip()
        # id에 공백/메타문자가 있어도 지시봇의 보고 명령이 안 깨지게 인용
        proj_flag = f" --project {shlex.quote(project)}" if project else ""
        rule2 = ("② 완료하면 `python3 tool-spec/biz-ttori/engine/events.py append --type report.filed "
                 f"--actor 지시봇 --dept hq --task-id {tid}{proj_flag} --summary \"결과 한줄\"` 로 기록하라."
                 + ("" if project else
                    " project가 지정 안 된 지시는 이벤트에 --project를 붙이지 마라(추측 금지)."))
        prompt = (
            f"[지시봇 — PM 지시 자동처리 워커] 지시: {order}\n"
            "규칙: ① tool-spec/biz-ttori/runbook.md §1 라우팅에 따라 처리하라. "
            f"{rule2} "
            f"③ 위험/비가역/대규모/불명확한 지시는 실행하지 말고 approval.requested 이벤트만 남겨라(--task-id {tid} 동일하게). "
            "④ 파생봇 재귀 spawn 금지, 젬또리(agy) 호출 금지(T1). ⑤ 간결하게.")
        cmd = (f"cd {shlex.quote(str(ROOT))} && "
               f"claude -p {shlex.quote(prompt)} --max-turns 30 >> /tmp/pm-order-worker.log 2>&1; "
               f"{shlex.quote(sys.executable)} {shlex.quote(str(HERE / 'spawn_queue.py'))} release {tid}")
        subprocess.Popen(["bash", "-c", cmd], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True

    def _api_bots(self, b: dict):
        bots = b.get("bots")
        if not isinstance(bots, list) or not bots:
            return self._json(400, {"ok": False, "error": "bots 배열 필수"})
        for bot in bots:
            if not (bot.get("name") and bot.get("dept") and bot.get("role")):
                return self._json(400, {"ok": False, "error": "각 봇에 name/dept/role 필수"})
        data = _load_projects()
        old = {x["name"] for x in data.get("bots", [])}
        new = {x["name"] for x in bots}
        data["bots"] = [{"name": x["name"], "dept": x["dept"], "role": x["role"]} for x in bots]
        _save_projects(data)
        diff = []
        if new - old: diff.append(f"추가 {', '.join(new - old)}")
        if old - new: diff.append(f"삭제 {', '.join(old - new)}")
        append_event("org.changed", "PM", "hq",
                     f"봇 조직 변경 — {'; '.join(diff) if diff else '정보 수정'} (총 {len(new)}명)")
        self._json(200, {"ok": True, "bots": data["bots"]})

    def _api_depts(self, b: dict):
        depts = b.get("depts")
        if not isinstance(depts, list) or not depts:
            return self._json(400, {"ok": False, "error": "depts 배열 필수"})
        for d in depts:
            if not (d.get("slug") and d.get("name")):
                return self._json(400, {"ok": False, "error": "각 부서에 slug/name 필수"})
        data = _load_projects()
        old = {x["slug"] for x in data.get("depts", [])}
        new = {x["slug"] for x in depts}
        # 사용 중인 부서 삭제 방지 (봇/프로젝트가 참조)
        removed = old - new
        in_use = {x["dept"] for x in data.get("bots", [])} | {x["dept"] for x in data.get("projects", [])}
        blocked = removed & in_use
        if blocked:
            return self._json(400, {"ok": False, "error": f"봇/프로젝트가 소속된 부서는 삭제 불가: {', '.join(blocked)}"})
        data["depts"] = [{"slug": x["slug"], "name": x["name"],
                          "color": x.get("color", "#7cc4ff")} for x in depts]
        _save_projects(data)
        diff = []
        if new - old: diff.append(f"신설 {', '.join(new - old)}")
        if removed: diff.append(f"폐지 {', '.join(removed)}")
        append_event("org.changed", "PM", "hq",
                     f"부서 개편 — {'; '.join(diff) if diff else '명칭/정보 수정'} (총 {len(new)}개)")
        self._json(200, {"ok": True, "depts": data["depts"]})

    def _api_procs(self, b: dict):
        """로컬 프로세스 종료. **화이트리스트(procs.REGISTRY) 키만** 허용 — 임의 PID kill 불가."""
        from procs import stop, REGISTRY, hits_self

        if b.get("action") != "stop":
            return self._json(400, {"ok": False, "error": "action=stop 만 지원"})
        key = b.get("key")
        spec = next((s for s in REGISTRY if s["key"] == key), None)
        if not spec:
            return self._json(400, {"ok": False, "error": f"알 수 없는 프로세스: {key}"})

        # 자기 자신(대시보드 서버)을 끄는 경우: 응답을 먼저 보내고 나서 죽어야
        # 클라이언트가 결과를 받는다. 안 그러면 연결이 끊겨 "실패"처럼 보인다.
        # 판정은 정적 플래그가 아니라 hits_self() — 설정에 별칭을 넣어 confirm 게이트를 우회하는 걸 막는다.
        if spec.get("is_self") or hits_self(key):
            if not b.get("confirm"):
                return self._json(400, {"ok": False,
                                        "error": "대시보드 서버 자신이다 — confirm:true 필요"})
            self._json(200, {"ok": True, "self_stop": True, "name": spec["name"],
                             "note": "대시보드 서버를 종료한다 — 이 페이지는 곧 응답하지 않는다"})
            threading.Timer(0.5, lambda: stop(key)).start()
            return

        r = stop(key)
        append_event("bot.done" if r.get("ok") else "bot.failed", "PM", "ops",
                     f"프로세스 종료: {spec['name']}"
                     + (f" (pid {r.get('stopped')})" if r.get("stopped") else " — 이미 꺼져 있음"))
        return self._json(200, r)

    def _api_projects(self, b: dict):
        pid, patch = b.get("id"), b.get("patch")
        if not pid or not isinstance(patch, dict):
            return self._json(400, {"ok": False, "error": "id + patch 필수"})
        allowed = {"status", "phase", "note", "details"}
        bad = set(patch) - allowed
        if bad:
            return self._json(400, {"ok": False, "error": f"수정 불가 필드: {bad}"})
        data = _load_projects()
        for p in data["projects"]:
            if p["id"] == pid:
                p.update(patch)
                _save_projects(data)
                append_event("project.updated", "PM", "hq",
                             f"{p['name']} 수정 — {', '.join(patch.keys())}")
                return self._json(200, {"ok": True, "project": p})
        self._json(404, {"ok": False, "error": f"프로젝트 없음: {pid}"})


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"biz-ttori 대시보드 서버 — http://127.0.0.1:{PORT} (root={ROOT})")
    srv.serve_forever()
