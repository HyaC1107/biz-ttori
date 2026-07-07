---
type: spec
status: 완료
project: "fanbird (close)"
created: 2026-07-06
updated: 2026-07-06
author: "Antigravity"
is_public: false
tags: [type/spec, status/완료, fanbird, ios, test-guide]
related: ["[[projects/close/close|fanbird]]", "[[송출앱_기술설계서]]", "[[g-brain-map]]"]
---

# 📱 iOS 실기기 연동 및 송출 테스트 가이드

모바일 송출앱(fanbird-broadcast)의 iOS 실기기(iPhone/iPad) 빌드 배포, 하드웨어(카메라/마이크) 연동 및 실제 RTMPS 송출 검증을 수행하기 위한 가이드라인입니다.

관련 설정 파일:
* [BroadcastScreen.tsx](file:///Users/linkcampus02/fanbird-broadcast/src/screens/Broadcast/BroadcastScreen.tsx)
* `ios/FanbirdBroadcast.xcworkspace` (Xcode 프로젝트)

---

## 1. 🔑 1단계: Apple 개발자 계정 서명 설정 (Code Signing)
iOS 실기기에 앱을 배포하려면 Apple의 유효한 인증서 서명이 필수입니다. (무료 개인 계정도 7일 제한 서명 가능)

1. macOS 머신에서 Xcode를 열고, `ios/FanbirdBroadcast.xcworkspace` 워크스페이스 파일을 엽니다.
2. 좌측 내비게이터 상단의 **FanbirdBroadcast** 프로젝트 노드를 선택하고, **Signing & Capabilities** 탭으로 이동합니다.
3. **Team** 선택 박스에서 본인의 Apple 개발자 계정을 지정합니다.
4. **Bundle Identifier**가 `live.fanbird.broadcast`로 고유화되어 있는지 확인합니다. (기본 React Native example 도메인은 서명 충돌이 날 수 있습니다.)

---

## 🔌 2단계: 물리 기기 연결 및 신뢰 설정
1. USB-to-Lightning/C타입 케이블을 이용하여 Mac과 iPhone을 연결합니다.
2. iPhone 화면에 "이 컴퓨터를 신뢰하시겠습니까?" 팝업이 활성화되면 **[신뢰]**를 누르고 패스코드를 입력합니다.
3. **[중요 - iOS 16 이상 필수]**: 
   - iPhone의 **설정 ➡️ 개인정보 보호 및 보안 ➡️ 개발자 모드 (Developer Mode)** 메뉴를 켭니다.
   - 안내에 따라 iPhone을 재부팅한 뒤, 화면에 노출되는 개발자 모드 켜기 확인 팝업을 승인합니다.

---

## 🏗️ 3단계: Xcode 빌드 및 기기 실행
1. Xcode 상단 스키마 선택 도구(시뮬레이터 선택 영역)에서 **연결된 실물 iPhone 기기명**을 타겟으로 선택합니다.
2. `Cmd + R` (또는 재생 버튼)을 눌러 프로젝트 빌드 및 실기기 전송을 개시합니다.
3. **개발자 프로파일 신뢰 처리 (최초 1회 필수)**:
   - 빌드가 성공적으로 끝난 뒤 기기에서 앱이 켜질 때 "신뢰하지 않는 개발자" 경고가 뜨며 강제 종료될 수 있습니다.
   - iPhone의 **설정 ➡️ 일반 ➡️ VPN 및 기기 관리** 메뉴로 이동합니다.
   - 본인의 Apple ID가 적힌 개발자 앱 항목을 탭하고 **[신뢰(Trust)]** 처리를 완료한 후 다시 앱을 기동합니다.

---

## 🎬 4단계: 실기기 송출 테스트 모드 검증

기본 송출앱에는 카메라가 없는 시뮬레이터 환경을 위해 더미 프리뷰(목업) 및 API 모의 데이터 우회 장치(`TEST_MODE`)가 설정되어 있습니다. 실기기 테스트 시에는 이를 해제하여 실성능을 교차 검증합니다.

* **수정 파일**: [BroadcastScreen.tsx](file:///Users/linkcampus02/fanbird-broadcast/src/screens/Broadcast/BroadcastScreen.tsx)

### 📸 4.1 카메라/마이크 물리 렌더링 확인 (스트림키가 없는 경우)
- `TEST_MODE_COVER_PREVIEW_WITH_MOCK` 상수를 **`false`**로 변경합니다.
- 기기에서 앱을 실행해 방송 화면에 진입하면 시뮬레이터의 검은 목업 화면이 아닌, **물리 카메라 렌더링 프리뷰 뷰가 화면 배경으로 정상 노출**되는지 시각적으로 검증합니다.

### 📡 4.2 실제 IVS RTMPS 송출 검증 (스트림키 확보된 경우)
- `TEST_MODE_SKIP_BROADCAST_APIS` 상수를 **`false`**로 변경합니다.
- 오늘 날짜 예약 방송에 정상 진입하여 백엔드로부터 발급된 `streamKey`와 `I_Epoint`가 네이티브 Broadcast SDK 세션에 올바르게 연동되어 송출이 정상 개시되는지 체크합니다.
- AWS IVS 관리 콘솔 상에서 송출 상태가 **"실시간(Live)"** 상태로 바뀌고, 웹 시청자 브라우저에 송출 스트림이 저지연으로 수신되는지 End-to-End로 최종 검증합니다.

---

## 🔍 5. Xcode에서 실기기(iPhone 13)가 목록에 뜨지 않을 때의 해결 방안

물리 iPhone 13 기기를 Mac에 연결했음에도 Xcode 빌드 대상(Target) 목록에 노출되지 않을 경우 아래 항목들을 순서대로 점검합니다.

### 1. ⚙️ iOS 및 Xcode 버전 호환성 체크 (가장 빈번함)
- 연결된 iPhone 13의 iOS 버전(예: iOS 17.5 또는 18.0)이 Mac에 설치된 Xcode 버전보다 높으면 기기 목록에 표시되지 않거나 **"Unavailable"** 상태로 숨겨집니다.
- Xcode 메뉴 상단 `Window ➡️ Devices and Simulators` (단축키 `Cmd + Shift + 2`)를 켜서 연결된 iPhone 옆에 **"iOS version mismatch"** 혹은 **"Not Ready"** 노란색 경고가 떠 있는지 확인해 봅니다. 이 경우 Xcode 업데이트가 필요합니다.

### 2. 🛡️ 개발자 모드 (Developer Mode) 켜기 여부 확인
- iOS 16 이상 기기에서는 개발자 모드가 비활성화되어 있으면 Xcode 타겟 목록에 기기가 전혀 나타나지 않습니다.
- iPhone의 **설정 ➡️ 개인정보 보호 및 보안 ➡️ 개발자 모드**가 반드시 **[켬]** 상태로 되어 있고, 재부팅 후 뜨는 2차 승인 팝업까지 완료했는지 다시 팩트체크합니다.

### 3. 🔌 컴퓨터 신뢰 팝업 승인 재시도
- iPhone을 연결할 때 패스코드를 치고 **"이 컴퓨터를 신뢰함"**을 명시적으로 수락했는지 확인합니다.
- 기기 인식이 꼬였을 경우, 케이블을 분리했다가 다시 연결하여 신뢰 팝업이 다시 뜨는지 확인하고 재승인해 줍니다.

### 4. 🧵 정품/MFi 인증 데이터 케이블 사용
- 단순 충전용 USB-C/Lightning 케이블은 전력만 공급하고 데이터 전송 라인이 없어 Xcode가 인식하지 못합니다. MFi 인증 정품 데이터 전송 케이블을 사용하고, USB 허브 대신 Mac 본체 포트에 직접 꽂는 것을 권장합니다.

