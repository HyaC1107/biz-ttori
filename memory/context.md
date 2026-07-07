# context.md — 현재 진행 상황 스냅샷

> 세션 시작 시 클또리가 **가장 먼저 읽는** 문서. **현재 상태만** 담는다 (1화면 이내 유지).
> 완료 이력은 → [`CHANGELOG.md`](../CHANGELOG.md). 기술 가이드는 → [`stack.md`](stack.md). 협업 규칙은 → [`team-rules.md`](team-rules.md).

---

## 📍 지금 상태

```
워크스페이스 : Biz-Ttori (회사 풀스택/RN & 기획 지원 환경)
현재 단계    : Phase 1 — 멀티에이전트 협업 구조 정비 (거의 완료)
체제         : 2인 (클또리 + 젬또리) + 클또리 내부 분신 / 챗또리(codex) 보류
마지막 작업  : FMS 자재관리 — 자재명/종류/규격·창고이름 '@' 입력 차단 + 이력조회 필터 구분자 ',' → '@' 변경 (2026-07-07, 계약: [[projects/FMS/api-specs]])
다음 할 일   : fanbird-broadcast iOS 실기기 검증(블로커) / Slack 웹훅 실전송 / FMS worker 필터 '@' 리스크 (문제 시 대응 보류)
```

## ⏳ 다음 할 일 (우선순위 순)

- [x] **(P2) `_templates/` 3종 정합** — YAML frontmatter + G-Brain 링크섹션 + 기본상태 버그 수정 (spec/api-spec/meeting-minutes)
- [ ] (채택①) 실프로젝트 연동 시 Postgres/GitHub **MCP 서버** 연결 (쉘 DB조회 대체)
- [~] **첫 실프로젝트 = fanbird-broadcast(RN 송출앱)** 연동 진행 중 — Android 실기기 방송 E2E 완료(2026-07-06, [[daily/260706]]). 남음: iOS 검증, 9파일 커밋(PM 승인 대기), 채팅 고도화·Foreground Service(젬또리 리포트)
- [x] Slack webhook 및 OpenClaw 연동 가이드 작성 ([slack-integration-spec.md](file:///Users/linkcampus02/biz-ttori/specs/slack-integration-spec.md), [openclaw-integration-guide.md](file:///Users/linkcampus02/biz-ttori/specs/openclaw-integration-guide.md))
- [x] **Slack 연동 Phase 1 구현** — `tools/slack-post.sh`(웹훅 단방향). ⚠️ PM이 `keys/.env`에 `SLACK_WEBHOOK_URL` 입력해야 실전송됨
- [ ] **(PM)** Slack Incoming Webhook URL 발급 → `keys/.env` 입력 → `tools/slack-post.sh "테스트"` 실전송 확인
- [ ] (Phase 2) OpenClaw **leash 모델**로 양방향 연동 — 두뇌는 claude, OpenClaw는 배관만 (specs/openclaw-integration-guide.md)
- [ ] `daily/` 첫 업무 일지 작성 시작

## 🚧 블로커 / 결정 대기

- **iOS 실기기 검증 불가** — Apple 개발자 계정 인증 문제로 Xcode 실기기 테스트가 막힘. → 계정 인증 해결 전까지 fanbird-broadcast 배포 준비(Android 마켓 심사 포함) 보류. (2026-07-07)

## 💤 보류 (실프로젝트/일지 쌓인 뒤 재검토)

- 로컬 벡터 RAG, Docker/Wasm 샌드박스, Dataview 대시보드, context 도메인별(프론트/백/DB) 분리
  → 현재는 데이터량이 적어 premature. friction이 실제로 생기는 시점에 도입.
