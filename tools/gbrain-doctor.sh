#!/usr/bin/env bash
#
# tools/gbrain-doctor.sh — 지브레인 [[wikilink]] 무결성 점검기
#
# 정책: CLAUDE.md "🧠 지브레인(G-Brain)" 규칙(G1) 보조 장치.
#   - 볼트의 모든 [[링크]]가 실재 노트를 가리키는지 검사한다.
#   - 깨진 링크 = 거짓말하는 지식 = 환각 소스 → 발견 즉시 수정/제거.
#   - Obsidian과 동일하게 "노트 이름(basename)"으로 해석한다. (경로/별칭/헤딩은 정규화)
#
# 사용법:  tools/gbrain-doctor.sh
# 종료코드: 0 = 정상, 1 = 깨진 링크 있음, 2 = 사용 오류
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# 점검 대상 .md (의존성·git·옵시디언 메타 제외)
NOTES="$(find . -type f -name '*.md' \
  -not -path './node_modules/*' \
  -not -path './.git/*' \
  -not -path './_templates/*' \
  -not -path './.obsidian/*')"

if [ -z "$NOTES" ]; then
  echo "[gbrain-doctor] 점검할 .md 노트가 없습니다." >&2
  exit 2
fi

# 볼트 내 모든 노트의 basename 목록 (Obsidian 링크 해석 기준)
BASENAMES="$(printf '%s\n' "$NOTES" | sed 's#.*/##')"

TOTAL=0
BROKEN=0

while IFS= read -r f; do
  # 실제 링크만 보도록 코드 영역을 제거한다:
  #   ① ``` 펜스 코드블록 통째 제거  ② 인라인 `code` 스팬 제거
  # (문서의 예시 [[링크]]/[[auth.ts]] 등을 오탐하지 않기 위함)
  CONTENT="$(awk 'BEGIN{inblk=0} /^[[:space:]]*```/{inblk=!inblk; next} inblk==0{print}' "$f" \
             | sed 's/`[^`]*`//g')"
  LINKS="$(printf '%s\n' "$CONTENT" | grep -oE '\[\[[^]]+\]\]' 2>/dev/null || true)"
  [ -z "$LINKS" ] && continue

  while IFS= read -r raw; do
    [ -z "$raw" ] && continue
    t="${raw#\[\[}"; t="${t%\]\]}"   # [[ ]] 제거
    t="${t%%|*}"                      # 별칭(alias) 제거
    t="${t%%#*}"                      # 헤딩(#) 제거
    t="$(printf '%s' "$t" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    [ -z "$t" ] && continue           # 순수 헤딩 링크 [[#sec]] 스킵
    case "$t" in *"{"*|*"}"*) continue;; esac  # 템플릿 자리표시자 {..} 스킵
    case "$t" in *.png|*.jpg|*.jpeg|*.gif|*.pdf) continue;; esac  # 이미지/미디어 파일 스킵

    TOTAL=$((TOTAL + 1))
    base="$(basename "$t")"           # 경로형 [[a/b/note]] → note
    case "$base" in *.md) ;; *) base="$base.md";; esac

    if ! printf '%s\n' "$BASENAMES" | grep -Fxq "$base"; then
      echo "❌ ${f#./} : 깨진 링크 [[${t}]]"
      BROKEN=$((BROKEN + 1))
    fi
  done <<EOF
$LINKS
EOF
done <<EOF
$NOTES
EOF

echo "---"
echo "점검 링크 ${TOTAL}개 / 깨진 링크 ${BROKEN}개"
if [ "$BROKEN" -eq 0 ]; then
  echo "✅ 모든 [[링크]] 정상."
  exit 0
else
  echo "⚠️  깨진 링크를 수정하거나 제거하세요 (링크 부패 = 환각 소스)." >&2
  exit 1
fi
