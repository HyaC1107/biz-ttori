# api-specs.md — 전역 API 인덱스 + biz-ttori 내부툴 계약

> **지브레인 G3.** ⚠️ **외부 프로젝트의 계약 SSOT가 아니다.** 각 외부 프로젝트의 FE↔BE 계약은 **그 프로젝트 폴더** `projects/<name>/api-specs.md`가 단일 진실원(SSOT)이다.
> 이 전역 파일의 역할은 둘뿐: ① 각 프로젝트 계약으로의 **인덱스**, ② biz-ttori **자체 내부 툴**(Slack 연동 등)의 계약.
> 상세 양식은 [`_templates/api-spec-template.md`](../_templates/api-spec-template.md). 관계 인덱스는 [`g-brain-map.md`](g-brain-map.md).

---

## 🧭 ① 프로젝트 계약 인덱스

> 외부 프로젝트가 붙으면 한 행 추가. 실제 계약은 각 프로젝트의 `api-specs.md`에 있다(여기엔 위치만).
> 2026-07-27: 환경 초기화로 `projects/` 폴더가 비워지며 옛 close 항목(드리프트)을 제거했다.

| 프로젝트 | 계약 SSOT 위치 | 비고 |
|:---|:---|:---|
| _(없음)_ | | |

---

## 🛠️ ② biz-ttori 내부 툴 계약

> 비즈또리 자체 기능(Slack 연동 등)의 API/인터페이스만 여기 직접 기재한다.

| ID (앵커) | Method · Path / 인터페이스 | 설명 | 구현부 | 상태 |
|:---|:---|:---|:---|:---|
| `slack-report` | `POST $SLACK_WEBHOOK_URL` (`{text}`) | Step7 보고 단방향 전송 | `tools/slack-post.sh` | ✅ 구현(웹훅URL 입력 시 가동) |

> 상세는 [`specs/slack-integration-spec.md`](../specs/slack-integration-spec.md) 참조.

---

## 사용 규칙

1. **외부 프로젝트 엔드포인트**: `projects/<name>/api-specs.md`에 등록(이 파일 아님). 여기엔 인덱스 한 행만.
2. **내부 툴 엔드포인트**: ② 표에 등록 + 앵커(`#id`) 부여.
3. 커밋·브랜치에 앵커를 `ref`로 기록 (G2). 예: `(ref: projects/<name>/api-specs.md#auth-login)`.
4. 계약이 바뀌면 **코드보다 계약 문서를 먼저** 고친다.
