# projects/ — 외부 프로젝트별 두뇌 (허브 모델)

> **biz-ttori는 외장 두뇌다. 코드는 외부 폴더에 그대로 있고, 여기엔 그 프로젝트의 *컨텍스트·계약·기획*만 둔다.**
> 규칙: [`CLAUDE.md`](../CLAUDE.md) 🧠 지브레인 **G5(외장 두뇌 모델)**.

---

## 구조

실프로젝트가 붙으면 폴더 하나를 만든다:

```
projects/
└── <프로젝트명>/
    ├── context.md          ← 이 프로젝트 상태 + 실코드 절대경로(포인터)
    ├── api-specs.md         ← FE↔BE 계약 (_templates/api-spec-template.md 기반, G3)
    └── (필요 시) context-frontend.md / context-backend.md / context-db.md
```

코드는 **복사하지 않는다.** `context.md`에 외부 레포의 **절대경로 포인터**만 적는다.

## 철칙

1. **`claude`는 항상 biz-ttori에서 띄운다.** (규칙·분신·G-Brain 로드) 외부 폴더 파일은 절대경로로 접근.
2. **외부 코드 참조 = 백틱 절대경로** `` `/Users/.../repo/src/...` ``. wikilink `[[..]]`는 볼트 안에서만.
3. 새 프로젝트 추가 시 [`memory/g-brain-map.md`](../memory/g-brain-map.md) 프로젝트 노드 표에 한 행 등록.
4. 프로젝트 컨텍스트는 여기, **전역 상태**는 [`memory/context.md`](../memory/context.md)(얇은 라우터)에.

## 새 프로젝트 시작 체크리스트

- [ ] `projects/<name>/` 생성
- [ ] `context.md` 작성 — `_templates/project-context-template.md` 복사 → 실코드 절대경로 기입
- [ ] `api-specs.md` 작성 — `_templates/api-spec-template.md` 기반
- [ ] `g-brain-map.md` 프로젝트 노드 표에 등록
- [ ] (실연동) Postgres/GitHub MCP 서버 연결 검토
