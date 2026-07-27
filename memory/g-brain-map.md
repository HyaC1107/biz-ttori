# g-brain-map.md — 지브레인 지식 관계 인덱스

> biz-ttori의 **지식 그래프 한눈에 보기**. 문서·코드·계약·Git이 어떻게 연결되는지의 지도.
> 규칙은 [`CLAUDE.md`](../CLAUDE.md)의 **🧠 지브레인(G-Brain)** 섹션(G1~G5). 링크 무결성은 `tools/gbrain-doctor.sh`로 점검.

---

## 🗺️ 핵심 노드 (허브 문서)

| 노드 | 역할 | 주요 연결 |
|:---|:---|:---|
| [[context]] (`memory/context.md`) | 지금 상태 스냅샷 (얇은 라우터) | → 활성 프로젝트, [[api-specs]] |
| [[api-specs]] (`memory/api-specs.md`) | **전역 인덱스 + 내부툴 계약** (외부 프로젝트 계약 SSOT는 `projects/<name>/api-specs.md`) | → 프로젝트 계약, 내부툴 |
| [[stack]] (`memory/stack.md`) | 기술 스택·트러블슈팅 | → 빌드/캐시 패턴 |
| [[team-rules]] (`memory/team-rules.md`) | 협업 규칙·누적 교훈 | → 커밋 컨벤션, 리뷰 게이트 |
| [[CHANGELOG]] (`CHANGELOG.md`) | 완료 이력 (append-only) | ← context 이력 이주 |

---

## 📑 문서 인덱스 (상태별 모아보기, 2026-07-15 신설)

> 문서 3개 이상 쌓인 폴더의 상태(진행중/초안/완료) 뷰. 파일은 안 옮기고 인덱스만 둔다 — CLAUDE.md §3 참고.

| 인덱스 | 대상 폴더 |
|:---|:---|
| [[specs/README]] | `specs/` (biz-ttori 자체 툴 스펙) |

---

## 🔗 연결 규약 (요약)

- **코드 ↔ 문서**: 모듈/기능 단위 `[[링크]]`만 (함수 단위 금지 — G1). 안정적 앵커에만.
- **FE ↔ BE**: 반드시 계약 문서 경유 (G3). 외부 프로젝트는 `projects/<name>/api-specs.md`(SSOT), 전역 [[api-specs]]는 인덱스+내부툴만. 직접 추측 금지.
- **Git ↔ 노트**: 커밋/브랜치에 `ref: <노트>#<앵커>` 기록 (G2).
- **외장 두뇌 모델(G5)**: 코드는 외부 폴더, 두뇌는 볼트. `claude`는 항상 biz-ttori에서 기동. **외부 코드는 백틱 절대경로**(`` `/Users/.../repo/...` ``), wikilink는 볼트 안에서만. 프로젝트 폴더 규약 → `projects/README.md`.
- **분할 축**: 프로젝트별(`projects/<name>/`) — 레이어(FE/BE/DB) 분할은 프로젝트 폴더 *안*에서만 (G5).

---

## 📂 프로젝트 노드 (실연동 시 추가)

> 실제 활성화된 외부 프로젝트 노드 자동 동기화 목록입니다.
> 2026-07-27: 환경 초기화로 `projects/` 폴더가 비워지면서 기존 FMS/close/fanbird-broadcast 노드는 제거했다(문서 드리프트 정리 — team-rules.md 교훈 #2). 새 프로젝트가 붙으면 아래에 추가한다.

| 프로젝트 | 폴더 | context | api-specs 범위 | 상태 |
|:---|:---|:---|:---|:---|
| _(없음)_ | | | | |

### 내부 툴(biz-ttori 자체 개발)

> 2026-07-27: `specs/`에 실제로 존재하지 않는 문서(slack-integration-spec, openclaw-integration-guide, ask-gemttori-dashboard-spec)를 가리키던 드리프트 항목을 제거했다. 새 내부 툴 사양이 생기면 여기 추가한다.

| 툴 | 사양서 | 상태 |
|:---|:---|:---|
| _(없음)_ | | |

---

## 🩺 무결성 점검

```bash
tools/gbrain-doctor.sh   # 깨진 [[링크]] 탐지 → 환각 소스 차단
```
- 세션 시작 또는 코드/문서 대량 변경 후 실행 권장.
- 깨진 링크 = 부패한 지식. 발견 즉시 수정하거나 링크 제거.
