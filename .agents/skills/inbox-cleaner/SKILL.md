---
name: inbox-cleaner
description: memory/inbox.md에 남아있는 젬또리의 팩트체크 리서치 리포트를 오늘 날짜의 daily 일지 하단으로 이관(아카이빙)하고, inbox를 다음 세션을 위해 비워두는 프로세스 청소 비서 스킬입니다.
---

# 📬 inbox-cleaner 스킬 실행 가이드 (젬또리 전용)

이 스킬은 클또리가 젬또리의 팩트체크 결과를 모두 확인하고 세션을 마무리할 때, 공유 메모리(`inbox.md`)의 잔여 텍스트를 오늘 일지로 이관하여 업무 아카이브를 누적하고 우체통을 청소하는 자동화 스킬입니다.

## 🚦 실행 절차

1. **우체통 정리 스크립트 실행:**
   * **명령어:** `./.agents/skills/inbox-cleaner/scripts/clean.js`
   * **역할:** `memory/inbox.md` 파일에 유효한 텍스트가 있는 경우, 이를 읽어 `daily/YYMMDD.md` 일지 끝부분에 보관하고 `inbox.md` 파일을 초기화합니다.
2. **사후 지식 검증:**
   * 파일들이 갱신된 후, `./tools/gbrain-doctor.sh`를 구동하여 링크 정합성에 문제가 없는지 점검합니다.
