# agents/ — (레거시 참고용 명세)

> ⚠️ **이 폴더는 사람이 읽는 역할 명세 문서다.** 실제로 클또리가 호출하는 **실행 가능한 서브에이전트**는
> `.claude/agents/*.md`(frontmatter 포함)에 있다. 정의를 수정할 때는 **`.claude/agents/`** 쪽을 고칠 것.

## 실행 에이전트(.claude/agents/)와 권한 격리

| 에이전트 | 계층 | Write 권한 |
|:---|:---|:---|
| planner | 생성(설계) | ❌ (설계만 반환) |
| coder | 생성(구현) | ✅ 코드 |
| reviewer | **검증** | ❌ (adversarial, 지적만) |
| tester | 검증 | ⚠️ 테스트 파일만 |
| writer | 생성(문서) | ✅ 문서만 |

핵심 원칙: **코드를 작성한 분신(coder)이 자기 코드를 리뷰하지 않는다**(확증편향 방지). 검증은 독립된 reviewer/tester가 담당한다.
