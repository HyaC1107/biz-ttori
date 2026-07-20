---
type: spec
status: 초안
project: "BTD (biz-ttori for Developer)"
created: "2026-07-20"
updated: "2026-07-20"
author: "PM & 클또리"
is_public: false
confidential: true   # 깃 원격 푸시 스킵
tags: [type/spec, status/초안, project/BTD, layer/doctor]
related: ["[[BTD-세부4-뼈대추출]]", "[[BTD-세부2-모노레포]]"]
---

# 🩺 BTD 세부기획 5 — doctor 스펙 (bash→TS 포팅)

> **목적**: 현행 `tools/gbrain-doctor.sh`가 *정확히 뭘 하는지* 명세로 고정하고, `@btd/core`의 TS 무결성 엔진으로 포팅한다. + 세부4의 "고유명 잔존 검사"를 어디에 둘지 확정.

---

## 1. 현행 doctor가 하는 일 (포팅 SSOT)

**한 줄**: 볼트의 모든 `[[wikilink]]`가 실재 노트를 가리키는지 검사(Obsidian 규칙 = basename 해석). 깨진 링크 = 환각 소스.

**동작 순서**:
1. 대상 `.md` 수집 — 제외: `node_modules/`, `.git/`, `_templates/`, `.obsidian/`.
2. 볼트 전체 노트의 **basename 목록** 작성(링크 해석 기준).
3. 각 노트에서 **코드 영역 제거** 후 링크만 추출:
   - ① ```` ``` ```` 펜스 블록 통째 제거, ② 인라인 `` `code` `` 스팬 제거 (문서 예시 링크 오탐 방지).
4. `[[...]]` 추출 후 **정규화**: `[[ ]]` 벗김 → 별칭 `|` 제거 → 헤딩 `#` 제거 → 트림.
5. **스킵 규칙**: 순수 헤딩 링크 `[[#sec]]`, 템플릿 자리표시자 `{..}` 포함, 이미지/미디어(`.png/.jpg/.jpeg/.gif/.pdf`).
6. 링크 대상 `basename(+.md)`가 볼트 basename 목록에 없으면 **깨진 링크**로 리포트.
7. **종료코드**: `0`=정상, `1`=깨진 링크 있음, `2`=사용 오류(대상 없음).

**알려진 한계(그대로 포팅, 개선은 future)**:
- basename 전역 해석 → **동일 basename 중복 시 아무거나 매칭되면 통과**(경로 구분 안 함).
- 존재만 검사, "링크가 의미상 맞는지"는 검사 안 함.

---

## 2. TS 포팅 명세 (`@btd/core`)

**룰 엔진 구조**(팩/future가 룰 추가 가능하게):
```ts
// @btd/shared
type DoctorFinding = { rule: string; file: string; message: string; severity: 'error'|'warn' };
type DoctorResult = { checkedLinks: number; findings: DoctorFinding[]; ok: boolean };

// @btd/core
interface DoctorRule { id: string; run(vault: VaultFiles): DoctorFinding[]; }
function runDoctor(vault, rules: DoctorRule[]): DoctorResult;
```

**v1 룰 = R1(wikilink) 하나만.** §1의 파싱/정규화/스킵 규칙을 **그대로** TS로 옮긴다(오탐 방지 로직이 핵심 자산이라 임의 변경 금지).

**종료코드 매핑**(CLI `btd doctor`): findings에 error 있으면 exit 1, 대상 없음 exit 2, 아니면 0. (기존과 동일)

**호출 지점**:
- 셋업 마법사 스텝6(세부3) — `runDoctor` 결과를 SSE로 스트림, 통과율 표시.
- `btd doctor` CLI.
- pre-commit 훅(선택) — 커밋 전 깨진 링크 차단(CLAUDE.md G1 "커밋 전 무결성" 계승).

---

## 3. "고유명 잔존 검사" — doctor 룰이 아니라 **빌드타임 추출 린트** (세부4 반영)

> ⚠️ **중요 구분**: 사용자 볼트엔 그 사람 프로젝트명이 **당연히 있어야** 한다 → 사용자-런타임 doctor가 고유명을 잡으면 안 된다. 이건 **배포물(skeleton/packs)을 만들 때만** 도는 별도 린트다.

- **위치**: `@btd/pack-sdk`(또는 core)의 **build-time 린트**(`btd build:check` 류), 사용자 `btd doctor`와 분리.
- **대상**: `core/assets/skeleton/**`, `packs/**` (배포 자산만).
- **검사**: 금지 고유명 사전(`close|fanbird|FMS|biz-ttori|젬또리|linkcampus|…`) grep → 잔존 시 **빌드 실패**.
- **근거**: 세부4 §4 "스트립 패스가 품질 관문". 배포물에 남의 회사 흔적 유출 = 포폴·배포 치명.
- 룰 엔진 재사용은 하되 **ruleset/대상이 다르다**(사용자 볼트 대상 아님).

---

## 4. Future 룰 (v1 제외, 확장 지점만)

> **R1(wikilink)의 다음 단계 = "링크가 존재하냐" → "링크가 타입상 맞냐"(온톨로지 R2).** 팔란티어식 온톨로지가 관계에 타입(Objects/Links/Actions/Rules)을 매기듯, doctor도 노트 종류별 필수 관계를 스키마로 검증할 수 있다(2026-07-20 리서치, `[[project-btd-landscape-orca-ontology]]`). 예: `project-context` 노트는 반드시 `api-specs`를 링크해야 함 / `daily` 로그는 반드시 프로젝트를 링크해야 함.

- **온톨로지 R2 — 계약 참조 무결성**: `api-specs`가 실재 엔드포인트를 가리키는지 + 위 타입별 필수관계 스키마 검증.
- 죽은 절대경로 코드 참조 검사(외부 레포 파일 이동 감지).
- 중복 basename 경고(현행 한계 개선).
- 팩이 제공하는 커스텀 doctor 룰(직군별 검사).

---

## 5. 세부기획 마무리

세부5까지로 **BTD 세부기획(설계) 라운드 종료.** 남은 열린 질문들은 전부 "구현 중 결정" 또는 "future"로 분류됨:
- 관제 대시보드 화면 구성(기존 board/dashboard3d 계승 범위) → 구현 중.
- planner/writer 뼈대냐 팩이냐 최종판정 → 추출 실행 중.
- 스트립 제네릭 치환 규칙표 → 추출 실행 중.

→ **다음 단계 = v1 MVP 슬라이스 정의** 후 첫 구현 착수.

---

## 🔗 관련
- 포팅 원본: `tools/gbrain-doctor.sh` · `[[BTD-세부4-뼈대추출]]`(고유명 스트립) · `[[BTD-세부2-모노레포]]`(패키지)
