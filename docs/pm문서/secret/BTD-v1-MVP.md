---
type: spec
status: 초안
project: "BTD (biz-ttori for Developer)"
created: "2026-07-20"
updated: "2026-07-20"
author: "PM & 클또리"
is_public: false
confidential: true   # 깃 원격 푸시 스킵
tags: [type/spec, status/초안, project/BTD, layer/mvp]
related: ["[[BTD-비전]]", "[[BTD-세부4-뼈대추출]]", "[[BTD-세부5-doctor스펙]]"]
---

# 🎯 BTD v1 MVP 슬라이스 — 워킹 스켈레톤 + 첫 구현

> 세부기획(비전~세부5) 완료 후, "딱 돌아가는 최소 범위 + 첫 구현 태스크"를 정의한다. 포폴 1순위 → **데모 가능한 워킹 스켈레톤**이 목표(완성도보다 end-to-end 관통).

---

## 0. 워크스페이스 결정 (2026-07-20 확정)

- **코드 = 별개 레포** `~/btd` (자체 git). biz-ttori 볼트 안에 넣지 않음(오염·회사레포 push 방지 + BTD 자신의 G5 철학 "코드는 밖"). 
- **브레인(기획문서) = biz-ttori `docs/pm문서/secret/` 유지** (push-skip 규약). 궤도 오르면 개인 볼트로 독립 검토.
- **연결**: biz-ttori는 `~/btd`를 **절대경로 포인터**로 참조(G5, wikilink 아님). 예: `` `/Users/linkcampus02/btd/packages/core` ``.

---

## 1. MVP 목표 = 워킹 스켈레톤 (한 문장)

> `npx btd` → 로컬 웹 셋업 마법사 → 직군(fullstack-rn) 선택 → **cwd에 유효한 볼트 생성**(뼈대+팩 슬롯 조립) → **doctor 통과** → 완료 화면.

모든 층을 **얇게 한 번씩** 관통: cli → server → **web(셋업 마법사 = IN)** → core(합성+doctor) → pack-sdk(팩 로드).

> ⚠️ **웹 대시보드 전체가 out이 아님.** 웹 대시보드의 2역할(세부3) 중 **①셋업 마법사 = IN**, **②관제/모니터링(이벤트·헬스·3D오피스) = v1.1로 뒤로**. 진입점=로컬 웹은 그대로 유지. out된 "기능"은 자가발전뿐.

---

## 2. In scope / Out of scope

### ✅ In (MVP)
- `npx btd` = server 기동 + 브라우저 오픈, 볼트 감지 분기(세부3 §1).
- **최소 마법사**: 스텝 2(직군 선택) → 3(구성 확인) → 5(실행) → 6(doctor) → 7(완료). *(스텝0 감지·1 볼트위치·4 에이전트설정은 기본값으로 축약)*
- **core 합성 엔진**: 슬롯 조립(`{{SKELETON_RULES}}`+`{{PACK_RULES}}`+`{{TEAM_CONFIG}}`) → CLAUDE.md 생성 + 뼈대/팩 자산 배치.
- **pack-sdk**: `pack.yaml` 로드·검증·targetSkeleton 호환 체크.
- **doctor**: wikilink 무결성(세부5 R1) TS 포팅, 결과 화면 표시.
- **추출 자산**: `core/assets/skeleton` + `packs/fullstack-rn` (세부4 매니페스트대로, 고유명 스트립).
- init **멱등성**(기본 비파괴).

### ❌ Out (v1 이후/future)
- 웹 대시보드의 **②관제/모니터링 역할만** → v1.1. *(①셋업 마법사는 IN — 위 참조)*
  - ⚠️ **3D 오피스 뷰(dashboard3d.html)는 계승 대상에서 제외(2026-07-20 PM 결정).** 봇 유휴 시 "누워/앉아 있는" 은유가 "일 안 한다"는 역효과 + 포폴상 gimmick으로 읽혀 실질 강점(doctor·우체통·가드레일)을 가림. v1.1 관제는 **실용 뷰(이벤트 피드 + 태스크보드 + 헬스, 정보밀도 우선)**로 가고, 원형은 `dashboard/web/board.html`(2D 현황판).
- SSE 실시간(MVP는 요청-응답/간단 폴링으로 충분).
- 에이전트설정 마법사 스텝(agents.config 기본값 생성만).
- `pack add` 스캐폴더, 다중 팩, 팀 모드.
- 자가발전(이미 컷), overlay 머지.

---

## 3. 두 갈래 작업(맞물림)

MVP는 **코드**와 **자산 추출**이 서로를 필요로 함 → 병행:
- **Stream A(추출, 세부4)**: `~/btd`에 `core/assets/skeleton` + `packs/fullstack-rn` 채우기. 대부분 biz-ttori 파일 복사 + **고유명 스트립**. (데이터 작업)
- **Stream B(코드)**: shared 타입 → core(합성+doctor) → pack-sdk → server(init 파이프라인+정적 서빙) → cli(`npx btd`) → web(최소 마법사).
- 맞물림: init 데모하려면 A 필요, A 검증하려면 B의 init+doctor 필요.

