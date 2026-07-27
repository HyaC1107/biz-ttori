# 🏢 Biz-Ttori — 회사 업무 및 AI 모델 개발 오케스트레이터

이 저장소는 AI 모델 개발(세부 스코프 미정) 업무와 기획, 사내 문서 작성을 자동화하고 관리하기 위한 **AI 에이전트 협업 워크스페이스**입니다. (2026-07-27: React Native/Fullstack 개발 중심에서 전환)

---

## 📋 핵심 구성 요소

| 구성 요소 | 내용 |
|-----------|------|
| **메인 협업 도구** | Obsidian (biz-ttori 폴더를 볼트로 연결하여 문서/로그 관리) |
| **핵심 AIs** | 👑 클또리(Claude Code) — 메인 지휘 + 코딩/문서 + 내부 리뷰 분신  <br> 🔍 젬또리(Antigravity) — 리서치/문서 팩트체크 (T1, PM이 직접 실행)  <br> ~~챗또리(Codex)~~ — **보류 중**, cross-model 검증 필요 시 재도입 |
| **협업 채널** | Slack (향후 slack-bridge 모듈을 통한 알림 및 보고 자동화) |

---

## 📁 디렉토리 구조

```
biz-ttori/
├── CLAUDE.md              ← AI 협업 지침 및 코딩 표준 (핵심)
├── CHANGELOG.md           ← 완료 작업 누적 이력 (append-only)
├── triggers.md            ← 작업 성격별 AI 도구 라우팅 규칙
├── setup.sh               ← 초기 세팅 스크립트 (keys/.env 자동 생성 등)
├── .claude/agents/        ← 실행 가능한 서브에이전트 (frontmatter+권한격리) ★실사용
│    ├── coder.md          ← 코드/실험 구현 (Write✅)
│    ├── reviewer.md       ← adversarial 코드 검토 (Write❌, 작성 분신과 분리)
│    ├── planner.md        ← 기획/설계·요구사항 분석 (Write❌)
│    ├── tester.md         ← 테스트 파일 작성·실행 (제품코드 수정❌)
│    └── writer.md         ← 문서화 및 Slack 요약 보고 (sonnet)
├── agents/                ← 레거시 에이전트 프롬프트 명세 (참고용, README로 안내)
├── tools/                 ← 자동호출 래퍼(T2) + 로컬 유틸리티
│    ├── agy-ask.sh        ← 젬또리 단답형 질의 래퍼 (40줄/2000자 캡)
│    └── gbrain-doctor.sh  ← 지브레인 [[링크]] 부패 점검기 (모델 호출 없음)
├── projects/              ← 외부 프로젝트별 두뇌 (코드는 외부, 두뇌만 볼트) ★G5
│    └── README.md         ← 허브 모델 규약 (절대경로 포인터)
├── specs/                 ← 비즈또리 자체 툴 개발 기획 및 사양서 폴더
├── memory/                ← 세션 연속성을 위한 정보 저장소
│    ├── context.md        ← 현재 진행 상황 스냅샷 (세션 시작 시 첫 읽기, 1화면)
│    ├── api-specs.md      ← 모듈 간 계약 단일 통로 SSOT (G3) ★G-Brain
│    ├── g-brain-map.md    ← 지식 관계 인덱스 (지식 그래프 지도) ★G-Brain
│    ├── stack.md          ← 기술 스택 및 트러블슈팅 가이드 (TBD)
│    └── team-rules.md     ← 누적 협업 교훈 및 규칙
├── _templates/            ← 업무용 표준 문서 템플릿 (YAML frontmatter+G-Brain 링크)
│    ├── spec-template.md             # 기획 및 기능 사양서
│    ├── api-spec-template.md         # API 명세서
│    ├── project-context-template.md  # 외부 프로젝트 컨텍스트(절대경로 포인터)
│    └── meeting-minutes-template.md  # 회의록 및 Slack 공유 포맷
├── keys/                  # .env (시크릿, gitignore 대상)
└── daily/                 # 일일 개발 및 업무 로그 (.md)
```

---

## 🚀 시작하기

1. **Obsidian 볼트 연결**: Obsidian 실행 → `biz-ttori` 폴더를 새 볼트로 엽니다.
2. **세팅 스크립트 실행**:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
3. **업무 기동**:
   터미널에서 `biz-ttori` 폴더로 이동한 뒤 `claude`를 실행하여 클또리를 기동합니다.
