---
type: spec
status: 초안
project: "BTD (biz-ttori for Developer)"
created: "2026-07-20"
updated: "2026-07-20"
author: "PM & 클또리"
is_public: false
confidential: true   # 깃 원격 푸시 스킵
tags: [type/spec, status/초안, project/BTD, layer/monorepo]
related: ["[[BTD-비전]]", "[[BTD-세부1-팩규격]]"]
---

# 🏗️ BTD 세부기획 2 — 모노레포 뼈대

> **전제**: 스택 = Node/TS 백엔드 + React 프론트, **단일 TS 모노레포(타입 공유)**, 진입점 `npx btd` (`[[BTD-비전]]` §2).
> **파생**: 패키지 분할은 `[[BTD-세부1-팩규격]]`의 3버킷 + 컴포넌트에서 그대로 떨어진다.

---

## 1. 패키지 그래프

```
btd/                          (모노레포 루트, pnpm workspaces + turborepo)
├── packages/
│   ├── shared/     @btd/shared    ★타입 SSOT — 프론트·백 공유
│   │                 PackManifest, ConfigSchema, EventSchema,
│   │                 company/*.json 스키마, DoctorResult 타입
│   ├── core/       @btd/core      ①뼈대 로직 + 불변 자산(원판)
│   │                 지식그래프·doctor·합성엔진·우체통·메모리/company 스키마
│   │                 └ assets/skeleton/  (범용 템플릿·메모리 빈스캐폴드·AGENTS.md·뼈대 rules 조각)
│   ├── pack-sdk/   @btd/pack-sdk  팩 규격 로더·검증·evolution 가드
│   │                 pack.yaml 파싱/검증, locked/evolvable 강제, 3-way 오버레이
│   ├── server/     @btd/server    로컬 웹 백엔드(Node/TS)
│   │                 파일워처(chokidar)·쓰기API·프로세스관리·셋업실행·ws 실시간
│   ├── web/        @btd/web       React 프론트 (Vite build → static)
│   │                 셋업 마법사 + 관제 대시보드. server가 정적 서빙
│   └── cli/        @btd/cli       `npx btd` — init / doctor / (server 기동)
├── packs/
│   └── fullstack-rn/              레퍼런스 팩 1개 (pack.yaml + assets)
│                     rules/ templates/ bots/ skills/ stack/
└── (turbo.json, pnpm-workspace.yaml, tsconfig.base.json …)
```

**의존 방향** (단방향, 순환 금지):
```
shared ← core ← pack-sdk ← server ← cli
shared ← web  ────────────↗ (web은 server가 서빙, 런타임 통신은 HTTP/ws)
```
- `shared`가 최하단 = **모두가 같은 타입을 봄**(Node 백엔드 채택의 핵심 근거 실현).
- `web`은 코드 의존은 `shared`만, 런타임엔 `server` API를 HTTP/ws로 호출.

---

## 2. skeleton 자산 vs packs 자산 (물리 배치)

| | 위치 | 성격 | 소유 |
|:---|:---|:---|:---|
| **뼈대 자산(원판)** | `packages/core/assets/skeleton/` | 불변. init이 사용자 볼트로 **복사**할 원본 | BTD 코어 |
| **직군 팩** | `packs/<id>/` | pack.yaml + 자산. 뼈대 위에 얹힘 | 규격+레퍼런스1개만 |
| **사용자 볼트(③)** | init 실행한 cwd (레포 밖) | 생성물. 실작업 산출 | 사용자 |

> 팩은 "코드"가 아니라 **매니페스트+자산 번들** → `packs/`는 별도 npm 패키지가 아니라 pack-sdk가 검증하는 폴더. (레퍼런스 팩은 배포 시 cli에 번들)

---

## 3. 세부1에서 넘긴 열린 질문 4개 — 결정

### Q1. rules 조각 합성 방식 → **슬롯 기반 템플릿 조립** (concat도 3-way머지도 아님)
- 뼈대가 **마스터 CLAUDE.md 템플릿(명명된 슬롯 보유)** 을 제공: `{{SKELETON_RULES}}`(고정) · `{{PACK_RULES}}`(직군) · `{{TEAM_CONFIG}}`(사용자).
- 팩 rules 조각은 `{{PACK_RULES}}` 슬롯에 **순서 태그대로** 채워짐. 사용자 팀설정은 `{{TEAM_CONFIG}}`.
- 이유: blind concat은 헤더 중복·순서 혼란, 풀 시맨틱 머지는 과함. 슬롯 조립이 예측가능+가드레일(뼈대 슬롯) 보존.

