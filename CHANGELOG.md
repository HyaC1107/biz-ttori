# CHANGELOG — Biz-Ttori 구축 이력

> 완료된 작업의 **append-only 누적 로그**. 세션 시작 시 읽지 않아도 되는 과거 기록.
> "지금 상태 / 다음 할 일"은 [`memory/context.md`](memory/context.md)에서 관리한다.

---

## 2026-06-30 — Phase 1: 멀티에이전트 협업 구조 정비

- 워크스페이스 디렉토리 `/Users/linkcampus02/biz-ttori` 생성
- `README.md` 작성 (핵심 구성 및 디렉토리 정의)
- `CLAUDE.md` 작성 (AI 협업 지침 및 코딩 표준)
- `triggers.md` 작성 (에이전트 호출 및 PR 게이트 조건)
- 레거시 에이전트 프롬프트 명세서 작성 (`agents/` — coder, reviewer, planner, writer / 참고용)
- `memory/stack.md` (기술 스택 + RN 트러블슈팅), `memory/team-rules.md` (협업 교훈) 작성
- **AI 호출 3단계 정책(지갑 방어) 수립** — CLAUDE.md (T1 사람운전 / T2 자동툴 / T3 분신격리)
  - Agent-to-Agent 자동호출의 토큰폭탄·컨텍스트오염·무한루프 위험 차단
  - 젬또리(agy) 대용량 리서치/검증 = T1 (PM이 직접, 자동화 금지)
- **2인 체제로 전환** — 챗또리(codex) 미사용(보류). 코드리뷰는 클또리 리뷰 분신(작성 분신과 분리, adversarial)이 담당
- **Claude Code 플러그인 2개 설치** (user scope, enabled)
  - `coderabbit` v1.1.1 — cross-model 코드리뷰 (챗또리 공백 보완)
  - `claude-md-management` v1.0.0 — CLAUDE.md/메모리 품질감사·세션교훈 캡처
- **실행 가능한 서브에이전트 5종 구현** (`.claude/agents/`, frontmatter+권한격리)
  - planner(설계,Write❌) / coder(구현✅) / reviewer(검증,Write❌,adversarial) / tester(테스트파일만) / writer(문서,sonnet)
  - coder와 reviewer 분리 = 확증편향 방지
