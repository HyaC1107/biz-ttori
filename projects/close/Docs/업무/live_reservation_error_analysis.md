---
type: spec
status: 완료
project: "fanbird (close)"
created: 2026-07-06
updated: 2026-07-06
author: "Antigravity"
is_public: false
tags: [type/spec, status/완료, fanbird, debug, error-analysis]
related: ["[[projects/close/close|fanbird]]", "[[송출앱_기술설계서]]", "[[g-brain-map]]"]
---

# 🔍 라이브 예약 실패 (POST /live/create-live 400) 원인 분석 보고서

웹 프로젝트(`close`)의 라이브 메이크 페이지에서 결제 모달 호출 및 라이브 예약 API 요청 시 **400 Bad Request** 에러가 발생하는 현상에 대한 원인 분석 및 해결 방안입니다.

관련 소스 코드:
* [LiveMake.tsx](file:///Users/linkcampus02/close/src/Page/Manage/LiveList/LiveMake.tsx)
* [CoinPaymentModal.tsx](file:///Users/linkcampus02/close/src/Page/Manage/LiveList/Modal/CoinPaymentModal.tsx)
* [Tools.js](file:///Users/linkcampus02/close/src/Component/tool/Tools.js)
* [live.dto.ts](file:///Users/linkcampus02/fanbird-backend/src/live/dto/live.dto.ts)

---

## 1. 🚨 에러 현상 요약
- **API**: `POST https://fanbird.live/F_shopping_dev/back/live/create-live`
- **결과**: `400 (Bad Request)`
- **증상**: 라이브 생성 버튼 클릭 시 데이터 밸리데이션 검증 실패로 인해 백엔드가 에러 응답을 반환하여 결제 및 예약 완료 처리가 진행되지 않음.

---

## ## 2. 🔍 핵심 에러 발생 원인

백엔드 서버의 글로벌 ValidationPipe 옵션 중 `forbidNonWhitelisted: true`(DTO에 없는 속성 에러)와 `transform: true` 및 `class-validator`가 켜져 있어, 프론트에서 넘어가는 DTO 데이터 규격이 단 하나라도 어긋날 경우 400 에러를 뱉게 됩니다.

### 🔴 원인 1: `make_date` 함수 리턴 포맷으로 인한 브라우저 날짜 파싱 실패 (사파리 등)
- [LiveMake.tsx](file:///Users/linkcampus02/close/src/Page/Manage/LiveList/LiveMake.tsx)의 `make_date`는 날짜 조립 시 다음과 같이 문자열을 반환합니다:
  ```js
  return `${formattedDate} ${timeHour}:00:00`; // 예: "2026-07-06 14:00:00"
  ```
- 부모 컴포넌트인 `LiveMake.tsx`는 이 값을 받아 `new Date(make_date(...))`를 실행하여 `live_start`와 `live_finish` 프롭스로 넘겨줍니다.
- **문제점**: 하이픈과 띄어쓰기가 조합된 날짜 형식(`"YYYY-MM-DD HH:mm:ss"`)은 Chrome에서는 파싱되지만, **Safari(사파리)** 브라우저에서는 표준 규격이 아니기 때문에 **`Invalid Date`**가 리턴됩니다.
- `Invalid Date`가 저장된 `Date` 객체는 `JSON.stringify` 과정에서 **`null`**로 변환되어 백엔드로 발송됩니다.
- 결과적으로 백엔드는 `live_start: null`을 수신하게 되고, `live.dto.ts`의 `@IsDate() @IsNotEmpty() live_start: Date;` 검증 조건에 걸려 400 Bad Request 에러가 발생합니다.

### 🔴 원인 2: `useCoin` 곱셈 연산 시 문자열 포맷 유틸 오용으로 인한 `NaN` 가능성
- [CoinPaymentModal.tsx](file:///Users/linkcampus02/close/src/Page/Manage/LiveList/Modal/CoinPaymentModal.tsx)의 52라인에서 소모 코인을 계산하는 코드는 다음과 같습니다:
  ```ts
  setUseCoin(live_limit * amountFormat(duration) * 3.8 * 1.2);
  ```
- **문제점**: [Tools.js](file:///Users/linkcampus02/close/src/Component/tool/Tools.js)의 `amountFormat(number)` 함수는 쉼표를 찍어 반환하는 **문자열** 변환 유틸입니다. 
- 만약 방송 예약 지속 시간(`duration`)이 1,000시간을 넘거나 하여 쉼표가 포함되면 `"1,000" * 3.8` 연산은 자바스크립트에서 **`NaN`**을 반환하게 됩니다. (쉼표가 없더라도 문자열과 숫자를 산술 연산하는 것 자체가 코드 오작용 리스크가 큽니다.)
- `useCoin`이 `NaN`이 되면 백엔드로 전송될 때 `coin: null`로 들어가서 `@IsNumber() @IsNotEmpty() coin: number` 검증에 실패해 400 에러를 뱉게 됩니다.

---

## 🛠️ 3. 해결 방안 (코드 수정 가이드)

### 3.1 `LiveMake.tsx` 내 `make_date` 개선 (날짜 객체 오작용 방지)
문자열을 쪼개어 다시 파싱하는 방식 대신 `Date` 객체의 표준 내장 메서드를 직접 수정하는 안전한 방식으로 변경하거나, 사파리에서도 안정적인 ISO 8601 표준 구분자인 `T` 포맷으로 조립해야 합니다.

```diff
  const make_date = (
    date: string,
    time: number[],
    type: "start" | "finish"
  ) => {
-   const getTimeHour = (hour: number) => (hour >= 10 ? hour : `0${hour}`);
-
-   let timeDate = new Date(date);
-   let timeHour = getTimeHour(
-     type === "start" ? time[0] : time[time.length - 1] + 1
-   );
-   if (timeHour === 24) {
-     timeDate.setDate(timeDate.getDate() + 1);
-     timeHour = "00";
-   }
-   const formattedDate = timeDate.toISOString().split("T")[0];
-   return `${formattedDate} ${timeHour}:00:00`;
+   let timeDate = new Date(date);
+   let targetHour = type === "start" ? time[0] : time[time.length - 1] + 1;
+   timeDate.setHours(targetHour, 0, 0, 0);
+   return timeDate.toISOString(); // ISO 8601 표준 포맷 반환
  };
```

### 3.2 `CoinPaymentModal.tsx` 내 코인 연산 로직 개선
문자열 포맷 유틸인 `amountFormat`을 산술 곱셈 연산에서 완전히 걷어내고 순수 숫자 타입으로 연산을 처리해야 합니다.

```diff
  useEffect(() => {
    const duration =
      moment(live_finish).diff(moment(live_start), "hours") || 24;
-   setUseCoin(live_limit * amountFormat(duration) * 3.8 * 1.2);
+   setUseCoin(live_limit * duration * 3.8 * 1.2); // 순수 숫자로 곱셈 처리
    stockCoin();
  }, [live_finish, live_start, live_limit]);
```

---

### 🔴 원인 3: `cancel_ticket` 신규 필수 필드 누락
- **에러 메시지**:
  `"cancel_ticket should not be empty"`, `"cancel_ticket must be a number conforming to the specified constraints"`
- **분석**: 백엔드의 라이브 예약 API에 "방송 중 제한적 취소 티켓 개수"인 `cancel_ticket` 필드가 숫자로 필수 등록되도록 업데이트되었으나, 프론트엔드 예약 폼에는 관련 입력창이 없으며 요청 바디에서도 누락되어 전송되었습니다.

### 🛠️ 3.3 `CoinPaymentModal.tsx` 내 `cancel_ticket` 필드 추가
API 요청 바디에 필수 필드인 `cancel_ticket: 0`을 기본값으로 할당하여 전송함으로써 검증을 통과시킵니다.

```diff
        const res = await api.post(url.Communication_url.create_live, {
          live_start,
          live_finish,
          live_limit,
          live_title,
          live_img,
          secret_yn: secret_yn ? "y" : "n",
          log_type: "사용",
          log_con: "라이브 예약",
          coin: useCoin,
+         cancel_ticket: 0, // 기본값 0장 할당하여 필수 밸리데이션 충족
        });
```