### Q2. 팩 버전업 머지 → ⏸️ **v1에선 불필요(2026-07-20 갱신)**
- v1은 **정적 팩 + 자가발전 없음**으로 결정됨(세부1 §5) → 사용자가 팩을 자가발전시키지 않으므로 **overlay/3-way 머지 자체가 v1엔 없다.** `@btd/pack-sdk`에서 이 복잡성 제거 → v1 코어 완성도에 집중.
- 팩 편집은 **사람이** `npx btd pack add <name>`(스캐폴더)로 새 팩을 뜨거나 기존 팩 파일을 직접 고침. 정적이라 버전헬 표면도 작음.
- *(future)* 자가발전 도입 시에만 pristine base + evolution overlay + 3-way를 부활(세부1의 보존된 설계).

### Q3. 파생봇 → **역할은 뼈대, 직군 튜닝은 팩 오버레이**
- 뼈대: 봇 **역할(role)** 정의 = coder/reviewer/tester/planner/writer + **불변 협업 규칙**("리뷰 분신은 작성 분신과 분리" 등).
- 팩: 역할별 **오버레이**(React/RN 포커스, 스택 예시). → 협업 불변식은 코어라 부패 불가, 전문화만 팩이 튜닝. locked/evolvable split과 일치.

### Q4. 사용자 팀설정 → **별도 `agents.config` 로 분리**(③)
- "내가 어떤 봇을 쓰나(젬또리·슬랙·…)"는 팩(②)도 뼈대(①)도 아닌 **사용자 런타임 설정**.
- 사용자 볼트 루트에 `agents.config.yaml`. (옛 문서의 `agent-postbox.config.json` 계승) init 마법사가 생성.

---

## 4. dev-time vs installed-time (`npx btd`)

- **개발(모노레포)**: `packs/`·skeleton 자산 인레포. `pnpm dev`로 server+web 동시 기동.
- **설치(`npx btd`)**: 배포 npm 패키지가 core+cli+server+web(빌드된 static)+skeleton자산+레퍼런스팩 번들.
  - `npx btd init` → 현재 cwd에 **사용자 볼트(③)** 스캐폴딩(뼈대 복사 + 선택 팩 합성 + `agents.config` 생성 + doctor 1회).
  - `npx btd` → server 기동 → 브라우저로 셋업 마법사/관제 대시보드.
  - `npx btd pack add <name>` → **정적 팩 스캐폴더**(사람이 새 직군 팩을 규격대로 1초에 생성). v1 자가발전 대체재.

---

## 5. 기존 Python 엔진 → TS 패키지 매핑 (포팅 레퍼런스)

| 기존 `dashboard/engine/` | → BTD 패키지 | 비고 |
|:---|:---|:---|
| `serve.py`(정적서빙+쓰기API) | `@btd/server` | http.server → Node http/express류 |
| `procs.py`(프로세스 화이트리스트 kill) | `@btd/server` | ⚠️ 최고위험 — 나란히 검증 후 교체 |
| `spawn_queue.py`, `tasks.py` | `@btd/server` | |
| `events.py`, `health.py`, `audit.py` | 스키마→`@btd/shared`, 로직→`@btd/server` | |
| `company/*.json` 스키마 | `@btd/shared` | |
| `web/*.html`(board, dashboard3d) | `@btd/web`(React 재작성) | 3D 오피스 뷰 계승 |
| `tools/gbrain-doctor.sh` | `@btd/core` | bash → TS 포팅 |

> 실운영 biz-ttori는 TS 패리티 도달 전까지 Python 엔진 그대로 가동(비전 §2 완화책).

---

## 6. 모노레포 툴링

- **pnpm workspaces**(엄격한 의존·디스크 효율) + **turborepo**(빌드 캐시·태스크 파이프라인).
- `tsconfig.base.json` 공유, 각 패키지 project references.
- `web`=Vite, `server/cli/core/shared/pack-sdk`=tsup(또는 tsc) 번들.
- 포폴 관점: pnpm+turbo+project references는 "제대로 된 모던 모노레포"로 읽힘.

---

## 7. 새 열린 질문 (세부3=셋업 마법사로 넘김)

- ❓ 셋업 마법사 단계 플로우(직군 선택→스택 확인→봇 선택→볼트 위치→doctor)의 화면 단위.
- ❓ `web`↔`server` 실시간 채널: ws vs SSE vs 폴링(기존 15초 폴링 계승?).
- ❓ 레퍼런스 팩(fullstack-rn)을 실제 자산으로 채우는 건 언제(뼈대 추출과 동시? 후?).
- ❓ init 멱등성(이미 볼트 있는 cwd에 재실행 시 동작).

---

## 🔗 관련
- `[[BTD-비전]]` · `[[BTD-세부1-팩규격]]`
- 포팅 레퍼런스: `dashboard/engine/`, `dashboard/web/`
