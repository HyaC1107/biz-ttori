# context.md — 현재 진행 상황 스냅샷

> 세션 시작 시 클또리가 **가장 먼저 읽는** 문서. **현재 상태만** 담는다 (1화면 이내 유지).
> 완료 이력은 → [`CHANGELOG.md`](../CHANGELOG.md). 기술 가이드는 → [`stack.md`](stack.md). 협업 규칙은 → [`team-rules.md`](team-rules.md).

---

## 📍 지금 상태

```
워크스페이스 : Biz-Ttori (회사 풀스택/RN & 기획 지원 환경)
현재 단계    : Phase 1 — 멀티에이전트 협업 구조 정비 (거의 완료)
체제         : 2인 (클또리 + 젬또리) + 클또리 내부 분신 / 챗또리(codex) 보류
마지막 작업  : fanbird-broadcast 실기기 검증 세션(2026-07-13). **검증 완료**: 다중 마이크 위치(iOS+Android), Android 블루투스 마이크 SCO(녹음 정상), 레이턴시 자동복구(양 플랫폼), UI(토글버튼·폴드 레이아웃). **오늘 코드 작성(실기기 미검증)**: iOS 블루투스 **재연결**(시작전 연결→해제→재연결) 시 마이크 라벨이 "아이폰 하단"으로 남는 문제 → 라우트 변경 후 즉시+지연(0.5/1.0/1.8s) 재확인 retry로 수정(HFP 마이크가 ~1초 비동기 수립되는 걸 놓치던 문제, `IVSBroadcastController.swift`). **신규 발견(🔴 최우선, 원인 미확정)**: 방송 중 전화 수신 시 송출앱은 방송 유지로 보이나 시청자(close 플레이어)에선 스트림 끊기고 "방송 준비중"만 뜸 → IVS 세션 실제 종료 추정. 코드로 바로 못 고치고 실기기+IVS 콘솔 진단 선행 필요(Android AudioFocus 진단 로그만 보강). **A/V 싱크 저하 대비 구현(코드)**: 최소 비트레이트 하한 1.5M→0.8M(iOS/Android, 방송 정상 시작 확인) + 네트워크 불안정 경고 배너(BroadcastScreen, `networkHealth`가 high/excellent 아니면 저하 판정 — broadcastQuality/recommendedBitrate는 실측상 신호 못 됨). **close 시청자 종료감지 수정(코드)**: 뷰어가 IVS 플레이어 상태로만 종료 감지해 목록 복귀 실패하던 버그 → `Live_Component.tsx`에서 `live_status`(='종료') 5초 폴링 + IVS 이벤트도 live_status 확인 후에만 종료 처리(일시저하 오탐 방지) (2026-07-13, [[daily/260713]])
다음 할 일   : **🔴 전화 인터럽트 시청자 스트림 소실 진단(최우선) — 실기기+IVS 콘솔 동시 관찰**(콘솔 스트림 세션 유지 여부/비트레이트 그래프, logcat `AudioFocusTest focusChange=` 값·GAIN 여부·RetryState 전이) / iOS 블루투스 재연결 라벨 수정 실기기 검증(`[MicRouteFix]` 로그) / A/V싱크 대비 실기기 검증(커스텀 ~1.2M 업링크로 배너 유지·비디오 0.8M 흐름) / close 종료감지 수정 웹 검증 + `TutoLive.tsx` 동일버그 확인 / 오디오인터럽트 iOS 검증 / 발열 S22·Fold7
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

- (없음 — close 로그인 이슈는 이후 세션에서 정상 동작 확인되어 해소)

## 📌 백로그 (급하지 않음)

- **fanbird-broadcast `liveStatus` 판단을 네이티브 세션 실제 상태로** — 현재 JS 모듈 변수 `activeBroadcastSeq`가 유일 근거라 JS 리로드 시 화면이 네이티브 세션과 desync(2026-07-13 Fast Refresh로 관측, dev 아티팩트). 네이티브에 `isSessionActive()`/`getActiveSeq()` 노출(iOS `isBroadcasting` 이미 있음) 후 마운트 시 조회하도록. 프로덕션 JS 리로드 대비. feedback-metro-dev-live-test

## 💤 보류 (실프로젝트/일지 쌓인 뒤 재검토)

- 로컬 벡터 RAG, Docker/Wasm 샌드박스, Dataview 대시보드, context 도메인별(프론트/백/DB) 분리
  → 현재는 데이터량이 적어 premature. friction이 실제로 생기는 시점에 도입.
