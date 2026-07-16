"""로컬 프로세스/포트 관제 — 대시보드에서 뭐가 떠 있는지 보고 끌 수 있게.

데몬이 늘어나면서(대시보드 서버·우편함 감시·어텐션 백엔드/프론트…) 뭐가 켜져 있는지
추적이 안 되는 문제가 있었다. 이 모듈은 **알려진 프로세스만** 탐지·설명·종료한다.

## 안전 설계
- **화이트리스트 전용.** 레지스트리(`REGISTRY`)에 정의된 것만 종료 가능.
  임의 PID kill은 API로 못 한다(경로 자체가 없음).
- serve.py는 `127.0.0.1`에만 바인딩 → 외부에서 이 API를 못 부른다.
- 자기 자신(대시보드 서버)은 `is_self=True`로 표시 — 끄면 대시보드도 같이 죽는다(UI에서 경고).
- 종료는 SIGTERM → 3초 대기 → 안 죽으면 SIGKILL.

## ⚠️ pgrep 자기매칭 함정
`pgrep -f "serve.py"` 는 **그 명령을 실행한 셸 자신**도 잡는다(여러 번 밟은 함정).
여기선 `/proc/*/cmdline`을 직접 읽고 **자기 PID와 부모 PID를 제외**한다.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

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

# ── OS별 관제 방식 (크로스플랫폼) ──────────────────────────────
# 프로세스/포트를 읽는 방법은 OS마다 다르다. 아래 플래그로 한 번만 분기하고,
# 각 함수(_scan / _cmdline / _start_time / _listening_ports)에서 OS별로 갈라진다.
#
#   • Linux   : /proc 파일시스템 + `ss -tlnp`      (이 저장소가 처음 돌던 환경)
#   • macOS/BSD: `ps -axww` + `lsof -iTCP -sTCP:LISTEN`  (/proc·ss 둘 다 없음)
#   • Windows : 미지원. 필요하면 `tasklist` / `Get-NetTCPConnection`(PowerShell)으로
#               _scan()·_listening_ports()에 분기를 하나 더 추가하면 된다.
#
# 판정은 /proc 존재 여부로 한다 — /proc 이 있으면 Linux(WSL 포함)로 보고 그 경로를,
# 없으면 macOS/BSD 경로(ps·lsof)를 쓴다. 다른 OS를 붙일 때 이 상수와 각 함수의
# `if _IS_LINUX:` 분기만 손대면 된다.
_IS_LINUX = Path("/proc").is_dir()

# ── 알려진 프로세스 레지스트리 ─────────────────────────────────
# match: cmdline 에 이 문자열이 모두 들어가면 해당 프로세스로 본다.
#
# 🧱 제품 기본값은 **대시보드 서버 하나뿐**이다. 우편함 감시 데몬·프로젝트 개발서버 같은
#    감시 대상은 환경마다 다르므로 하드코딩하지 않는다 — 하드코딩하면 그게 없는 환경
#    (= 남의 회사에 배포된 biz-ttori)에서 봇 현황이 전부 '정지'로 뜬다.
#    환경 고유 항목은 company/procs.json 에 선언한다. (ref: tool-spec/BOUNDARY.md)
def _serve_cmd() -> str:
    """대시보드 서버 재시작 명령. 경로를 글자로 박으면 폴더를 옮긴 순간 UI가 틀린 명령을 안내한다."""
    serve = Path(__file__).resolve().parent / "serve.py"
    try:
        return f"python3 {serve.relative_to(ROOT)}"
    except ValueError:            # ROOT 밖에 있으면 절대경로로
        return f"python3 {serve}"


BUILTIN: list[dict[str, Any]] = [
    {
        "key": "board",
        "name": "AI 회사 대시보드 서버",
        "match": ["serve.py"],
        "port": 8787,
        "desc": "현황판·3D 대시보드를 서빙하고 결재/이벤트 API를 처리한다. 이걸 끄면 대시보드가 안 열린다.",
        "start": _serve_cmd(),
        "is_self": True,          # 끄면 이 API도 같이 죽음
    },
]

PROCS_CONFIG = ROOT / "company" / "procs.json"


def _load_registry() -> list[dict[str, Any]]:
    """BUILTIN + company/procs.json 의 환경 고유 항목.

    이 목록은 **종료(kill) 대상 화이트리스트**이기도 하다. 설정에서 온 항목은
    검증을 통과한 것만 싣고, 내장 키(board)는 덮어쓰지 못하게 막는다
    (is_self 를 거짓으로 덮어써 대시보드 서버를 조용히 죽이는 걸 방지).
    """
    reg: list[dict[str, Any]] = [dict(s) for s in BUILTIN]
    try:
        raw = json.loads(PROCS_CONFIG.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return reg                      # 설정 없음 = 제품 기본값 (정상 경로)
    except (OSError, json.JSONDecodeError):
        return reg                      # 설정이 깨져도 대시보드 서버 감시는 살아 있어야 한다

    if not isinstance(raw, dict):       # 유효한 JSON이지만 최상위가 [] 나 "x" 인 경우
        return reg
    entries = raw.get("procs", [])
    if not isinstance(entries, list):
        return reg

    for spec in entries:
        if not isinstance(spec, dict):
            continue
        key, match = spec.get("key"), spec.get("match")
        if not isinstance(key, str) or not key.strip():
            continue                    # key 는 문자열 — 숫자면 API에서 영원히 못 부른다
        if any(s["key"] == key for s in reg):
            continue                    # 내장 항목 덮어쓰기 금지
        # 🔴 match 는 kill 대상 판정식이다. 빈 문자열 토큰 하나면 `all(tok in cmd)` 가 항상 참이 되어
        #    **떠 있는 모든 프로세스**가 종료 대상이 된다. 토큰을 엄격히 검증한다.
        if not isinstance(match, list) or not match:
            continue
        toks = [m.strip() for m in match if isinstance(m, str) and len(m.strip()) >= 2]
        if len(toks) != len(match):
            continue                    # 하나라도 불량이면 항목 자체를 버린다 (부분 수용 금지)

        port = spec.get("port")
        if not isinstance(port, int) or isinstance(port, bool):
            port = None                 # "8000" 같은 문자열은 ss 결과(int 키)와 안 맞아 항상 '닫힘'으로 보인다

        reg.append({
            "key": key,
            "name": spec.get("name") if isinstance(spec.get("name"), str) else key,
            "match": toks,
            "port": port,
            "desc": spec.get("desc") if isinstance(spec.get("desc"), str) else "",
            "start": spec.get("start") if isinstance(spec.get("start"), str) else None,
            "is_self": False,           # 설정으로는 is_self 를 못 켠다 (실제 판정은 hits_self — 아래)
            "bot": spec.get("bot"),     # 봇 현황판 연결키 (데몬 봇의 상태 SSOT는 실제 프로세스)
        })
    return reg


REGISTRY: list[dict[str, Any]] = _load_registry()


# ── /proc 스캔 ──────────────────────────────────────────────────
def _cmdline(pid: int) -> str:
    # Linux: /proc/<pid>/cmdline (NUL 구분 argv)
    if _IS_LINUX:
        try:
            raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        except (OSError, PermissionError):
            return ""
        return raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()
    # macOS/BSD: /proc 이 없으므로 ps 로 커맨드라인 한 줄을 뽑는다.
    try:
        r = subprocess.run(["ps", "-p", str(pid), "-o", "command="],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout.strip()


def _parse_etime(s: str) -> Optional[int]:
    """ps 의 elapsed time('[[dd-]hh:]mm:ss')을 초로 변환. Linux·BSD 공통 포맷."""
    s = s.strip()
    if not s:
        return None
    days = 0
    if "-" in s:                       # dd-hh:mm:ss
        d, s = s.split("-", 1)
        try:
            days = int(d)
        except ValueError:
            return None
    try:
        parts = [int(p) for p in s.split(":")]
    except ValueError:
        return None
    if len(parts) == 3:                # hh:mm:ss
        h, m, sec = parts
    elif len(parts) == 2:              # mm:ss
        h, m, sec = 0, parts[0], parts[1]
    else:
        return None
    return days * 86400 + h * 3600 + m * 60 + sec


def _start_time(pid: int) -> Optional[float]:
    """프로세스 시작 시각(epoch). uptime 계산용."""
    # Linux: /proc/<pid> 의 stat ctime = 프로세스 생성 시각
    if _IS_LINUX:
        try:
            return Path(f"/proc/{pid}").stat().st_ctime
        except OSError:
            return None
    # macOS/BSD: /proc 이 없으므로 ps 의 경과시간(etime)에서 시작 epoch 을 역산한다.
    try:
        r = subprocess.run(["ps", "-p", str(pid), "-o", "etime="],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    secs = _parse_etime(r.stdout)
    return None if secs is None else time.time() - secs


# 🔴 프로그램을 "언급만" 하는 프로세스(셸·grep·curl 등)를 실제 프로세스로 오인하면
#    그걸 죽여버린다. 실제로 밟았다: `bash -c "... uvicorn app.main:app ..."` 인 셸이
#    uvicorn으로 잡혀 종료됨 → 호출한 셸이 자살(exit 144).
#    → argv[0] 이 셸/래퍼면 제외한다. (pgrep -f 자기매칭과 같은 함정)
#    ⚠️ node/python은 제외하면 안 된다 — Vite가 node, 서버가 python이라 진짜 프로세스다.
#       셸과 "명령을 언급만 하는" 도구들만 뺀다.
_WRAPPERS = ("bash", "sh", "zsh", "dash", "grep", "curl", "nohup", "setsid",
             "timeout", "watch", "xargs", "claude")


def _is_wrapper(cmd: str) -> bool:
    argv0 = cmd.split()[0] if cmd.split() else ""
    base = os.path.basename(argv0)
    return any(base == w or base.startswith(w + ".") for w in _WRAPPERS)


def _scan() -> list[tuple[int, str]]:
    """현재 프로세스 목록. **셸 래퍼만** 제외한다.

    자기 PID를 빼면 안 된다 — serve.py가 자기 자신을 스캔하므로,
    빼버리면 '대시보드 서버'가 영원히 '꺼짐'으로 보인다(실제로 그랬다).
    자기 종료는 stop()이 아니라 API의 is_self + confirm 으로 통제한다.
    """
    out = []
    # Linux: /proc 디렉터리를 직접 순회
    if _IS_LINUX:
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            cmd = _cmdline(pid)
            if not cmd or _is_wrapper(cmd):
                continue
            out.append((pid, cmd))
        return out
    # macOS/BSD: /proc 이 없으므로 ps 한 번으로 전체 프로세스를 훑는다.
    #   -a 모든 사용자 · -x 제어터미널 없는 데몬 포함 · -ww 커맨드 truncation 방지
    #   출력: "<pid> <command…>" 한 줄씩
    try:
        r = subprocess.run(["ps", "-axww", "-o", "pid=,command="],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return out
    for line in r.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        pid, cmd = int(parts[0]), parts[1]
        if not cmd or _is_wrapper(cmd):
            continue
        out.append((pid, cmd))
    return out


def _listening_ports() -> dict[int, int]:
    """LISTEN 중인 포트 → pid 매핑 (psutil 없는 환경 기준)."""
    ports: dict[int, int] = {}
    # Linux: ss. 출력 예 `... 0.0.0.0:8787 ... users:(("python3",pid=123,fd=3))`
    if _IS_LINUX:
        try:
            r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            return ports
        for line in r.stdout.splitlines():
            if "LISTEN" not in line:
                continue
            m_port = re.search(r":(\d+)\s", line)
            m_pid = re.search(r"pid=(\d+)", line)
            if m_port and m_pid:
                ports[int(m_port.group(1))] = int(m_pid.group(1))
        return ports
    # macOS/BSD: lsof. 출력 예
    #   `python3.1 46881 user 3u IPv4 0x… 0t0 TCP 127.0.0.1:8787 (LISTEN)`
    #   → 2번째 컬럼 = pid, NAME 끝의 ':<port> (LISTEN)' = 포트
    try:
        r = subprocess.run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ports
    for line in r.stdout.splitlines():
        if "LISTEN" not in line:
            continue
        fields = line.split()
        m_port = re.search(r":(\d+)\s*\(LISTEN\)", line)
        if len(fields) < 2 or not fields[1].isdigit() or not m_port:
            continue
        ports[int(m_port.group(1))] = int(fields[1])
    return ports


def _match_pids(spec: dict[str, Any]) -> list[int]:
    return [pid for pid, cmd in _scan() if all(tok in cmd for tok in spec["match"])]


def hits_self(key: str) -> bool:
    """이 키를 종료하면 **대시보드 서버 자신이 죽는가**.

    ⚠️ is_self 를 스펙의 정적 플래그로만 보면 우회된다: 설정에 match:["serve.py"] 짜리
       별칭 항목을 넣으면 is_self=False 로 등록되지만 실제로는 같은 프로세스를 잡는다
       (리뷰 지적 2026-07-13). 그래서 **실행 중인 PID에 내 PID가 들어있는지**로 판정한다.
    """
    spec = next((s for s in REGISTRY if s["key"] == key), None)
    if not spec:
        return False
    return os.getpid() in _match_pids(spec)


# ── 조회 ────────────────────────────────────────────────────────
def list_procs() -> dict[str, Any]:
    procs = _scan()
    ports = _listening_ports()
    now = time.time()

    known = []
    claimed_pids: set[int] = set()

    for spec in REGISTRY:
        hits = [(pid, cmd) for pid, cmd in procs
                if all(tok in cmd for tok in spec["match"])]
        # 같은 프로그램이 여러 개 떠 있을 수 있음 (예: uv run + 실제 uvicorn)
        entry = {
            "key": spec["key"],
            "name": spec["name"],
            "desc": spec["desc"],
            "port": spec["port"],
            "start": spec.get("start"),
            # 정적 플래그 OR 실제로 내 PID를 잡는가 — 별칭 항목도 자기 자신으로 표시된다
            "is_self": spec.get("is_self", False) or os.getpid() in [pid for pid, _ in hits],
            "bot": spec.get("bot"),        # 봇 현황판 연결키 (데몬 봇의 상태 SSOT)
            "running": bool(hits),
            "pids": [pid for pid, _ in hits],
            "uptime_min": None,
            "port_open": False,
        }
        if hits:
            claimed_pids.update(entry["pids"])
            st = _start_time(hits[0][0])
            if st:
                entry["uptime_min"] = round((now - st) / 60, 1)
        if spec["port"]:
            entry["port_open"] = spec["port"] in ports
        known.append(entry)

    # 우리가 모르는 리스닝 포트 (뭐가 포트를 물고 있는지 PM이 볼 수 있게)
    #
    # ⚠️ macOS 는 로컬 리스너가 Linux 보다 훨씬 많다(IDE·브라우저 디버그·Adobe·보안에이전트
    #    등이 임시 고포트를 수십 개 연다). 전부 나열하면 패널이 노이즈로 도배되고 정작 내
    #    개발서버가 안 보인다. 그래서 **임시(ephemeral) 포트 대역은 숨긴다** — 그 대역은
    #    앱이 매번 랜덤으로 잡았다 버리는 자리라 사람이 관리할 대상이 아니다.
    #    개발서버는 3000·5173·8080·8081 처럼 낮고 외우는 포트를 쓰므로 그대로 보인다.
    #    (기준: IANA/BSD 동적 포트 시작점 49152. 이 값만 바꾸면 노출 폭을 조절할 수 있다.)
    EPHEMERAL_MIN = 49152
    others = []
    hidden = 0
    for port, pid in sorted(ports.items()):
        if pid in claimed_pids:
            continue
        if port >= EPHEMERAL_MIN:          # 임시 대역 = 관리 불가한 일회성 리스너 → 숨김
            hidden += 1
            continue
        cmd = _cmdline(pid)
        if not cmd:
            continue
        others.append({"port": port, "pid": pid, "cmd": cmd[:90]})

    return {"known": known, "other_ports": others, "hidden_ephemeral": hidden}


# ── 종료 ────────────────────────────────────────────────────────
def stop(key: str) -> dict[str, Any]:
    """레지스트리에 있는 프로세스만 종료. SIGTERM → 3s → SIGKILL."""
    spec = next((s for s in REGISTRY if s["key"] == key), None)
    if not spec:
        return {"ok": False, "error": f"알 수 없는 프로세스: {key}"}   # 화이트리스트 밖

    targets = [pid for pid, cmd in _scan()
               if all(tok in cmd for tok in spec["match"])]
    if not targets:
        return {"ok": True, "stopped": [], "note": "이미 꺼져 있음"}

    for pid in targets:
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass

    time.sleep(3)

    still = []
    for pid in targets:
        try:
            os.kill(pid, 0)          # 살아있나 확인
            os.kill(pid, signal.SIGKILL)
            still.append(pid)
        except (ProcessLookupError, PermissionError):
            pass

    return {"ok": True, "stopped": targets, "force_killed": still,
            "name": spec["name"]}


# ── 기동 ────────────────────────────────────────────────────────
def start(key: str) -> dict[str, Any]:
    """레지스트리에 있고 start 명령이 정의된 프로세스만 (재)기동한다.

    ## 안전 설계 (stop 과 대칭)
    - **화이트리스트 전용.** REGISTRY 키만 기동 가능 — 임의 명령 실행 경로는 없다.
    - start 문자열은 내장(board=_serve_cmd) 또는 company/procs.json(신뢰 로컬 설정)에서
      온다. 원래 UI가 "터미널에서 이 명령을 실행하라"고 그대로 안내하던 것과 **같은
      신뢰수준**이다 (복붙 실행을 버튼으로 옮긴 것).
    - **이미 떠 있으면 중복 기동 금지** — 포트 충돌·중복 데몬을 막는다. board(is_self)는
      serve.py 자신이 스캔에 잡히므로 서버가 살아 있는 한 항상 already_running 이다.
    - 백그라운드(start_new_session)로 띄워 요청이 끝나도 살아 있게 한다. cwd=ROOT 고정.
    - 기동 로그는 /tmp/biz-ttori-proc-<key>.log 로 남겨 안 뜬 이유를 추적할 수 있게 한다.
    """
    spec = next((s for s in REGISTRY if s["key"] == key), None)
    if not spec:
        return {"ok": False, "error": f"알 수 없는 프로세스: {key}"}   # 화이트리스트 밖
    cmd = spec.get("start")
    if not cmd:
        return {"ok": False, "error": f"{spec['name']}: 시작 명령(start)이 정의돼 있지 않다",
                "name": spec["name"]}

    if _match_pids(spec):          # 이미 떠 있음 — 중복 기동 안 함
        return {"ok": True, "already_running": True, "name": spec["name"]}

    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", key)
    logpath = f"/tmp/biz-ttori-proc-{safe}.log"
    try:
        logf = open(logpath, "ab")
        subprocess.Popen(["bash", "-c", cmd], cwd=str(ROOT),
                         start_new_session=True, stdout=logf, stderr=logf)
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "error": f"기동 실패: {e}", "name": spec["name"]}
    return {"ok": True, "started": True, "name": spec["name"],
            "cmd": cmd, "log": logpath}


if __name__ == "__main__":
    import json
    print(json.dumps(list_procs(), ensure_ascii=False, indent=2))
