---
type: api
status: 초안          # 초안 → 진행중 → 완료 / 보류
project: "{프로젝트명}"
domain: "{domain}"
created: "{YYYY-MM-DD}"
updated: "{YYYY-MM-DD}"
is_public: false
tags: [type/api, status/초안]
related: ["[[api-specs]]"]   # 이 도메인은 memory/api-specs.md 레지스트리에 등록(G3)
---

# [API 명세서] {도메인/기능 이름}

> **상태**: 초안 · **기반 URL**: `/api/{domain}` · **작성일**: {YYYY-MM-DD}
> ⚠️ **G3 통로**: 이 도메인의 각 엔드포인트는 [[api-specs]]의 레지스트리 표에 **앵커(`#엔드포인트-id`)와 함께 먼저 등록**한다. FE/BE는 서로의 구현을 추측하지 않고 이 계약을 본다.

---

## 📑 엔드포인트 목록

| 메서드 | 경로 | 설명 | 인증 | 앵커(id) | FE 호출부 | BE 구현부 |
|:---|:---|:---|:---|:---|:---|:---|
| `GET` | `/list` | 리스트 조회 (필터/페이징) | Yes | `{domain}-list` | `{src/...}` | `{server/...}` |
| `POST` | `/create` | 신규 항목 생성 | Yes | `{domain}-create` | `{src/...}` | `{server/...}` |
| `PATCH` | `/update/:id` | 특정 항목 수정 | Yes | `{domain}-update` | `{src/...}` | `{server/...}` |
| `DELETE` | `/delete/:id` | 특정 항목 삭제 | Yes | `{domain}-delete` | `{src/...}` | `{server/...}` |

---

## 📡 상세 스펙

### 1. [POST] `/create` (항목 생성) — `#{domain}-create`

* **설명**: 신규 데이터 레코드를 생성합니다.
* **연결 코드(G1)**: FE `{src/...}` ↔ BE `{server/...}` (모듈 단위)
* **검증**: 서버/클라 **양방향 검증 필수** (CLAUDE.md 풀스택 규칙). 인증/스키마 변경 시 🔴 강화 검증 게이트.
* **Headers**:
  - `Content-Type: application/json`
  - `Authorization: Bearer {JWT_TOKEN}`

#### 요청 바디 (Request Body)
```json
{
  "title": "string (필수, 글자수 2~50자)",
  "content": "string (선택)",
  "category": "string (필수, allowlist: ['TASK', 'BUG', 'DOC'])",
  "priority": "number (선택, 기본값 0)"
}
```

#### 응답 (Response)

##### 🟢 201 Created (성공)
```json
{
  "success": true,
  "data": {
    "id": 1024,
    "title": "새로운 사내 기획서 작성",
    "content": "Biz-Ttori 템플릿 정리",
    "category": "DOC",
    "priority": 1,
    "createdAt": "2026-06-30T10:32:00.000Z"
  }
}
```

##### 🔴 400 Bad Request (유효성 검증 실패)
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "title의 길이는 최소 2자 이상이어야 합니다."
  }
}
```

##### 🔴 401 Unauthorized (인증 실패)
```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "유효하지 않거나 만료된 토큰입니다."
  }
}
```

---

## 🔗 관련 노트 (G-Brain 링크)

* **계약 레지스트리(G3)**: [[api-specs]] — 위 앵커들을 표에 등록
* **기획 출처**: `[[{기능 스펙 파일명}]]`
* **지식 인덱스**: [[g-brain-map]]
* **Git 연결(G2)**: 커밋에 `(ref: memory/api-specs.md#{domain}-create)` 형태로 기록
