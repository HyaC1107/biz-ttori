---
type: spec
status: 초안
project: "BTD (biz-ttori for Developer)"
created: "2026-07-20"
updated: "2026-07-20"
author: "PM & 클또리"
is_public: false
confidential: true   # 깃 원격 푸시 스킵
tags: [type/spec, status/초안, project/BTD, layer/extraction]
related: ["[[BTD-세부1-팩규격]]", "[[BTD-세부2-모노레포]]", "[[BTD-세부3-셋업마법사]]"]
---

# 🧬 BTD 세부기획 4 — 뼈대 추출 계획

> **목적**: "설계"를 "실제 파일 이동"으로. 현재 biz-ttori 파일을 → `@btd/core/assets/skeleton`(①) / `packs/fullstack-rn`(②) / 버림·③로 **파일 단위 매니페스트**로 확정한다.
> **원칙(중요)**: 추출 시 **사용자·프로젝트 고유물은 반드시 스트립**한다(close/fanbird/FMS·PM·젬또리·biz-ttori 고유명 → 제네릭화). 배포물엔 "특정 사용자 흔적"이 남으면 안 됨.

---

## 1. CLAUDE.md 슬롯 분해 (제일 까다로움)

현재 통짜 CLAUDE.md를 **3조각**으로 쪼개 세부2 Q1 슬롯에 매핑한다.

| CLAUDE.md 섹션 | 버킷 | 목적지 / 슬롯 |
|:---|:---:|:---|
| 🧠 G-Brain 규칙(G1~G5) | ① | `skeleton/rules/gbrain.md` → `{{SKELETON_RULES}}` **(불변 핵심)** |
| 💰 AI 호출 3단계(T1/T2/T3) | ① | `skeleton/rules/ai-call-tiers.md` → `{{SKELETON_RULES}}` |
| 🔍 검색 품질(S1~S3) | ① | `skeleton/rules/search-quality.md` → `{{SKELETON_RULES}}` |
| 🎭 업무 표준 프로세스(Step0~6) | ① | `skeleton/rules/workflow.md` → `{{SKELETON_RULES}}` |
| 문서화 규칙 §3(문서 인덱스·Quartz 등) | ① | `skeleton/rules/docs.md` → `{{SKELETON_RULES}}` |
| 작업일지 규약 §5·§6(메커니즘) | ① | `skeleton/rules/worklog.md` → `{{SKELETON_RULES}}` (단, "close/fanbird만" 같은 프로젝트명은 스트립) |
| 개발 규칙 §1(React/RN) | ② | `packs/fullstack-rn/rules/react-native.md` → `{{PACK_RULES}}` |
| 개발 규칙 §2(Fullstack API/DB) | ② | `packs/fullstack-rn/rules/fullstack.md` → `{{PACK_RULES}}` |
| 🚦 도구 라우팅(메커니즘) | ① | skeleton (단, "젬또리/agy" 고유명은 `{{TEAM_CONFIG}}`로 치환 변수화) |
| 팀 구성원 표(클또리/젬또리/…) | ③ | `agents.config.yaml` + `{{TEAM_CONFIG}}` (배포 안 함, init이 생성) |
| §4 Slack 연동 | ③ | 옵션 통합(현재 미사용) → `agents.config`의 integrations |

> 최종 CLAUDE.md = `{{SKELETON_RULES}}`(뼈대 조각 concat) + `{{PACK_RULES}}`(팩 조각) + `{{TEAM_CONFIG}}`(사용자 팀). init 스텝5에서 슬롯 조립.

---

## 2. 파일 단위 추출 매니페스트

### → ① `@btd/core/assets/skeleton/` (불변 뼈대)
| 현재 위치 | 목적지 | 변환 |
|:---|:---|:---|
| `tools/gbrain-doctor.sh` | `core/`(로직) | bash→TS 포팅(세부5에서 명세) |
| `.agents/skills/{gbrain-healer, gbrain-map-sync, inbox-cleaner}` | `skeleton/skills/` | 그대로(고유명 점검) |
| `.agents/AGENTS.md` | `skeleton/AGENTS.md` | 협업 규칙 제네릭화 |
| `.agents/hooks.json`, `.agents/scripts/auto-logger.js` | `skeleton/hooks/` | 경로 변수화 |
| `memory/{context, g-brain-map, api-specs, inbox, outbox, team-rules}.md` | `skeleton/memory/` | **내용 비우고 스키마/헤더만**(빈 스캐폴드) |
| `company/*.json` | `skeleton/company/` | **스키마만**(런타임값 제거) |
| `_templates/{daily, spec, meeting-minutes, handover, troubleshooting, project-context, api-spec}-template.md` | `skeleton/templates/` | 프로젝트명 예시 제네릭화 |
| CLAUDE.md 마스터 템플릿(슬롯 포함) | `skeleton/CLAUDE.template.md` | §1에서 조립 |

