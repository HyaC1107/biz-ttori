---
type: spec
status: 완료
project: "fanbird (close)"
created: 2026-07-06
updated: 2026-07-06
author: "Antigravity"
is_public: false
tags: [type/spec, status/완료, fanbird, debug, timezone]
related: ["[[projects/close/close|fanbird]]", "[[송출앱_기술설계서]]", "[[g-brain-map]]"]
---

# 🔍 송출앱 라이브 시작 불가 (예약된 방송 시간 아님) 원인 분석 보고서

모바일 송출앱(fanbird-broadcast)에서 "라이브 시작" 버튼을 클릭할 때, 예약 시간 범위 내임에도 불구하고 **"예약된 방송 시간이 아닙니다"**라는 경고 팝업이 노출되며 송출이 불가능한 현상에 대한 원인 분석 및 해결 방안입니다.

관련 소스 코드:
* [BroadcastScreen.tsx](file:///Users/linkcampus02/fanbird-broadcast/src/screens/Broadcast/BroadcastScreen.tsx)
* [live.service.ts](file:///Users/linkcampus02/fanbird-backend/src/live/live.service.ts)

---

## 1. 🚨 에러 현상 요약
- **발생 위치**: 모바일 송출앱의 방송 화면([BroadcastScreen.tsx](file:///Users/linkcampus02/fanbird-broadcast/src/screens/Broadcast/BroadcastScreen.tsx)) 내 `handleStart` 함수.
- **증상**: 한국 시각 기준으로 현재 예약된 라이브 방송 시작 시각이 정상 범위에 부합함에도 불구하고, 내부 비교 연산에서 범위 이탈로 판단해 경고 팝업이 발생함.

---

## 2. 🔍 핵심 에러 발생 원인 (Timezone Mismatch)

### 🔴 백엔드의 한국 시간(KST) 문자열 리턴
- 백엔드 [live.service.ts](file:///Users/linkcampus02/fanbird-backend/src/live/live.service.ts)의 `getLiveInfo`는 라이브 정보를 리턴할 때 타임존 오프셋이나 구분자 없이 포매팅된 현지 시간 문자열을 내려줍니다.
  ```ts
  live_start: moment(live.live_start).tz('Asia/Seoul').format('YYYY-MM-DD HH:mm:ss') // 예: "2026-07-06 12:00:00"
  ```

### 🔴 모바일 기기(시뮬레이터/에뮬레이터)의 시스템 타임존 오인
- 모바일 송출앱은 전달받은 문자열을 `new Date(liveInfo.live_start).getTime()` 로 파싱합니다.
- **문제점**: 
  1. 기기나 브라우저의 기본 시스템 타임존이 **UTC** 또는 미국 시간대로 설정되어 있는 시뮬레이터/에뮬레이터 환경인 경우, 타임존 오프셋이 생략된 `"2026-07-06 12:00:00"` 문자열은 **기기 로컬 기준(즉, UTC 12시)**으로 해석됩니다.
  2. UTC 12시는 **한국 시각(KST)으로 밤 21시**에 해당합니다.
  3. 현재 실제 한국 시각은 낮 12시(UTC 3시)이므로, `now (낮 12시) < start (밤 21시)` 비교문에 걸려 예약 시간이 시작되지 않은 것으로 오인하게 됩니다.
  4. 추가로 일부 구버전 JavaScript 모바일 엔진에서는 하이픈과 공백 조합 포맷(`"2026-07-06 12:00:00"`)에 대해 파싱 오류(`Invalid Date`)를 일으켜 비교가 어긋날 수도 있습니다.

---

## 🛠️ 3. 해결 방안 (코드 수정 가이드)

기기의 로컬 타임존 설정에 의존하지 않고, 항상 한국 표준시 오프셋(`+09:00`)과 ISO 8601의 `T` 구분자를 결합하여 파싱함으로써 시간대 왜곡을 완벽하게 차단합니다.

* **대상 파일**: [BroadcastScreen.tsx](file:///Users/linkcampus02/fanbird-broadcast/src/screens/Broadcast/BroadcastScreen.tsx)

```diff
  const handleStart = async () => {
    if (!selectedVideo || !selectedAudio) {
      Alert.alert('비디오 장치와 오디오 장치를 선택해주세요');
      return;
    }
    // TEST ONLY — 가짜 토큰으로도 실제 dev 백엔드가 응답할 때가 있어(인증 느슨),
    // 그 실제 live_start/live_finish가 지금 시각과 안 맞으면 여기서 막힌다.
    // 화면 흐름 확인 목적이므로 테스트 모드에서는 시간 검증 자체를 건너뛴다.
    if (liveInfo && !TEST_MODE_SKIP_BROADCAST_APIS) {
      const now = Date.now();
-     const start = new Date(liveInfo.live_start).getTime();
-     const finish = new Date(liveInfo.live_finish).getTime();
+     // 공백을 T로 바꾸고 KST 오프셋(+09:00)을 강제 결합하여 크로스 플랫폼 타임존 호환성 확보
+     const start = new Date(liveInfo.live_start.replace(' ', 'T') + '+09:00').getTime();
+     const finish = new Date(liveInfo.live_finish.replace(' ', 'T') + '+09:00').getTime();
      if (now < start || now > finish) {
        Alert.alert('예약된 방송 시간이 아닙니다.');
        return;
      }
    }
```
