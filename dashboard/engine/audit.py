"""검증관(Auditor) — 결재 게이트.

PM에게 결재를 올리기 **직전에** 결과물을 자동 검증한다.
지금까지는 클또리가 자기 작업을 자기가 "다 됐다" 판정하고 바로 결재를 올렸다 —
작성자와 검증자가 같은 확증편향 구조였다(CLAUDE.md 철칙 4 위반에 가깝다).

    task.created → report.filed → [🔍 audit] → approval.requested → granted → bot.done
                                       ↑
                              여기서 걸리면 PM에게 안 올라간다

## 왜 규칙 기반(LLM 없음)인가
우리가 반복해서 밟은 실수는 대부분 **패턴으로 잡힌다**:
pgrep 자기매칭(3회), 인라인 onclick XSS, 봇 상태 하드코딩, T1 위반(agy 자동호출),
지어낸 수치, task.created 없이 report만 올린 태스크…
이것들은 team-rules.md에 **글로만** 적혀 있었고, 글로만 있으니 또 밟았다.
여기서는 **실행 가능한 검사**로 바꾼다. 토큰 0원, 매번 돌려도 공짜다.

LLM 판단이 필요한 부분(설계 타당성, 로직 오류)은 2단 LLM 검증관(agents/auditor.md)이
diff 한정으로 맡는다. 정적 게이트는 그 앞단의 싸구려 필터다.

## 사용
    python3 audit.py check --task T-0007          # 태스크 1건 검증
    python3 audit.py check --diff                 # working tree 변경분 검증
    python3 audit.py gate --task T-0007 --summary "..."   # 검증 통과 시에만 결재 올림

## 심각도
    🔴 blocker — 결재 차단. 고치기 전엔 PM에게 안 올라감
    🟡 warn    — 통과시키되 결재 카드에 경고 배지
    🟢 note    — 참고
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from events import append_event, read_events   # noqa: E402

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
KST = timezone(timedelta(hours=9))

BLOCKER, WARN, NOTE = "blocker", "warn", "note"
_ICON = {BLOCKER: "🔴", WARN: "🟡", NOTE: "🟢"}


@dataclass
class Finding:
    severity: str
    rule: str            # 규칙 ID (team-rules 추적용)
    detail: str
    where: str = ""      # file:line 또는 task_id
    # 🔴 게이트 차단 범위. 과거의 빚이 미래의 결재를 영원히 잠그면 안 된다.
    #    "task" = 지금 결재하려는 태스크의 결함  → 차단
    #    "code" = 이번 변경분(diff)의 결함        → 차단
    #    "global" = 다른 태스크·과거 이력의 결함  → 보이되 차단 안 함(위생 리포트)
    scope: str = "task"

    def line(self) -> str:
        loc = f" ({self.where})" if self.where else ""
        tag = " ·위생(차단 안 함)" if self.scope == "global" else ""
        return f"{_ICON[self.severity]} [{self.rule}] {self.detail}{loc}{tag}"


# ══════════════════════════════════════════════════════════════
#  A. 라이프사이클 검사 — 이벤트 그래프의 결함
#     (태스크 보드 도입 때 기존 태스크 5건이 이 검사에 걸렸다)
# ══════════════════════════════════════════════════════════════
STUCK_HOURS = 24

# 네임스페이스마다 "시작 이벤트"가 다르다. 이걸 모르면 Debate·크론 리포트를
# 전부 결함으로 잡아 늑대소년이 된다 (오탐 나는 검증관은 아무도 안 본다).
#   T- 태스크    → task.created
#   D- Debate    → debate.started
#   R-/H- 크론   → 사람이 만든 태스크가 아님(AI 레이더·체력 보고). 생성 이벤트 없음이 정상
GENESIS = {"T": "task.created", "D": "debate.started"}

# 태스크가 "끝났다"고 보는 이벤트. tasks.py의 종료 판정과 기준을 맞춘다.
CLOSED_TYPES = {"bot.done", "approval.granted", "approval.rejected",
                "bot.failed", "debate.concluded"}
AUTONOMOUS_NS = {"R", "H"}          # 자동 생성 — 라이프사이클 검사 면제


def _ns(task_id: str) -> str:
    return task_id.split("-", 1)[0] if "-" in task_id else ""


def _parse_ts(s: str):
    try:
        dt = datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
    return dt.replace(tzinfo=KST) if dt.tzinfo is None else dt   # naive → KST


def check_lifecycle(task_id: str | None = None) -> list[Finding]:
    evs = read_events()
    out: list[Finding] = []

    by_task: dict[str, list[dict]] = {}
    for e in evs:
        tid = e.get("task_id")
        if tid:
            by_task.setdefault(tid, []).append(e)

    targets = [task_id] if task_id else list(by_task)
    now = datetime.now(KST)

    # LC-002는 **전역 검사**다 — 태스크 루프 밖에서 한 번만 돈다.
    # (루프 안에 두면 태스크 수 × 이벤트 수 만큼 반복 스캔한다 — 젬또리 리뷰 지적)
    for e in evs:
        if e["type"] == "approval.requested" and not e.get("task_id"):
            out.append(Finding(WARN, "LC-002",
                               f"결재 요청에 task_id가 없다 — 브리핑이 처리 여부를 매칭 못 함: "
                               f"\"{e.get('summary', '')[:40]}\"", e.get("ts", ""),
                               scope="global"))

    for tid in targets:
        group = by_task.get(tid, [])
        if not group:
            out.append(Finding(BLOCKER, "LC-000",
                               f"태스크 {tid} 의 이벤트가 하나도 없다", tid))
            continue

        ns = _ns(tid)
        if ns in AUTONOMOUS_NS:      # 크론이 만든 리포트 — 사람 태스크가 아니다
            continue

        types = [e["type"] for e in group]

        # LC-001: 생성 이벤트 없이 보고부터 올라온 태스크 (추적 불가)
        genesis = GENESIS.get(ns)
        if genesis and genesis not in types:
            out.append(Finding(BLOCKER, "LC-001",
                               f"{genesis} 없이 이벤트가 진행됨 — 어디서 시작됐는지 추적 불가",
                               tid))

        # LC-003: 정체 — **열린** 태스크가 오래 안 움직임
        # ⚠️ 종료 상태를 빠뜨리면 끝난 태스크가 영원히 '정체'로 잡힌다.
        #    approval.granted(승인)와 debate.concluded(회의 종결)가 빠져 있어서
        #    승인된 태스크도 24시간 뒤 정체 경고를 냈다 (젬또리 리뷰 지적).
        #    tasks.py의 종료 판정과 기준을 통일한다.
        last = max((_parse_ts(e["ts"]) for e in group if _parse_ts(e["ts"])), default=None)
        if last and not (set(types) & CLOSED_TYPES):
            hours = (now - last).total_seconds() / 3600
            if hours >= STUCK_HOURS:
                out.append(Finding(WARN, "LC-003",
                                   f"{int(hours)}시간 무진척 (정체)", tid))

    return out


# ══════════════════════════════════════════════════════════════
#  B. 코드 가드레일 — 우리가 실제로 밟은 실수 패턴
#     각 규칙 옆 주석은 "언제 밟았는지". 재발하면 여기서 걸린다.
# ══════════════════════════════════════════════════════════════
@dataclass
class Rule:
    id: str
    severity: str
    pattern: str
    detail: str
    files: str = r"\.(py|js|html|sh)$"
    # 이 패턴이 같은 줄에 있으면 오탐이므로 통과 (주석·방어코드 자체)
    unless: str = ""


CODE_RULES: list[Rule] = [
    # 3번 밟았다. 셸이 자기가 실행한 명령 문자열을 포함해 매칭돼 자살(exit 144).
    Rule("CG-001", BLOCKER, r"\bp(grep|kill)\b[^\n]{0,15}-f\b",
         "pgrep/pkill -f 는 그 명령을 실행한 셸 자신도 잡는다 (자기매칭 → 자살). "
         "/proc 직접 스캔 + 셸 래퍼 제외를 쓸 것",
         files=r"\.(py|sh)$"),

    # 리뷰어봇이 잡은 XSS. HTML 엔티티가 JS 파싱 전에 디코딩되므로 esc()가 안 먹는다.
    Rule("CG-002", BLOCKER, r"\son\w+\s*=\s*[\"'][^\"']*\$\{",
         "인라인 이벤트 핸들러에 템플릿 값 주입 = XSS. "
         "data-* 속성 + 이벤트 위임을 쓸 것",
         files=r"\.(html|js)$"),

    # watcher가 꺼졌는데 '작업 중'으로 뜨던 모순. 데몬 상태를 이벤트로 추론했다.
    Rule("CG-003", BLOCKER, r"name\s*===?\s*[\"'](watcher|cron)[\"']\s*\)\s*return\s+[\"']working",
         "데몬 봇 상태를 하드코딩했다. 데몬의 상태 SSOT는 **실제 프로세스**다 (procs.py)",
         files=r"\.(js|html)$"),

    # CLAUDE.md T1 철칙 1. 클또리가 agy를 자동 호출하면 지갑이 녹는다.
    Rule("CG-004", BLOCKER, r"^\s*(?!#).*\b(subprocess|os\.system|Popen)\b.*\bagy\b",
         "클또리 코드 경로에서 agy(젬또리) 자동 호출 = T1 위반. "
         "젬또리 호출은 PM이 손으로 하거나 독립 cron(일일 업무)으로만",
         files=r"\.py$"),

    # Discord가 urllib 기본 UA를 403으로 막는다. 두 번 밟았다.
    Rule("CG-005", WARN, r"urlopen\([^)]*discord",
         "Discord는 urllib 기본 UA를 403으로 막는다 — DiscordBot UA 헤더 필수",
         files=r"\.py$"),

    Rule("CG-006", WARN, r"\.innerHTML\s*=\s*[^\"'`\n]*\$\{(?!.*esc\()",
         "innerHTML에 이스케이프 없이 값 주입 — esc() 통과시킬 것",
         files=r"\.(js|html)$"),

    # 지어낸 수치를 대시보드에 남기면 안 된다 (젬또리 체력 62% 예시값 사건)
    Rule("CG-007", WARN, r"(TODO|FIXME|XXX|하드코딩|임시|예시값|더미|mock).*(체력|수치|%|퍼센트)",
         "측정 못 하는 값을 지어내지 말 것 — '미측정'으로 표기",
         files=r"\.(py|js|html)$"),
]


def _strip_comments(text: str, name: str) -> str:
    """주석을 공백으로 치환(줄 수는 보존).

    🔴 없으면 검증관이 주석을 코드로 오인한다. 실제로 밟았다:
       "이전엔 `if (b.name === 'watcher') return 'working'` 로 하드코딩돼 있었다" 는
       **교훈 주석**을 CG-003 위반으로 잡았다. 교훈을 적을수록 더 걸리는 꼴이라
       검증관이 스스로를 못 통과했다.
    """
    def blank(m):                       # 줄바꿈만 남기고 지운다 (줄 번호 유지)
        return "".join(c if c == "\n" else " " for c in m.group(0))

    if re.search(r"\.(js|html)$", name):
        text = re.sub(r"/\*.*?\*/", blank, text, flags=re.S)     # 블록 주석
        text = re.sub(r"(?m)//.*$", blank, text)                 # 라인 주석
        text = re.sub(r"(?s)<!--.*?-->", blank, text)            # HTML 주석
    elif re.search(r"\.(py|sh)$", name):
        text = re.sub(r'(?s)"""(.*?)"""', blank, text)           # 파이썬 docstring
        text = re.sub(r"(?m)(?<!\\)#.*$", blank, text)           # 라인 주석
    return text


def _changed_files() -> list[Path]:
    """working tree + staged 변경 파일."""
    try:
        r = subprocess.run(["git", "diff", "HEAD", "--name-only"],
                           cwd=ROOT, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return []
    out = []
    for name in r.stdout.splitlines():
        p = ROOT / name.strip()
        if p.is_file():
            out.append(p)
    return out


def check_code(paths: list[Path] | None = None) -> list[Finding]:
    """diff 한정 검사. 전체 레포는 훑지 않는다 (CLAUDE.md 철칙 4)."""
    files = paths if paths is not None else _changed_files()
    out: list[Finding] = []

    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = f.relative_to(ROOT) if f.is_relative_to(ROOT) else f

        # audit.py 자신은 규칙 문자열을 품고 있으므로 검사 대상에서 뺀다 (자기매칭!)
        if f.name == "audit.py":
            continue

        code = _strip_comments(text, f.name)      # 주석은 코드가 아니다

        for rule in CODE_RULES:
            if not re.search(rule.files, f.name):
                continue
            for i, line in enumerate(code.splitlines(), 1):
                if not re.search(rule.pattern, line, re.IGNORECASE):
                    continue
                if rule.unless and re.search(rule.unless, line):
                    continue
                out.append(Finding(rule.severity, rule.id, rule.detail, f"{rel}:{i}",
                                   scope="code"))
                break     # 규칙당 파일 1건이면 충분 (노이즈 방지)
    return out


# ══════════════════════════════════════════════════════════════
#  C. 종합
# ══════════════════════════════════════════════════════════════
def audit(task_id: str | None = None, code: bool = True) -> dict:
    findings: list[Finding] = []

    # 결재 게이트일 때(task_id 지정)는 전체 태스크를 다 훑되,
    # **대상 태스크가 아닌 것의 결함은 차단하지 않는다**(global로 강등).
    # 안 그러면 7/10에 남긴 테스트 이벤트 하나가 앞으로의 모든 결재를 영원히 잠근다.
    for f in check_lifecycle(None):
        if task_id and f.where != task_id and f.scope != "global":
            f.scope = "global"
        findings.append(f)

    if code:
        findings += check_code()

    # 차단은 대상 태스크(task) + 이번 변경분(code) 의 blocker 만
    blockers = [f for f in findings
                if f.severity == BLOCKER and f.scope in ("task", "code")]
    warns = [f for f in findings if f.severity == WARN or
             (f.severity == BLOCKER and f.scope == "global")]
    # 배지에 쓰는 경고는 **이 태스크 자신의 것만** 센다.
    # 남의 태스크 위생 경고까지 세면 깨끗한 작업에도 경고 배지가 붙어 배지가 거짓말이 된다.
    own_warns = [f for f in findings
                 if f.severity == WARN and f.scope in ("task", "code")]

    return {
        "ok": not blockers,
        "task_id": task_id,
        "blockers": len(blockers),
        "warns": len(own_warns),
        "hygiene": len(warns) - len(own_warns),   # 남의 태스크·과거 이력 (차단 안 함)
        "findings": [asdict(f) for f in findings],
        "lines": [f.line() for f in findings],
        "checked_at": datetime.now(KST).isoformat(timespec="seconds"),
    }


def gate(task_id: str, summary: str, dept: str = "hq",
         project: str | None = None) -> dict:
    """검증 통과 시에만 결재를 올린다. 막히면 approval.requested를 만들지 않는다."""
    res = audit(task_id)

    if not res["ok"]:
        append_event("audit.failed", "검증관", "qa",
                     f"결재 차단 — blocker {res['blockers']}건",
                     task_id=task_id, project=project)
        res["gated"] = False
        return res

    note = (f"검증 통과 (warn {res['warns']}건)" if res["warns"]
            else "검증 통과 (결함 없음)")
    append_event("audit.passed", "검증관", "qa", note,
                 task_id=task_id, project=project)
    append_event("approval.requested", "클또리", dept, summary,
                 task_id=task_id, requires_approval=True, project=project)
    res["gated"] = True
    return res


def _cli():
    ap = argparse.ArgumentParser(description="검증관 — 결재 게이트")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="검증만 (이벤트 기록 안 함)")
    c.add_argument("--task")
    c.add_argument("--no-code", action="store_true")

    g = sub.add_parser("gate", help="검증 통과 시에만 결재 요청")
    g.add_argument("--task", required=True)
    g.add_argument("--summary", required=True)
    g.add_argument("--dept", default="hq")
    g.add_argument("--project", help="projects.json 등록 id (결재를 프로젝트 축에 연결)")

    a = ap.parse_args()

    if a.cmd == "check":
        res = audit(a.task, code=not a.no_code)
    else:
        # project 오타는 **검사 돌기 전에** 걸러낸다 — 안 그러면 audit 완주 후
        # append_event의 ValueError로 죽어 audit.* 이벤트가 통째로 유실된다
        from events import validate_project
        try:
            validate_project(a.project)
        except ValueError as e:
            print(f"⛔ {e}")
            sys.exit(2)
        res = gate(a.task, a.summary, a.dept, a.project)

    for ln in res["lines"]:
        print(ln)
    if not res["lines"]:
        print("🟢 결함 없음")

    if a.cmd == "gate":
        print()
        print("✅ 결재 올림" if res.get("gated")
              else f"⛔ 결재 차단 — blocker {res['blockers']}건 먼저 고칠 것")

    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    _cli()
