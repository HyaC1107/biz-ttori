---
name: gbrain-map-sync
description: projects/ 하위의 실제 프로젝트 폴더들을 탐색하여 memory/g-brain-map.md의 프로젝트 노드 매핑 테이블을 자동으로 일치하도록 갱신해주는 지식 자동화 스킬입니다.
---

# 🗺️ gbrain-map-sync 스킬 실행 가이드 (젬또리 전용)

이 스킬은 비즈또리 워크스페이스 내에 새 외부 프로젝트 폴더가 생성되었을 때, 지식 인덱스 맵(`g-brain-map.md`)에 자동으로 매핑을 동기화하여 지식 일관성을 유지하도록 돕습니다.

## 🚦 실행 절차

1. **동기화 스크립트 실행:**
   * **명령어:** `./.agents/skills/gbrain-map-sync/scripts/sync.js`
   * **역할:** `projects/` 내부의 실제 프로젝트 디렉토리를 스캔하여 `memory/g-brain-map.md` 파일에 매핑 테이블을 동적 생성하고 덮어씁니다.
2. **사후 지식 검증:**
   * 테이블이 정상 갱신된 후, `./tools/gbrain-doctor.sh`를 구동하여 생성된 링크들이 정상인지 한 번 더 검사합니다.
