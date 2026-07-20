---
type: spec
status: 초안
project: "BTD (biz-ttori for Developer)"
created: "2026-07-20"
updated: "2026-07-20"
author: "PM & 클또리"
is_public: false
confidential: true   # 깃 원격 푸시 스킵
tags: [type/spec, status/초안, project/BTD, layer/pack-spec]
related: ["[[BTD-비전]]"]
---

# 📦 BTD 세부기획 1 — ①/② 경계 + 직군 팩 규격(Pack Spec)

> **목표**: "직군 팩이 *구체적으로* 뭐냐"를 데이터 구조로 정의한다. 이게 정해지면 모노레포 구조(세부2)·셋업 마법사(세부3)가 파생된다.
> **동시 해결**: §5-1 자가 부패 방지 = 이 문서의 "불변/가변 split"이 곧 방어선이다.

---

## 1. 핵심 발견 — 2버킷이 아니라 **3버킷**

현재 biz-ttori 파일을 갈라보니 "뼈대 vs 팩"만으론 안 나뉘고, **"사용자가 만든 콘텐츠"**라는 세 번째 축이 필요하다.

| 버킷 | 정의 | 자가수정 권한 | 배포 시 |
|:---|:---|:---:|:---|
| **① 뼈대 (Skeleton)** | 직군 무관 불변 가드레일·인프라 | 🔒 **불변** (툴이 못 고침) | BTD가 소유·버전관리 |
| **② 직군 팩 (Pack)** | 직군별 규칙·봇·템플릿·스택 | ✏️ **가변** (선언된 범위 내 자가발전) | 규격+레퍼런스 1개만 소유, 나머지 커뮤니티 |
| **③ 사용자 데이터 (Workspace)** | 실제 업무 산출물·프로젝트 | 📝 자유 write (=실작업) | 사용자 것, 배포 대상 아님 |

---

## 2. 현재 biz-ttori 파일 → 3버킷 매핑

> 이 매핑이 곧 "무엇을 BTD 코어로 추출하고, 무엇을 팩으로 떼고, 무엇을 사용자 볼트로 남길지"의 실측 근거다.

### ① 뼈대 (🔒 불변 코어)
- **지식그래프 인프라**: G-Brain 규칙(CLAUDE.md의 🧠섹션), `tools/gbrain-doctor.sh`, `.agents/skills/{gbrain-healer, gbrain-map-sync}`
- **메모리 스키마(빈 스캐폴드)**: `memory/{context, g-brain-map, api-specs, inbox, outbox}.md`의 *구조*(내용 아님)
- **협업 프로토콜**: `.agents/AGENTS.md`, 우체통(inbox/outbox) 컨벤션, `.agents/skills/inbox-cleaner`
- **정책**: AI 호출 3단계(T1/T2/T3), 문서 인덱스 규약, `memory/team-rules.md` 구조
- **인프라**: `dashboard/`(BTD 제품 본체), `.agents/hooks.json`, `.agents/scripts/auto-logger.js`, `company/*.json` **스키마**
- **범용 템플릿**: `_templates/{daily, spec, meeting-minutes, handover, troubleshooting, project-context, api-spec}-template.md`

### ② 직군 팩 (✏️ 가변, 교체 가능) — 현재=풀스택 팩(레퍼런스)
- **직군 개발 규칙**: CLAUDE.md §1(React/RN)·§2(Fullstack) — 팩으로 분리
- **기술 스택 지식**: `memory/stack.md`(RN/iOS/Android 트러블슈팅)
- **직군 템플릿**: `_templates/{test-report, rn-exception-test-checklist}-template.md`
- **파생봇 페르소나**: `.claude/agents/{coder, reviewer, tester, planner, writer}.md`의 *직군 튜닝분*(React/RN 포커스)
- **직군 스킬**: `.agents/skills/visual-validator`(UI 검증 — 프론트 전용)

### ③ 사용자 데이터 (📝 볼트, 배포 안 함)
- `daily/`, `projects/`, `docs/`, `keys/`, `specs/`
- `memory/` 파일들의 *내용*, `company/` 런타임 상태(events.jsonl 등)
- **에이전트 런타임 설정**: `tools/{agy-ask, append-gemttori-done, report-gemttori-quota, slack-post}` = "내가 어떤 봇(젬또리·슬랙)을 쓰는가" → 사용자별 설정

> ⚠️ **CLAUDE.md는 통짜가 아니라 조립물이다.** 현재 한 파일에 ①(G-Brain·정책)+②(직군규칙)+③(팀 명단)이 섞여 있다. BTD에선 **뼈대 규칙(불변) + 팩 규칙(가변) + 사용자 팀설정**을 각각 조각으로 두고 **init 시 합성**해서 최종 CLAUDE.md를 생성한다.

---

## 3. 팩 규격 (Pack Manifest) — 초안

직군 팩 = **매니페스트 1개 + 자산 폴더**. 매니페스트가 "이 팩이 뼈대 위에 무엇을 얹는가"를 선언한다.

