#!/usr/bin/env bash
#
# tools/slack-post.sh — Slack 단방향 알림 (Phase 1, Incoming Webhook)
#
# 정책: 모델 호출 없는 로컬 유틸리티(보내기 전용) → 출력 캡 불필요.
#   - CLAUDE.md 업무 프로세스 "Step 7. SLACK REPORT"에서 요약본을 채널에 자동 포스팅.
#   - 봇 토큰 불필요. `keys/.env`의 SLACK_WEBHOOK_URL만 사용.
#
# 사용법:
#   tools/slack-post.sh "오늘 작업: 슬랙 연동 Phase 1 완료 ✅"
#   cat daily/2026-06-30.md | tools/slack-post.sh        # stdin도 가능
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 1) 웹훅 URL 로드 (환경변수 우선, 없으면 keys/.env에서 안전 파싱 — source 안 함)
WEBHOOK="${SLACK_WEBHOOK_URL:-}"
if [ -z "$WEBHOOK" ] && [ -f "$ROOT/keys/.env" ]; then
  WEBHOOK="$(grep -E '^SLACK_WEBHOOK_URL=' "$ROOT/keys/.env" | head -n1 | cut -d= -f2-)"
  WEBHOOK="${WEBHOOK%\"}"; WEBHOOK="${WEBHOOK#\"}"   # 양끝 따옴표 제거
fi

if [ -z "$WEBHOOK" ] || printf '%s' "$WEBHOOK" | grep -q 'XXX/YYY/ZZZ'; then
  echo "[slack-post] SLACK_WEBHOOK_URL이 설정되지 않았습니다 (keys/.env 확인)." >&2
  echo "  Slack → 앱 'Incoming Webhooks' → 채널 선택 → 발급된 URL을 keys/.env에 입력하세요." >&2
  exit 2
fi

# 2) 메시지 수집 (인자 우선, 없으면 stdin)
if [ "$#" -gt 0 ]; then
  MSG="$*"
else
  MSG="$(cat)"
fi
if [ -z "${MSG//[[:space:]]/}" ]; then
  echo "[slack-post] 보낼 메시지가 비어 있습니다." >&2
  exit 2
fi

# 3) JSON 페이로드 생성 (python3로 안전 인코딩 — 따옴표/개행/유니코드 처리)
if ! command -v python3 >/dev/null 2>&1; then
  echo "[slack-post] python3가 필요합니다 (JSON 인코딩용)." >&2
  exit 1
fi
PAYLOAD="$(MSG="$MSG" python3 -c 'import os,json; print(json.dumps({"text": os.environ["MSG"]}))')"

# 4) 전송 (curl). Slack은 성공 시 본문 "ok" + HTTP 200 반환
RESP="$(curl -sS -X POST -H 'Content-type: application/json' \
        --data "$PAYLOAD" "$WEBHOOK" -w $'\n%{http_code}' 2>&1)" || {
  echo "[slack-post] 전송 실패(네트워크/curl 오류)." >&2; exit 1; }

CODE="$(printf '%s' "$RESP" | tail -n1)"
BODY="$(printf '%s' "$RESP" | sed '$d')"

if [ "$CODE" = "200" ]; then
  echo "[slack-post] ✅ 전송 완료 (HTTP 200, ${#MSG}자)"
  exit 0
else
  echo "[slack-post] ❌ 전송 실패 (HTTP ${CODE}): ${BODY}" >&2
  exit 1
fi
