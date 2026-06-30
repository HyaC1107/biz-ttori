# [가이드/사양서] Biz-Ttori x OpenClaw 슬랙 연동 가이드

> **작성일**: 2026-06-30 | **작성자**: 젬또리 (Antigravity)
> **태그**: #type/spec #status/진행중 #project/biz-ttori
> **배포여부**: is_public: false

이 문서는 지휘자 에이전트인 **클또리(Claude Code)**가 자율형 에이전트 프레임워크인 **OpenClaw**의 개념을 이해하고, 두 도구를 결합하여 Slack 연동 환경을 구축하는 방법을 정의합니다.

---

## ⚠️ 클또리 검증 & 교정 (2026-06-30)

> 젬또리 원안을 **웹 검증 후 적대적으로 재검토**(team-rules 교훈5)한 결과. 원안은 대체로 정확했으나 **아키텍처에 지갑방어 충돌**이 있어 교정함.

- **OpenClaw 실재 확인 ✅** — 오픈소스 self-hosted 게이트웨이(전 Clawdbot/Moltbot), `SOUL.md`(우리 CLAUDE.md 격), ClawHub 스킬 레지스트리. ([github.com/openclaw/openclaw](https://github.com/openclaw/openclaw), [docs.openclaw.ai](https://docs.openclaw.ai/concepts/agent))
- **🚨 결정적 사실**: OpenClaw는 *"single embedded agent runtime — model discovery, prompt assembly... one integrated runtime surface"* 로, **자기 LLM으로 직접 추론하는 독립 에이전트**다. Claude Code로 위임하는 단순 게이트웨이가 **아니다.**
- **따라서 원안대로 "OpenClaw가 planner/coder를 돌린다"고 하면 두뇌가 2개** → OpenClaw 자체 LLM 루프 = **우리 T2/T3 캡 밖의 비용 센터** = 지갑방어 정면충돌.
- **교정 원칙**: OpenClaw를 **"두 번째 두뇌"로 쓰지 않는다.** 아래 *leash(배관) 모델*로만 도입한다. 두뇌는 클또리 하나로 유지.
- **Phase 1(단방향 보고)은 OpenClaw 0% 불필요** → `tools/slack-post.sh`(웹훅)로 이미 구현 완료. OpenClaw는 Phase 2(양방향)에서만 검토.

### 🔒 OpenClaw Leash(배관) 모델 — 도입 시 필수 제약
```
OpenClaw 코어 모델  → Haiku 등 싼 모델 (라우팅/파싱 전용)
OpenClaw 자율 루프  → OFF / 턴 수 상한 (멀티스텝 자율 추론 금지)
OpenClaw 스킬       → 우리 결정론적 자산만 호출:
   · context.md 읽기/쓰기 (파일 I/O, LLM 추론 X)
   · agy-ask.sh / 기타 tools (T2 캡 그대로)
   · 무거운 사고는 셸 위임: `claude -p "..."` (← 진짜 두뇌는 여기)
실행 게이트        → run_*류는 [승인]/[반려] 버튼 통과 후에만 셸 실행
```

---

## 1. 🤖 OpenClaw 핵심 개념 (클또리 참조용)

**OpenClaw**는 로컬 파일 시스템 및 터미널 제어 권한을 가진 자율형 AI 에이전트 실행 런타임입니다.

### 핵심 구조
1. **에이전트 코어 (Agent Core)**: 대규모 언어 모델(LLM)과 로컬 OS/환경을 중재하는 핵심 실행기입니다.
2. **채널 커넥터 (Channel Connectors)**: Slack, Discord, Telegram 등 메시징 플랫폼과 실시간으로 이벤트를 주고받는 소켓/웹훅 리스너입니다.
3. **스킬/플러그인 시스템 (ClawHub)**: 에이전트가 호출할 수 있는 도구(Tools)의 집합입니다. Python/JS 등으로 스킬을 정의하여 에이전트의 기능을 확장합니다.
4. **자율 루프 (Execution Loop)**: 사용자의 지시를 수신하면 계획 수립(Plan) -> 도구 실행(Act) -> 결과 관찰(Observe) 단계를 자율적으로 반복합니다.

---

## 2. 🏗️ Biz-Ttori ↔ OpenClaw 결합 아키텍처

비즈또리의 구조적 지식(Obsidian, `CLAUDE.md`, `context.md`)과 OpenClaw의 상시 구동 및 Slack 수신 능력을 결합합니다.

```
                  ┌──────────────────────────────────────────┐
                  │                사내 Slack                │
                  └────────────────────┬─────────────────────┘
                                       │ (1) 이벤트 수신 / (4) 메시지 송신
                                       ▼
                  ┌──────────────────────────────────────────┐
                  │                 OpenClaw                 │
                  │  (Slack Listener / Agent Runtime Daemon) │
                  └────────────────────┬─────────────────────┘
                                       │ (2) Custom Skill 호출
                                       ▼
                  ┌──────────────────────────────────────────┐
                  │      Biz-Ttori Workspace (로컬)           │
                  │  - memory/context.md (상태 정보)          │
                  │  - tools/ (T2 래퍼 실행)                 │
                  │  - .claude/agents/ (서브에이전트 실행)    │
                  └──────────────────────────────────────────┘
```

### 역할 분담 (⚠️ leash 모델 기준 — 상단 교정 참조)
* **OpenClaw (배관 전용)**: Slack API 연동, 상시 대기 데몬, 인터랙티브 버튼 핸들링, 세션 관리. **자기 LLM으로 업무를 추론하지 않는다** — 멘션을 파싱해 알맞은 스킬(=우리 툴 셸 호출)로 라우팅만.
* **클또리 (유일한 두뇌)**: 실제 기획/코드/리뷰 추론은 OpenClaw 스킬이 `claude -p`로 셸 위임. OpenClaw는 그 결과를 슬랙에 중계만.
* **Biz-Ttori (지식/규칙)**: `memory/`·`CLAUDE.md`·G-Brain·템플릿 = 두뇌가 참조하는 외장 지식.

---

## 3. 🛠️ 연동 스킬 (`biz-ttori-skill`) 설계 사양

OpenClaw에 탑재할 커스텀 스킬을 개발하여 비즈또리 워크스페이스를 조작하도록 만듭니다.

### 주요 도구 목록 (Tools)
1. **`read_workspace_status`**
   * **설명**: `memory/context.md` 파일의 현재 진행 상태("지금 상태", "다음 할 일", "블로커")를 읽어옵니다.
   * **출력**: 슬랙 Block Kit에 적합한 포맷으로 변환된 텍스트.
2. **`append_workspace_todo`**
   * **설명**: `memory/context.md` 파일의 "⏳ 다음 할 일" 목록에 사용자가 슬랙으로 지시한 태스크를 추가합니다.
   * **인자**: `task_description (string)`
3. **`run_ttori_agent`** (⚠️ 위임 전용 — OpenClaw가 직접 추론 금지)
   * **설명**: 슬랙 지시를 **클또리에 셸 위임**한다. `claude -p "<instruction>"`을 biz-ttori cwd에서 실행하거나, 단답이면 `agy-ask.sh`(T2 캡)를 호출. OpenClaw는 결과 텍스트를 슬랙 스레드로 중계만.
   * **인자**: `instruction (string)`, (선택) `mode: "claude" | "agy"`
   * **🚨 가드레일**: ① **[승인] 버튼 통과 후에만** 셸 실행 ② `agy` 경로는 40줄/2000자 캡 그대로 ③ OpenClaw 자체 멀티스텝 자율 루프 OFF(1요청=1위임) ④ 분신의 재귀 스폰 금지. **OpenClaw의 LLM이 업무를 "생각"하게 두지 않는다 — 생각은 `claude -p`가 한다.**

---

## 📅 4. 단계별 구현 마일스톤

### Phase 1: OpenClaw 환경 구성 및 슬랙 봇 연결
* 로컬 머신에 OpenClaw를 설치하고, Slack Developer Portal에서 Bot App을 생성하여 토큰 발급.
* OpenClaw 설정 파일에 슬랙 토큰을 연동하여 특정 채널에서 멘션 대기 상태 활성화.

### Phase 2: 커스텀 `biz-ttori-skill` 작성
* OpenClaw 스킬 디렉토리에 `biz_ttori_skill.py` (또는 JS 파일) 작성.
* `memory/context.md` 경로를 절대경로로 파싱하여 파일 Read/Write 기능 구현.
* 슬랙에서 `/ttori status` 또는 `@봇 status`를 쳤을 때 context 요약이 리턴되는지 검증.

### Phase 3: 에이전트 트리거 및 대화 인터랙티브 승인
* OpenClaw가 슬랙의 특정 이벤트(예: `@봇 리뷰해줘`)를 수신했을 때, 비즈또리의 `tools/agy-ask.sh`나 `.claude/agents/`를 구동하는 연동부 개발.
* 실행 전 슬랙에 **[승인] / [반려]** 버튼을 띄우는 OpenClaw Interactive Flow 연결.

---

## 🧠 5. 하이브리드 운영 전략 (공식 Slack Claude App x Biz-Ttori)

공식 Slack Claude App(팀 협업/브레인)과 Biz-Ttori x OpenClaw(로컬 실행/개발자)의 협업 바운더리를 결합하여 생산성을 극대화합니다.

### 1) 역할 정의 및 경계선
* **공식 Slack Claude App (@Claude)**:
  * **바운더리**: 슬랙 클라우드 & 채널 맥락.
  * **주요 역할**: 실시간 대화 흐름 인지, 여러 팀원과의 스펙 브레인스토밍, 채널 대화 및 업로드된 파일 요약.
* **Biz-Ttori x OpenClaw (@Biz-Ttori)**:
  * **바운더리**: 로컬 머신 파일 시스템 & 터미널 환경.
  * **주요 역할**: 로컬 소스 코드 직접 수정, 테스트/린터/빌드 실행, 구조적 지식 데이터베이스(`memory/`) 조작 및 배포 관리.

### 2) 하이브리드 워크플로우 예시
1. **토론 & 요약 (클라우드)**:
   * 팀원들이 슬랙 채널에서 공식 `@Claude`를 태그해 새로운 기능에 대한 마일스톤과 스펙 설계안을 논의하고 합의안을 도출합니다.
2. **컨텍스트 이주 및 태스크 할당**:
   * PM이 해당 합의안이나 요약 스레드를 복사하여 `@Biz-Ttori`에게 전달하며 기획서 작성 및 구현을 지시합니다.
   * 예: `@Biz-Ttori 아래 합의된 스펙 기준으로 specs/ 하위에 기획서 적고 `coder` 에이전트 띄워서 코드 구현해줘.`
3. **로컬 실행 및 피드백 (로컬)**:
   * 로컬 OpenClaw가 멘션을 감지하여 비즈또리 워크스페이스에서 `planner`와 `coder` 서브에이전트를 순차 실행합니다.
   * 수정된 코드를 로컬 환경에서 테스트하고 검증(린터/타입)을 성공한 뒤, 결과를 슬랙 스레드 답글로 완성 보고합니다.

---

## 💡 클또리(Claude Code) 가이드라인

1. **개발 시 파일 절대경로 확인**: OpenClaw 스킬을 작성할 때 비즈또리 워크스페이스는 항상 절대경로(예: `/Users/linkcampus02/biz-ttori`) 기준으로 지정해야 경로 꼬임을 막을 수 있습니다.
2. **T2/T3 규칙 준수**: OpenClaw가 비즈또리 툴을 구동하도록 래퍼를 짤 때, 출력 캡(최대 40줄) 및 무한 루프 가드레일이 코드 레벨에서 안전장치로 작동하도록 작성하세요.
3. **하이브리드 바운더리 준수**: 클또리는 외부 프로젝트 빌드/테스트 시 본 가이드라인의 하이브리드 경계선을 고려해 로컬 실행에만 집중하고, 슬랙 채널의 거시적 맥락 파악은 공식 `@Claude` 앱과의 복사/이주 연동을 통해 해결하도록 코드를 유도합니다.
