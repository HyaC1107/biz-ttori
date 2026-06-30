#!/usr/bin/env bash
#
# tools/agy-ask.sh — 젬또리(agy) T2 자동호출 래퍼 (출력 캡 강제)
#
# 정책: CLAUDE.md "AI 호출 3단계 정책" 참조.
#   - T2(자동/툴): 출력이 짧고 정형화된 "단답형" 질의만 허용. (DB 스키마 조회, 함수 시그니처 확인 등)
#   - 출력 캡(40줄 / 2000자)을 강제해 컨텍스트 오염·토큰 폭탄을 차단한다. (철칙 #2)
#   - 대용량 코드 분석·리서치·문서 검증은 T1 — 반드시 PM이 직접 `agy`를 실행할 것. 이 래퍼로 우회 금지.
#
# 사용법:
#   tools/agy-ask.sh "users 테이블의 컬럼명만 나열해줘"
#
set -euo pipefail

MAX_LINES=40
MAX_CHARS=2000
TIMEOUT="90s"

if [ "$#" -eq 0 ] || [ -z "${1:-}" ]; then
  echo "usage: tools/agy-ask.sh \"<짧은 단답형 질의>\"" >&2
  echo "  주의: 대용량 분석/리서치는 T1(PM 직접 실행) 영역입니다. 이 래퍼는 단답 전용." >&2
  exit 2
fi

PROMPT="$*"

# 단답 강제 가드레일 프롬프트
GUARD="아래 질의에 ${MAX_LINES}줄, ${MAX_CHARS}자 이내로 핵심만 단답형으로 답하라. 서론/요약/잡담 금지. 코드나 표가 필요하면 최소한으로. 확실치 않으면 '불명확'이라고만 답하라.

질의: ${PROMPT}"

# agy 호출 (자체 타임아웃 플래그 사용 — macOS 호환)
RAW="$(agy -p --print-timeout "$TIMEOUT" "$GUARD" 2>&1 || true)"

if [ -z "$RAW" ]; then
  echo "[agy-ask] 빈 응답 또는 호출 실패 — T1(PM 직접 실행)으로 전환을 권장합니다." >&2
  exit 1
fi

# 출력 캡: 줄 수 → 문자 수 순으로 강제
CAPPED="$(printf '%s' "$RAW" | head -n "$MAX_LINES")"
CHARS="$(printf '%s' "$CAPPED" | wc -c | tr -d ' ')"

if [ "$CHARS" -gt "$MAX_CHARS" ]; then
  CAPPED="$(printf '%s' "$CAPPED" | cut -c1-"$MAX_CHARS")"
  printf '%s\n' "$CAPPED"
  echo ""
  echo "[agy-ask] ⚠️ 출력이 캡(${MAX_LINES}줄/${MAX_CHARS}자)을 초과해 잘렸습니다. 이 질의는 T2(단답)에 적합하지 않습니다 — T1(PM 직접 실행)으로 전환하세요." >&2
else
  printf '%s\n' "$CAPPED"
fi
