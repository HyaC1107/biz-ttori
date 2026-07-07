---
type: spec
status: 완료
project: "fanbird (close)"
created: 2026-07-06
updated: 2026-07-06
author: "Antigravity"
is_public: false
tags: [type/spec, status/완료, fanbird, backend, websocket, redis]
related: ["[[projects/close/close|fanbird]]", "[[송출앱_기술설계서]]", "[[backend_code_review_summary]]", "[[g-brain-map]]"]
---

# 🌐 웹소켓(Socket.io)과 Redis Pub/Sub 연동 아키텍처 분석

본 문서는 **fanbird-backend** 프로젝트에서 실시간 데이터 송수신을 위해 웹소켓(Socket.io)과 Redis Pub/Sub을 함께 사용하는 구조적 이유를 분석한 보고서입니다.

관련 소스 코드:
* [socket.gateway.ts](file:///Users/linkcampus02/fanbird-backend/src/socket/socket.gateway.ts)
* [redis_subscriber.ts](file:///Users/linkcampus02/fanbird-backend/src/socket/redis_subscriber.ts)
* [product.service.ts](file:///Users/linkcampus02/fanbird-backend/src/product/product.service.ts)
* [package.json](file:///Users/linkcampus02/fanbird-backend/package.json)

---

## 1. 🚀 핵심 이유 1: 수평적 확장성 (Horizontal Scaling / Scale-Out)

실시간 라이브 커머스 서비스는 동시 접속자 수가 급격히 몰리기 때문에 백엔드 서버(NestJS) 인스턴스를 여러 대(예: PM2 클러스터, 오토스케일링 컨테이너 등) 띄워 트래픽을 분산해야 합니다.

* **세션 파편화 문제**:
  - 웹소켓은 클라이언트와 **특정 서버 인스턴스 1대** 사이에 지속적인 연결(Stateful Connection)을 맺습니다.
  - 판매자가 상품 노출 상태를 변경하여 인스턴스 A 서버로 API 요청이 전송되었을 때, 인스턴스 A가 본인에게 접속된 클라이언트들에게만 소켓 이벤트를 보내면 **인스턴스 B, C에 접속되어 있는 시청자들은 상품 변경 정보를 받지 못하는 현상**이 발생합니다.
* **Redis Pub/Sub을 이용한 해결**:
  - API 요청을 처리한 인스턴스 A가 Redis 채널(`send-stock-event`)에 이벤트를 발행(`publish`)합니다.
  - Redis 서버는 이 채널을 구독(`subscribe`)하고 있는 **모든 서버 인스턴스(A, B, C)**에 메시지를 실시간 복제 및 전파합니다.
  - 메시지를 수신한 모든 인스턴스가 각자 자신에게 접속한 웹소켓 클라이언트들에게 이벤트를 브로드캐스팅하여, 다중 서버 환경에서도 동기화 누락 없이 동일한 정보를 수신할 수 있게 됩니다.
  - 이를 증명하듯 [package.json](file:///Users/linkcampus02/fanbird-backend/package.json)에 `@socket.io/redis-adapter`가 포함되어 있어 인스턴스 간 소켓 세션 및 룸 데이터 동기화 어댑터로 사용하고 있음을 알 수 있습니다.

---

## 2. 🧩 핵심 이유 2: 느슨한 결합 (Decoupling) 및 관심사 분리

* **의존성 엉킴 방지**:
  - 상품 정보 변경(`product.service.ts`)이나 라이브 시간 업데이트(`live.service.ts`) 등의 비즈니스 로직 내부에서 실시간 전송을 위해 웹소켓 게이트웨이(`SocketGateway`) 인프라를 직접 참조하게 되면 모듈 간 결합도가 극도로 높아집니다.
* **관심사 분리**:
  - 서비스 레이어는 단순히 Redis라는 데이터 버스(Broker)에 이벤트를 던지는 것(`publish`)으로 책임을 끝냅니다.
  - 소켓 연동을 담당하는 [redis_subscriber.ts](file:///Users/linkcampus02/fanbird-backend/src/socket/redis_subscriber.ts)와 [socket.gateway.ts](file:///Users/linkcampus02/fanbird-backend/src/socket/socket.gateway.ts)는 오직 Redis 이벤트를 대기하고 있다가 소켓 클라이언트들에게 패킷을 뿌려주는 일에만 집중합니다.
  - 이로 인해 특정 모듈의 기능 변경이 웹소켓 인프라 전체에 영향을 주지 않으므로 유지보수성이 비약적으로 증가합니다.

---

## 3. ⚡ 핵심 이유 3: 비동기 처리를 통한 API 응답 속도 및 리소스 최적화

* 만약 상품 변경 API 내부에서 동시 접속 중인 수천~수만 명의 소켓 커넥션 리스트를 조회하고 루프를 돌며 동기식으로 브로드캐스팅 연산을 수행한다면, 해당 API의 응답 지연 시간(Latency)은 급격히 늘어나고 스레드가 점유되어 서버가 마비될 수 있습니다.
* API 서버는 상품 정보를 DB에 반영하고 Redis에 이벤트를 발행하는 매우 가벼운 비동기 작업만 처리한 뒤 **즉시 클라이언트에게 API 응답**을 보냅니다.
* 실제 브로드캐스팅 연산과 소켓 전송 작업은 소켓 모듈의 이벤트 핸들러가 별도의 비동기 컨텍스트로 처리하므로 CPU 및 메모리 리소스를 효율적으로 분배할 수 있습니다.
