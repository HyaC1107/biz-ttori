# 📋 [설계서] AI 팀 자율 파이프라인 Phase 0 — 가드레일 및 젬또리 연동 설계

이 문서는 `specs/ai-team-autonomous-pipeline.md` 기획서의 **Phase 0(가드레일 구현 및 젬또리 연동)**을 달성하기 위한 구체적인 기술 설계서 및 미결 이슈 권장안입니다.

---

## 1. 💳 크레딧 잔량 하한 가드레일 — 구현 완료 (2026-07-15)

> **방식**: biz-ttori는 **구독형**이라 토큰당 USD 과금이 없다. USD 단가 적산 방식(input×$3 …)은
> **폐기**하고, **5시간 롤링 크레딧 창의 잔량 %**를 읽어 하한에서 신규 spawn을 차단한다.
> **두 봇 모두 독립적으로 게이트한다**(PM 결정) — 클또리 20%, 젬또리 15%. `spawn_queue.claim()`은
> 헤드리스 `claude` 워커를 스폰하므로 클또리 자원이 직접 소모 대상이지만, 팀 전체 가용성 관점에서
> 젬또리 잔량도 별도로 함께 본다.

### 1.0. 선결 검증 결과 — ✅ 가능 확인됨
클또리(Claude Code) 5시간 크레딧 잔량은 `~/.claude/.rate-limits.json`에서 **실측 가능**하다.
Claude Code의 statusLine 훅이 stdin으로 받는 `rate_limits.five_hour.used_percentage`를
`~/.claude/statusline.py`가 이 파일에 스냅샷으로 기록한다 — `dashboard/engine/health.py`의
`_claude()`가 이미 같은 파일을 읽어 대시보드 BOT HP 패널에 표시 중이던 것과 동일 소스.
추정치가 아니라 Claude Code 자신이 보고하는 값이라 신뢰도 높음.

### 1.1. 클또리 크레딧 게이트 — `check_claude_credit_limit()` (`spawn_queue.py`)
별도 설정 파일(`spend-limit.json`) 없이, 이미 존재하는 `~/.claude/.rate-limits.json` 스냅샷을
그대로 재사용한다(중복 설정 불필요).

```python
CLAUDE_SNAP = Path.home() / ".claude" / ".rate-limits.json"
CLAUDE_CREDIT_MIN_PCT = 20.0

def check_claude_credit_limit() -> bool:
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
```

> `check_gemttori_quota_limit()`과 동일 컨벤션으로 통일. (당초 §1의 "실패 시 차단" 초안은
> 기각 — 세션 미기동 같은 정상 상태에서 영구 차단되는 걸 막기 위함.)

### 1.2. 젬또리 크레딧 게이트 — `check_gemttori_quota_limit()` (기존 구현 유지)
젬또리(젬또리 자기보고 → `company/bot_health.json`)의 `remaining_pct`가 **15% 미만**이면 차단
(PM이 젬또리에게 직접 지시한 값 — 클또리의 20%와 다른 게 정상, 봇마다 별도 임계치).
`resets_at` 지난 경우 자동 통과. 구현은 그대로 유지, 수정 없음.

### 1.3. `claim()` 호출 순서
```python
if not check_claude_credit_limit():   # 클또리 20%
    return False
if not check_gemttori_quota_limit():    # 젬또리 15%
    return False
```

검증: 실측 스냅샷(당시 five_hour 사용 8% → 잔량 92%)으로 `True` 확인, 임계치 이하(85% 사용 시뮬레이션)로 `False` 확인.

---

## 2. 🚨 "위험 행동" 판정 규칙 설계

워커가 수행하려는 명령어나 작업 요약 중 위험 요소가 존재하면 즉시 **결재 요청(`approval.requested`)** 상태로 전이시킵니다.

### 2.1. 위험 행동 블랙리스트 패턴 정의 (append-only 축적 — PM 결정 2026-07-15)
- **초기 커맨드 패턴 (Regex)**: `git push`, `rm -rf`, `deploy`, `publish`, `delete`, `drop`
- **운영 방식**: 텍스트 패턴 매칭으로 시작하고, **사고가 날 때마다 패턴을 계속 추가**하는
  append-only 리스트로 운영한다. 정교한 분류는 지금 불필요(오탐=과잉 차단이 안전한 방향).
