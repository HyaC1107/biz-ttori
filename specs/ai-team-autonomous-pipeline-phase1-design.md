# 📋 [설계서] AI 팀 자율 파이프라인 Phase 1 — 자동 트리거 프로토타입 설계 (개정본)

이 문서는 클또리(PM 지시 및 검수 반영)의 피드백을 수용하여 개정된 **Phase 1(단일 워커 자동 트리거 프로토타입)**의 기술 설계서입니다.

---

## 1. 🛠️ 클또리 피드백 3건 반영 조치 설계

### 1.1. [조치 1] 시범 프로젝트 변경 (`biz-ttori` 자체 툴)
* **결정**: 배포 임박한 실무 프로젝트(`fanbird`)의 안전을 위해 시범 대상을 `biz-ttori` 자체 툴로 한정합니다.
* **프로젝트 등록**: `company/projects.json`에 `biz-ttori` 프로젝트를 공식 등록하여 `events.py` 검증을 통과하게 만듭니다.
  ```json
  {
    "id": "biz-ttori",
    "name": "⚙️ biz-ttori",
    "dept": "dev",
    "status": "active",
    "phase": "자체 툴링 개발",
    "note": "AI 자율 파이프라인 시범 프로젝트",
    "details": "자체 툴링 및 가드레일 개발",
    "keywords": ["biz-ttori", "또리", "자체툴"]
  }
  ```
* **필터링**: 자동 스케줄러는 오직 `project == "biz-ttori"`인 태스크만 스폰 대상으로 선별합니다.

---

### 1.2. [조치 2] 위험 행동 우회 방지 가드레일 개선 (`tasks.py` 수정)
* **문제점**: `requires_approval=True` 플래그가 찍혀도 이벤트 타입이 `task.created`일 경우 태스크가 `created` 상태로 남아 스케줄러가 자동 실행하는 취약점이 존재했습니다.
* **해결책**: `tasks.py`의 `build_tasks()` 내부에서 개별 이벤트를 순회할 때, `requires_approval: True` 플래그를 발견하면 강제로 해당 태스크의 `state`를 `"awaiting_approval"`(결재대기)로 승격합니다.
* **구현 방식**:
  ```python
  # tasks.py의 build_tasks() 루프 내부 수정안
  stage = EVENT_STAGE.get(etype)
  if e.get("requires_approval"):
      stage = "awaiting_approval"
  ```
  이를 통해 위험행동 태스크는 폴링 대상(`state == "created"`)에서 즉시 누락되어 결재 게이트에 잠기게 됩니다.

---

### 1.3. [조치 3] 동시성 파일 락 도입 (`spawn_queue.py` 수정)
* **문제점**: 30초 주기의 스케줄러와 PM 수동 트리거가 겹칠 시 race condition이 발생해 동시성 제한 캡(2)이 뚫릴 수 있습니다.
* **해결책**: Python 표준 라이브러리인 `fcntl` 모듈을 사용하여 파일 락(flock)을 도입합니다.
* **구현 방식**:
  ```python
  import fcntl
  
  LOCK_FILE = ROOT / "company" / "spawn-queue.lock"
  
  def claim(task_id: str, actor: str, project: str | None = None) -> bool:
      # 락 파일을 열고 배타적 잠금(LOCK_EX) 획득
      with open(LOCK_FILE, "w") as lf:
          try:
              fcntl.flock(lf, fcntl.LOCK_EX) # 동시성 블록
              
              # 기존 claim 로직 수행
              # _load() -> validation -> save()
              
          finally:
              fcntl.flock(lf, fcntl.LOCK_UN) # 잠금 해제
  ```

---

## 2. 🏗️ 구조 리팩터링 및 백그라운드 스케줄러 설계 (`serve.py`)

### 2.1. 인스턴스 메서드 분리
현재 `serve.py`의 `Handler` 인스턴스 내부에 묶여 있는 `_claim_and_run` 및 `_spawn_order_worker` 함수들을 모듈 레벨 함수로 격리하여, 웹 요청 핸들러와 백그라운드 스케줄러 스레드가 동시 참조할 수 있게 리팩터링합니다.

### 2.2. `TaskScheduler` 스레드 기동
* **기동**: `serve.py` 메인 함수 시작 시 백그라운드 데몬 스레드로 `TaskScheduler` 루프를 실행합니다.
* **폴링**: 30초 주기로 다음 로직을 순회합니다.
  ```python
  def task_scheduler_loop():
      while True:
          time.sleep(30)
          # 1. 태스크 상태 빌드
          tasks = build_tasks()
          
          # 2. 대기 상태이면서 시범 프로젝트 대상인 태스크 필터링
          pending_tasks = [
              t for t in tasks 
              if t["state"] == "created" and t["project"] == "biz-ttori"
          ]
          
          if not pending_tasks:
              continue
              
          # 3. 순차적으로 스폰 시도 (_claim_and_run)
          for task in pending_tasks:
              # 가용 슬롯이 차거나 가드레일에 막히면 _claim_and_run이 False 반환
              success = spawn_worker_for_task(task)
              if not success:
                  break # 다음 루프 때 재시도
  ```