- **T2 자동호출 래퍼 `tools/agy-ask.sh`** — 출력 캡(40줄/2000자) 강제, 단답 전용
- **옵시디언 볼트 정비 (P0/P1)** — 문서 모순 동기화(2인 체제로 triggers/team-rules/README 통일), `context.md` 스냅샷/이력 분리(본 CHANGELOG 신설)
- **슬랙 연동 전략 사양서 작성** — 비즈또리 자체 툴 개발을 위해 일반 프로젝트 문서와 분리된 [specs/slack-integration-spec.md](file:///Users/linkcampus02/biz-ttori/specs/slack-integration-spec.md)에 기획서 작성 및 `memory/context.md` 할 일 업데이트
- **지브레인(G-Brain) 다차원 링크 체계 도입 (정제안)** — G-Brain 원안에서 함정(함수단위 링크 부패 / 글로벌 레이어분할 / 매작업 thought 강제)을 걷어내고 코어만 채택
  - `CLAUDE.md` 🧠 G1~G5 조항 추가 (굵은 링크 / Git-노트 ref / api-specs 통로 / 조건부 의존맵 / 프로젝트축 분할)
  - `memory/api-specs.md` 신설 — FE↔BE 계약 SSOT(G3 통로)
  - `memory/g-brain-map.md` 신설 — 지식 관계 인덱스
  - `tools/gbrain-doctor.sh` 신설 — `[[링크]]` 부패 점검기(코드블록/인라인/`{}` 제외, 현재 링크 8개 0깨짐)
- **(P2) `_templates/` 3종 정합** — 이미 채워져 있던 템플릿을 신규 규칙과 정합화
  - YAML frontmatter 추가(type/status/project/created/tags/related) → Dataview 쿼리 가능 + 태그 체계 실사용
  - G-Brain "관련 노트" 섹션 추가(spec↔api-specs G3, 코드모듈 G1, Git ref G2)
  - 기본 상태값 버그 수정(api-spec/회의록 `완료`→템플릿엔 부적절, spec `진행중`→`초안`)
  - gbrain-doctor 재검증: 링크 17개 0깨짐
- **외장 두뇌(허브) 모델 명문화 (G5 개정)** — "코드는 외부 폴더, 두뇌만 biz-ttori"로 전제 교정 (실코드가 다른 워크스페이스에 있는 실무 반영)
  - `claude`는 항상 biz-ttori에서 기동 → 규칙 로드 보장. 외부 코드는 백틱 절대경로 참조(wikilink는 볼트 내부만)
  - `projects/README.md` 신설(허브 규약·절대경로 포인터), `_templates/project-context-template.md` 신설(`repo_path` 포인터)
  - g-brain-map 연결규약·README 트리 동기화. gbrain-doctor가 작업 중 자기 깨진 링크 1건 포착→수정(도구 효용 입증)
- **젬또리 설계검토(T1) 반영 — 7건 중 3건 선별 적용** (외부 리뷰 적대적 재검증 후 채택)
  - ① **api-specs SSOT 이중화 버그 수정** — 계약 SSOT를 **프로젝트별** `projects/<name>/api-specs.md`로 일원화. 전역 `memory/api-specs.md`는 "인덱스+내부툴 계약"으로 역할 재정의(G3 개정). 잔재 grep 0건
  - ② **G5 기동≠cwd 구분 명시** — 외부 레포 lint/test/build는 그 레포를 cwd로 실행(`cd`/디렉토리 추가), biz-ttori cwd에서 외부 빌드 금지
  - ③ **T3 분신 캡 정직화** — 소프트(프롬프트) 캡임을 명시 + 완화책(좁은 스코프/짧은 리턴/재귀 스폰 금지) 철칙 #5 추가
  - 보강: symlink 트레이드오프 1줄(G5), 링크 남발 금지 가드(G1)
  - **기각 2건**(벡터 RAG '시급', CLAUDE.md 규칙 누실=추정) → `team-rules.md` 교훈5에 재발방지 기록
- **OpenClaw 슬랙 연동 가이드 작성** — 클또리(Claude Code) 학습을 위해 OpenClaw 개념, Biz-Ttori와의 결합 아키텍처, 커스텀 스킬 설계 및 지갑 방어 가이드라인을 담은 [specs/openclaw-integration-guide.md](file:///Users/linkcampus02/biz-ttori/specs/openclaw-integration-guide.md) 기획 문서 추가
  - **하이브리드 운영 전략 보강** — 공식 Slack Claude App(채널 맥락/기획 토론)과 Biz-Ttori x OpenClaw(로컬 빌드/코드 수정)의 역할 경계를 명확히 규정하고 워크플로우 예시 수립
- **Slack 연동 Phase 1 구현 + OpenClaw 검증/교정**
  - `tools/slack-post.sh` 신설 — Incoming Webhook 단방향 알림(Step7 보고용). python3 JSON 인코딩+curl, 가드(플레이스홀더 거부)/배관(실제 Slack 도달 404 검증) 테스트 통과. PM이 `SLACK_WEBHOOK_URL` 입력 시 가동
  - env 정합: `keys/.env.example`+`setup.sh`에 `SLACK_WEBHOOK_URL` 추가(Phase1=웹훅, 봇토큰=Phase2). setup.sh mkdir에 tools/projects/specs 보강
  - **OpenClaw 웹검증** — 실재 확인(오픈소스 게이트웨이, SOUL.md, ClawHub). 단 **자기 LLM 루프를 돎**(게이트웨이 아님) → 원안의 "OpenClaw가 planner/coder 실행" = 두뇌 2개=지갑방어 충돌
  - **가이드 교정** — "두 번째 두뇌"→**leash(배관) 모델**: OpenClaw는 싼 모델·자율루프 OFF·승인버튼, 무거운 사고는 `claude -p`로 셸 위임. 두뇌는 클또리 하나 유지
  - `memory/api-specs.md` 내부툴 `slack-report` ✅구현 갱신, g-brain-map 상태 동기화



