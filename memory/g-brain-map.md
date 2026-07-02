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

## 🔗 연결 규약 (요약)

- **코드 ↔ 문서**: 모듈/기능 단위 `[[링크]]`만 (함수 단위 금지 — G1). 안정적 앵커에만.
- **FE ↔ BE**: 반드시 계약 문서 경유 (G3). 외부 프로젝트는 `projects/<name>/api-specs.md`(SSOT), 전역 [[api-specs]]는 인덱스+내부툴만. 직접 추측 금지.
- **Git ↔ 노트**: 커밋/브랜치에 `ref: <노트>#<앵커>` 기록 (G2).
- **외장 두뇌 모델(G5)**: 코드는 외부 폴더, 두뇌는 볼트. `claude`는 항상 biz-ttori에서 기동. **외부 코드는 백틱 절대경로**(`` `/Users/.../repo/...` ``), wikilink는 볼트 안에서만. 프로젝트 폴더 규약 → `projects/README.md`.
- **분할 축**: 프로젝트별(`projects/<name>/`) — 레이어(FE/BE/DB) 분할은 프로젝트 폴더 *안*에서만 (G5).

---

## 📂 프로젝트 노드 (실연동 시 추가)

> 실제 활성화된 외부 프로젝트 노드 자동 동기화 목록입니다.

| 프로젝트 | 폴더 | context | api-specs 범위 | 상태 |
|:---|:---|:---|:---|:---|
| [[FMS/FMS]] | `projects/FMS/` | `projects/FMS/context.md` | `projects/FMS/api-specs.md` | 🟢 활성 |
| [[close/close]] | `projects/close/` | `projects/close/context.md` | `projects/close/api-specs.md` | 🟢 활성 |

### 내부 툴(biz-ttori 자체 개발)

| 툴 | 사양서 | 상태 |
|:---|:---|:---|
| Slack 연동 | [[slack-integration-spec]] (`specs/slack-integration-spec.md`) | 🟢 Phase1 구현(`tools/slack-post.sh`) |
| OpenClaw 연동 | [[openclaw-integration-guide]] (`specs/openclaw-integration-guide.md`) | 🟡 Phase2 설계(leash 모델로 교정) |

---

## 🩺 무결성 점검

```bash
tools/gbrain-doctor.sh   # 깨진 [[링크]] 탐지 → 환각 소스 차단
```
- 세션 시작 또는 코드/문서 대량 변경 후 실행 권장.
- 깨진 링크 = 부패한 지식. 발견 즉시 수정하거나 링크 제거.
