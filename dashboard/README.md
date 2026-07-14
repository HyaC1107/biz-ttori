# dashboard/ — AI 회사 대시보드

봇 활동을 이벤트 로그로 쌓고, 현황판·3D 사무실 뷰로 관전/결재하는 로컬 대시보드.
정본(SSOT)은 `ttori/tool-spec/biz-ttori`이고, 여기는 그 이식본이다.

## 실행

```bash
python3 dashboard/engine/serve.py     # 포트 8787, 127.0.0.1 전용
```

- 현황판: http://127.0.0.1:8787/dashboard/web/board.html
- 3D 사무실: http://127.0.0.1:8787/dashboard/web/dashboard3d.html

> ⚠️ **반드시 레포 루트에서 실행한다.** 서버는 `CLAUDE.md`가 있는 폴더를 루트로 잡아 정적 서빙한다.

## 데이터

| 파일 | 성격 | git |
|:---|:---|:---|
| `company/projects.json` | 부서·프로젝트·봇 명단 (SSOT). 이벤트의 `project`는 여기 등록된 id만 허용 | 추적 |
| `company/events.jsonl` | 봇 활동 이벤트 로그 | **미추적** (환경마다 새로 쌓임) |
| `company/procs.json` | 이 환경에서 감시할 프로세스 (선택) | 추적 |

`events.jsonl`이 없으면 대시보드는 **🟢 LIVE — 이벤트 없음**으로 뜬다. 정상이다.

## 이 환경에 없는 기능

- **토큰 HUD** — `~/.claude` 트랜스크립트가 있을 때만 표시된다. 없으면 자동으로 숨는다.
- **프로세스 감시** — 기본값은 대시보드 서버 하나뿐이다. 더 감시하려면 `company/procs.json`에 선언한다:

```json
{ "procs": [
  { "key": "api", "name": "FMS 백엔드", "match": ["uvicorn", "app.main:app"],
    "port": 8000, "desc": "로컬 개발 서버", "start": "uv run uvicorn app.main:app" }
] }
```

`match`의 문자열이 **모두** 들어간 프로세스를 그 프로그램으로 본다. 이 목록은 대시보드에서
**종료 가능한 대상의 화이트리스트**이기도 하니, 넣기 전에 대상이 맞는지 확인할 것.