---

## 4. 첫 구현 태스크 (순서)

```
T1. ✅ ~/btd 레포 부트스트랩 (pnpm9+turbo2+tsconfig.base, 6패키지 스캐폴드, git init 로컬). 검증: pnpm install+build 6/6 통과, cli 진입점 작동. (원격 push는 미실행)
T2. ✅ @btd/shared: pack/doctor/config/init 타입(PackManifest·DoctorResult·AgentsConfig·ComposeInput·VaultMarker). 검증 build 6/6. (로컬커밋 0a2b73b)
T3. ✅ @btd/core: doctor(wikilink R1 TS 포팅, DoctorRule 엔진) + 슬롯 합성 엔진. 검증: 픽스처 스모크 통과(checkedLinks=4·깨진링크 1건·오탐 없음). (로컬커밋 2d1eb1b)  [세부5]
T4. ✅ @btd/pack-sdk: loadPack + validatePackManifest + isSkeletonCompatible(semver). deps=yaml/semver. 검증: 스모크(로드·range판정·검증실패 3케이스). (로컬커밋 7e7d92a)
T5. ✅ [Stream A] skeleton 자산 추출 + fullstack-rn 팩 채우기 + 고유명 스트립  [세부4] (로컬커밋 98ff8fc, 52파일)
    - T5-1 ✅ skeleton/rules 7개 + order.json + CLAUDE.template.md
    - T5-2 ✅ skeleton/{skills 3개, AGENTS.md, hooks, memory 빈스캐폴드 6개, company 스키마 5개, templates 7개}
    - T5-3 ✅ packs/fullstack-rn: rules(RN+CSS/fullstack) + stack(트러블슈팅, 기술지식 유지·태그만 스트립) + templates 2개 + visual-validator + pack.yaml. pack-sdk로 실로드·호환체크 검증.
    - T5-4 ✅ 파생봇 역할/오버레이 분리 — coder·reviewer·tester는 뼈대(역할)+팩(직군튜닝) 분리, planner·writer는 직군색 옅어 통째 뼈대行
    - T5-5 ✅ 전체 grep 스트립 검증 클린 + doctor 실전 구동(버그 2건 발견·수정: rules조각 wikilink→일반텍스트, templates는 `_templates/`명명이어야 doctor제외 확인) + build 6/6 + 커밋
    - 실결함 발견·수정 상세는 커밋 98ff8fc 메시지 참조.
    - biz-ttori TaskList(#1~#5)에도 동일 진행상황 추적 중.
T6. ✅ @btd/server: init 파이프라인(runInit/detectVault/listPacks) + 로컬 HTTP API(status/packs/init, node:http 순수). 정적서빙은 T8 TODO. (로컬커밋 6ef306b)
    - 부수 수정: core의 CLAUDE.template.md 미해결 슬롯 버그 발견·수정, hooks.json 치환 코멘트 정리.
    - 검증: 빈 디렉토리 e2e(35파일 생성·doctor ok:true·슬롯 완전해소·멱등성) + HTTP curl 전체 라우트 실측.
T7. ✅ @btd/cli: `btd`(server기동+볼트감지 안내) / `btd init`(헤드리스, --pack/--yes/--name) / `btd pack add`(미구현 안내) / `--help`. argv 직접파싱(외부 CLI프레임워크 無). (로컬커밋 878b9e6)
    - 검증: 실전 스모크 6개 시나리오 전부 통과(help·init헤드리스·재실행안내·멱등재실행·미지명령·pack add) + `btd` 무인자 실행을 볼트有/無 양쪽에서 curl 확인.
T8. ✅ @btd/web: Vite+React 셋업 마법사 5스텝(PackSelect/Review/Scaffold/Doctor/Done) + api클라이언트 + 라이트/다크 styles. server에 compatible필드·web/dist 정적서빙 연결, shared에 API계약 타입. 스텝3 Review=포폴 킬러화면(뼈대 vs 팩자산 카테고리 시각화). (로컬커밋 a4e3e9f)
    - 검증: pnpm build 6/6(vite포함) + Playwright 브라우저 e2e 전스텝 클릭통과(팩선택→구성확인→생성→doctor✅0건→완료35파일) + 디스크 볼트 실제생성·슬롯해소 확인 + 스크린샷.
T9. ✅ 통합 검증: shebang 실행권한으로 cli dist를 진짜 실행파일(`btd`, node 명시 없이)로 완전 새 빈 디렉토리에서 구동 → Playwright 브라우저로 5스텝 전체 관통(팩선택→구성확인→생성→doctor✅0/0→완료35파일) → 디스크 실제생성·슬롯해소 확인 → 서버 재기동 시 기존볼트 감지 분기(`/api/status`)까지 확인.
    - ⚠️ 발견: pnpm workspace에서 `@btd/cli`가 어디의 dependency도 아니라 `btd` bin이 자동 심볼릭링크 안 됨(`node_modules/.bin/btd` 없음, `pnpm exec` 불가). **실제 npm publish 전엔 알 수 없던 패키징 갭.** v1 MVP는 shebang 직접실행으로 우회 검증(기능적으로 동일 메커니즘). **실배포(npm publish 또는 `pnpm link --global`) 전 해결 필요 — future 작업으로 기록.**

🎉 **v1 MVP 워킹 스켈레톤 완성 (T1~T9 전부 완료, 2026-07-20).**
```