### → ② `packs/fullstack-rn/` (레퍼런스 팩)
| 현재 위치 | 목적지 | 변환 |
|:---|:---|:---|
| CLAUDE.md §1·§2 | `rules/{react-native, fullstack}.md` | 조각화 |
| `memory/stack.md` | `stack/rn-troubleshooting.md` | **fanbird/close 고유 트러블슈팅 스트립**, 제네릭 RN/iOS/Android만 |
| `_templates/{test-report, rn-exception-test-checklist}-template.md` | `templates/` | 제네릭화(이미 대부분 범용) |
| `agents/{coder, reviewer, tester}.md` | `bots/` | **역할부 제거(뼈대로)**, RN/풀스택 튜닝분만 오버레이로 |
| `agents/{planner, writer}.md` | 판단 필요 | 대체로 역할=뼈대. 직군색 옅으면 통째 뼈대로 이동 검토 |
| `.agents/skills/visual-validator` | `skills/` | UI 검증=프론트 전용 |
| `pack.yaml` | 신규 작성 | 위 provides 목록으로 |

### → ③ 사용자 데이터 / 배포 제외 (그대로 두거나 버림)
`daily/`, `projects/`, `docs/`, `keys/`, `specs/`, `memory/*.md`의 내용, `company/*.json` 런타임값, `tools/{agy-ask, append-gemttori-done, report-gemttori-quota, slack-post}`(=에이전트 런타임 설정 → `agents.config`로 추상화), `setup.sh`, 각종 `.png`.

---

## 3. 파생봇 역할/오버레이 분리 방법 (세부2 Q3 적용)

`coder.md`/`reviewer.md` 실물 확인 결과 경계가 뚜렷:

```
[역할 = 뼈대 skeleton/bots/<role>.md]        [직군 오버레이 = packs/fullstack-rn/bots/<role>.md]
─────────────────────────────────────       ────────────────────────────────────────────
coder:  지시로 모듈 구현·반환 / PLAN범위       coder:  React/RN Flexbox·리렌더 / Prisma N+1
        외 금지 / 사용자 직접대화 금지                Zod 검증
reviewer: 적대적 리뷰 / [위험도상중하]         reviewer: Hooks 종속성·cleanup / Podfile 충돌
          구조화 보고                                   SQL Injection·N+1 체크리스트
```
- **뼈대 봇** = 역할 정의 + **불변 협업규칙**("작성/리뷰 분신 분리" 등) → 부패 불가.
- **팩 봇** = 직군 체크리스트/전문화만. init 시 `뼈대 역할 + 팩 오버레이` 합성해 최종 페르소나 생성.

---

## 4. 추출 절차 (실행 순서)

```
1. 스냅샷: 현재 biz-ttori를 건드리지 않는다(실운영 유지) — 복사본에서 작업.
2. skeleton 조립: CLAUDE.md 슬롯 분해 → skeleton/rules/* + CLAUDE.template.md.
3. 고유물 스트립 패스: 전 파일에서 close/fanbird/FMS/PM/젬또리/biz-ttori 고유명 → 제네릭 치환·제거.
4. fullstack-rn 팩 채우기: §2 매니페스트대로 + pack.yaml 작성.
5. 봇 역할/오버레이 분리(§3).
6. 검증: 추출된 skeleton+팩으로 `btd init`을 빈 디렉토리에서 돌려 doctor 통과 확인.
```
> ⚠️ **스트립 패스(3)가 품질 관문.** 고유명이 새어나가면 "남의 회사 흔적 든 템플릿"이 되어 포폴·배포 다 망침. grep 체크리스트로 자동화(세부5 doctor에 "고유명 잔존 검사" 룰 추가 검토).

---

## 5. 새 열린 질문 (세부5=doctor 스펙으로)

- ❓ `gbrain-doctor.sh`가 현재 정확히 뭘 검사하는지 → TS 포팅 명세(세부5).
- ❓ "고유명 잔존 검사"를 doctor 룰로 넣을지(추출 품질 게이트).
- ❓ `planner`/`writer`가 뼈대인지 팩인지 최종 판정(직군색 실측 필요).
- ❓ 스트립 시 제네릭 치환 규칙표(close→"프로젝트A" 식 매핑) 필요 여부.

---

## 🔗 관련
- `[[BTD-세부1-팩규격]]` §2(3버킷 매핑 원본) · `[[BTD-세부2-모노레포]]` §5(포팅 매핑) · `[[BTD-세부3-셋업마법사]]` §3 Q3(팩 채우는 시점)