- **적용 대상**: `tasks.py` 또는 `spawn_queue.py`에서 claim한 직후, 태스크 프롬프트나 작업 내역에 위 패턴이 존재하면 `requires_approval = True` 플래그를 자동으로 주입합니다.

---

## 3. 🔍 젬또리 사용량 자기 보고 & 감사 로그 연동

젬또리(Antigravity CLI)는 샌드박스 내부에서 기동되므로, **Lifecycle Hooks**를 사용해 주기적으로 사용량을 업데이트하고 종료 시점 이벤트를 `events.jsonl`에 기록하게 만듭니다.

### 3.1. 훅 정의 (`.agents/hooks.json`)
젬또리가 도구를 호출한 직후(`PostToolUse`) 또는 매 실행 종료 시(`Stop`)에 백그라운드 헬퍼 스크립트를 트리거합니다.

```json
{
  "gemttori-usage-report": {
    "PostToolUse": [
      {
        "matcher": "run_command",
        "hooks": [
          {
            "type": "command",
            "command": "python3 tools/report-gemttori-quota.py",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 tools/append-gemttori-done.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

### 3.2. 헬퍼 스크립트 구현 스펙

#### ① 사용량 보고 (`tools/report-gemttori-quota.py`)
- **작동 원리**: 에이전트 루프가 돌 때마다 API 호출 카운트를 늘리거나, 매 10회 누적 호출 시점(혹은 15분 경과 시) 젬또리의 `/credits` 출력 또는 API 잔량을 긁어옵니다.
- **보고 툴 실행**: `python3 dashboard/engine/health.py report --bot 젬또리 --remaining <잔량_pct> --window "5시간" --note "Hooks 자동 자가보고"`

#### ② 감사 로그 기록 (`tools/append-gemttori-done.py`)
- **작동 원리**: 젬또리 세션이 완료/종료될 때 `Stop` 훅이 트리거되면, 세션 내 누적 변경된 작업 요약을 `company/events.jsonl`에 기록합니다.
- **보고 툴 실행**: `python3 dashboard/engine/events.py append --type bot.done --actor 젬또리 --dept ops --summary "젬또리 CLI 세션 작업 완료 및 감사 로그 자동 기록"`

---

## ✅ 4. 미결 이슈 — PM 최종 결정 (2026-07-15)

> 아래는 젬또리 권장안에 PM이 결정을 내려 확정한 결과다. (원 권장안은 참고로 병기)

| 미결 이슈 | **PM 최종 결정** | 비고 (원 젬또리 권장안 대비) |
| :--- | :--- | :--- |
| **① 상한** | **클또리 20% / 젬또리 15%, 봇별 독립 게이트** (USD 계산 폐기) | 구독형이라 USD 단가 무의미 → 젬또리 "$10/day" 안 기각. 두 봇 임계치가 다른 게 정상(각각 PM이 별도 지시). §1 참조 — 구현 완료. |
| **② 위험 행동 판정** | **텍스트 패턴 블랙리스트 + append-only 축적** | 젬또리 권장안 채택. 사고 날 때마다 패턴 추가. |
| **③ 재시도 정책** | **실패 유형별 분기** — 인프라/일시적 실패만 **클린 리셋 후 1회** 자동 재시도, **리뷰 블로커/로직 실패는 재시도 없이 즉시 PM 에스컬레이션** | 젬또리 "블라인드 1회 재시도"를 보정: 같은 프롬프트 재시도는 재실패·크레딧 낭비. 재시도는 반드시 worktree/브랜치 리셋 후(부분 편집 중첩 방지). |
| **④ Phase 1 시범 프로젝트** | **biz-ttori 자체 툴로만 시작 — 실프로젝트(fanbird/close) 금지** | 신규 결정. fanbird 앱스토어 배포 직전이라 폭발 반경 회피. 후보: gbrain-doctor 링크점검, 일지 인덱스 정리, g-brain-map 갱신. 검증 후 실프로젝트는 읽기전용/분석부터 승격. |
| **⑤ 프레임워크 도입** | **LiteLLM/LangGraph 기각, 파일 기반 자체 구현** | 젬또리 권장안 채택. LiteLLM은 USD 예산 프록시라 구독형과 불일치까지 더해 기각 근거 보강. |