---

## 5. 성공 기준 (= 포폴 데모 스크립트)

1. 빈 폴더에서 `npx btd` 실행 → 브라우저에 셋업 마법사 뜸.
2. "풀스택/RN" 카드 선택 → 구성 미리보기(어떤 규칙·템플릿·봇이 깔리는지) 표시.
3. "생성" → 볼트 스캐폴딩 진행 → **CLAUDE.md가 슬롯 조립으로 생성됨**(뼈대+팩+팀).
4. doctor 자동 실행 → **✅ 링크 N/N 통과** 초록 표시.
5. 완료 → 생성된 볼트를 열어보면 정상 구조(memory 스키마·템플릿·팩 규칙 반영).

> 이 5단계가 GIF/영상 하나로 찍히면 **BTD 포폴의 코어 데모** 완성.

**✅ 2026-07-20 T9에서 5단계 전부 실증 완료**(Playwright 브라우저 e2e). 스크린샷/GIF 촬영은 보류(PM 요청) — 필요할 때 재개.

---

## 7. v1 이후 열린 항목 (future)

- ⚠️ **`btd` bin 패키징 갭**(T9 발견): pnpm workspace 안에서 `@btd/cli`가 아무 패키지의 dependency도 아니라 bin 심볼릭링크가 자동 생성 안 됨. 실제 `npx btd`(npm registry 배포) 또는 `pnpm link --global` 전에는 검증 불가한 부분 — v1은 shebang 직접실행으로 기능 동일성만 확인. **npm publish 준비 시 반드시 재검증.**
- ✅ **멀티 "메인 에이전트" 벤더중립 설계 — 검증 완료, 구현은 v2로 명시적 이연 (2026-07-20 결론)**:
  - 리서치 검증 결과(젬또리 4차 우편 + 클또리 WebFetch 원문대조): ① Claude Code `@파일` import **실재**(공식문서 `code.claude.com/docs/en/memory`, 재귀 최대 4단계) ② `AGENTS.md` **진짜 업계표준**(Linux Foundation, Codex/Cursor/Copilot/Windsurf 등 광범위 지원, agents.md 사이트 직접 확인) ③ **Anthropic 공식문서가 정확히 이 패턴을 권장**: `CLAUDE.md`에 `@AGENTS.md` 1줄 + 클로드 전용 추가사항. (④ Antigravity 네이티브 컨벤션은 젬또리가 출처 없이 답해 **미검증 폐기** — 필요시 PM이 직접 `agy` 빈폴더 실행해 확인.)
  - **PM 결정(2026-07-20)**: 지금 리팩터링하지 않고, **v1 스코프를 "BTD (Claude Code 에디션)"으로 명시**하는 쪽으로 정리(비전 §0.1 참조). 검증된 아키텍처는 그대로 두고 다음 버전에 구현.
  - 남는 별개 이슈: `hooks.json`(클로드 전용 lifecycle 훅)은 AGENTS.md 방식으로도 안 풀림.
- 온톨로지 R2(doctor 타입별 관계검증) — 세부5 §4.
- 관제/모니터링 웹(v1.1) — 세부3, board.html 계승, 3D뷰 제외.
- 포폴 패키징(스크린샷·GIF·케이스스터디 문서) — 보류.

---

## 6. 착수 전 확인 (2026-07-20 결정)
- ✅ `~/btd` 레포 = **개인 GitHub 계정, private**. (원격 생성은 PM이 원하는 개인계정으로 — 로컬 부트스트랩 후 `gh repo create`.)
- ✅ **버전 고정**(재현성=온보딩 마찰 최소화 핵심):
  - `.nvmrc` + `"engines".node` + `"packageManager": "pnpm@x.y.z"`(corepack) + `pnpm-lock.yaml` 커밋.
  - 후보: **Node 22 LTS**(또는 24 LTS), **pnpm 9.x**. ⚠️컷오프 2026-01 기준 → **레포 생성 시 Active LTS 재확인**.

---

## 🔗 관련
- `[[BTD-비전]]` · `[[BTD-세부4-뼈대추출]]`(Stream A) · `[[BTD-세부5-doctor스펙]]`(T3) · `[[BTD-세부1-팩규격]]`(T4)