```yaml
# pack.yaml
id: fullstack-rn            # 팩 고유 id
name: "풀스택 / React Native"
version: 1.0.0
targetSkeleton: "^1.0"      # 호환되는 뼈대 버전 (버전 헬 방지 — 젬또리 리스크 #2)
description: "React/RN 프론트 + Node 백엔드 풀스택 개발자용"

# 뼈대 위에 얹는 것들 (add/override만, 뼈대 자체는 못 건드림)
provides:
  rules:                    # 최종 CLAUDE.md에 합성될 직군 규칙 조각
    - rules/react-native.md
    - rules/fullstack.md
  templates:                # _templates/에 추가될 직군 템플릿
    - templates/test-report.md
    - templates/rn-exception-test-checklist.md
  bots:                     # 파생봇 페르소나 (뼈대 봇 역할을 직군 튜닝)
    - bots/coder.md
    - bots/reviewer.md
    - bots/tester.md
  skills:
    - skills/visual-validator/
  stack:                    # 기술스택 지식(stack.md에 해당)
    - stack/rn-troubleshooting.md

# ⏸️ evolution 블록 = v1 제외(2026-07-20 결정, future). v1 팩은 정적.
#    자가발전을 빼서 자가부패 리스크 자체를 제거(클또리+젬또리 교차검토 수렴).
#    아래 locked/evolvable 설계는 future 자가발전 도입 시 재사용할 의도로 남겨둠.
evolution:   # (v1 미사용)
  locked:                   # 툴이 절대 못 고치는 것 (뼈대 참조 + 팩의 핵심 계약)
    - "targetSkeleton"      # 뼈대 버전 호환성 못 낮춤
    - "provides.rules[*].guardrail_section"   # 규칙 중 가드레일 표시된 문단
  evolvable:                # 툴이 선언 범위 내에서 자가발전 허용
    - "templates/*"         # 새 템플릿 추가·개선 OK
    - "stack/*"             # 트러블슈팅 지식 축적 OK
    - "provides.bots[*].examples"  # 봇 예시 보강 OK
  policy:
    requireHumanReview: true        # evolvable 변경도 커밋 전 사람 검토 (지시·검토 원칙)
    doctorMustPass: true            # 변경 후 gbrain-doctor 통과 필수
    maxAutoChangesPerRun: 5         # 한 번에 폭주 방지
```

---

## 4. init(셋업)이 이걸로 하는 일

```
1. 사용자가 웹 셋업 마법사에서 직군 선택 → 해당 pack.yaml 로드
2. targetSkeleton 버전 호환 체크 (안 맞으면 중단 — 버전 헬 차단)
3. 뼈대(불변) 복사 + 팩의 provides.* 를 뼈대 위에 합성
   - rules 조각들 + 사용자 팀설정 → 최종 CLAUDE.md 생성
   - templates/bots/skills/stack → 각 위치에 배치
4. 빈 사용자 볼트(memory 스키마·company 스키마) 스캐폴딩
5. gbrain-doctor 1회 실행 → 무결성 확인 후 완료
```

---

## 5. §5-1 자가 부패 방지 — v1은 "안 함"으로 원천 제거

> **결정(2026-07-20)**: v1은 **자가발전을 하지 않는다**(정적 팩). 따라서 "툴이 스스로 규칙 고치다 가드레일 약화"라는 자가부패 리스크 자체가 v1엔 존재하지 않는다. 대신 `npx btd pack add <name>`로 **사람이** 팩을 추가/편집한다. 근거: 클또리 자체검토 + 젬또리 교차검토(AutoGPT 자가진화 실패·자가 규칙 완화 편향) 수렴.
>
> 아래는 **future(자가발전 도입 시)** 를 위한 방어 설계로 보존한다. Letta 등 실제 프레임워크도 자가편집엔 read-only 잠금을 두는 게 확인됨 — 아래 locked/evolvable split이 그와 동형.

(future 설계) 자가발전을 켜게 되면 다음 3중 방어로 막는다:

1. **뼈대(①)는 물리적으로 팩 밖**이라, 팩을 자가발전시켜도 뼈대 가드레일(G-Brain·doctor·티어정책)엔 손이 닿지 않는다.
2. 팩 내부도 `evolution.locked`로 **핵심 계약(가드레일 문단·버전 호환성)은 잠금**, `evolvable`로 **부수 자산(템플릿·스택지식)만 자가발전** 허용.
3. 모든 자가발전은 `requireHumanReview + doctorMustPass + maxAutoChangesPerRun`으로 **사람 검토 + 결정론적 검사 + 폭주 상한**을 통과해야 커밋. (CLAUDE.md의 "지시·검토 위주" 원칙과 일치)

---

## 6. 열린 질문 (세부2로 넘김)

- ❓ `rules` 조각 합성 방식: 단순 concat vs 섹션 머지(중복 헤더 처리)?
- ❓ 팩 버전업 시 이미 자가발전된 사용자 팩과의 머지 전략(3-way merge?).
- ❓ 파생봇을 "뼈대 봇(역할) + 팩 오버레이(직군 튜닝)"로 나눌지, 팩이 봇 통째로 제공할지.
- ❓ 사용자 팀설정(누가 어떤 에이전트 쓰나)을 별도 `agents.config` 로 뺄지.

---

## 🔗 관련
- `[[BTD-비전]]` — 상위 비전
- 매핑 근거 원본: `CLAUDE.md`, `_templates/`, `.agents/`, `.claude/agents/`, `memory/`, `tools/`
