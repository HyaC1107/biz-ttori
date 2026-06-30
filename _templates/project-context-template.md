---
type: spec
status: 진행중         # 초안 → 진행중 → 완료 / 보류
project: "{프로젝트명}"
created: "{YYYY-MM-DD}"
updated: "{YYYY-MM-DD}"
is_public: false
tags: [type/spec, status/진행중]
repo_path: "/Users/.../{실제 레포 절대경로}"   # ★ 외부 코드 위치 (G5 포인터)
related: ["[[g-brain-map]]"]
---

# [프로젝트] {프로젝트명} — 컨텍스트

> **외장 두뇌 노트.** 코드는 `repo_path`의 외부 레포에 있다. 여기엔 상태·계약·포인터만 둔다.
> `claude`는 항상 `biz-ttori`에서 띄우고, 아래 절대경로로 외부 파일을 읽고/수정한다 (G5).

---

## 📍 지금 상태

```
프로젝트   : {프로젝트명}
실코드 위치 : /Users/.../{레포 경로}      ← 절대경로
스택       : {예: React Native + NestJS + PostgreSQL}
현재 단계   : {지금 무엇을 하고 있나}
다음 할 일  : {바로 다음 작업}
```

## 🗺️ 핵심 모듈 포인터 (G1 — 모듈 단위, 백틱 절대경로)

| 영역 | 모듈 | 절대경로 |
|:---|:---|:---|
| FE | {화면/컴포넌트} | `/Users/.../repo/src/...` |
| BE | {라우트/서비스} | `/Users/.../repo/server/...` |
| DB | {스키마/마이그레이션} | `/Users/.../repo/prisma/...` |

## 🔗 관련 노트 (볼트 내부는 wikilink)

* **API 계약(G3, SSOT)**: `projects/{프로젝트명}/api-specs.md` (이 프로젝트 계약의 단일 진실원) · 전역 [[api-specs]] 인덱스에 한 행 등록
* **기획/스펙**: `[[{스펙 파일명}]]`
* **지식 인덱스**: [[g-brain-map]]

## 🚧 블로커 / 결정 대기

- 없음
