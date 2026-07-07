---
type: spec
status: 완료
project: "fanbird (close)"
created: 2026-07-06
updated: 2026-07-06
author: "Antigravity"
is_public: false
tags: [type/spec, status/완료, fanbird, playstore, appstore, review-checklist]
related: ["[[projects/close/close|fanbird]]", "[[송출앱_기술설계서]]", "[[g-brain-map]]"]
---

# 🚀 모바일 송출앱 마켓 심사(App Store & Play Store) 대비 체크리스트

모바일 송출앱(fanbird-broadcast)을 App Store 및 Google Play Store에 출시하기 위한 심사 제출 전 필수 보완 및 대비 사항들을 분석한 체크리스트입니다.

---

## 1. 🔑 [최고 리스크] 데모 계정 및 심사용 모의 환경 구축 (Guideline 2.1)
애플 및 구글 심사관(대부분 해외)은 앱을 다운로드받아 **반드시 로그인 및 주요 핵심 기능(라이브 송출)을 직접 실행**해 봅니다. 이 단계에서 에러가 나면 즉시 리젝트(Reject)됩니다.

* **대비 방안**:
  1. **심사용 데모 계정(Test Account) 제공**:
     - 심사 정보 입력 란에 심사관 전용으로 로그인 가능한 **테스트용 판매자 계정 ID/PW**를 명시해야 합니다.
  2. **심사용 백엔드 API 바이패스(Bypass) 처리**:
     - 심사관이 임의의 시각(예: 미국 시간 새벽 등)에 "라이브 시작" 버튼을 누르므로, 백엔드의 `getLiveInfo` 및 `getStreamInfo` API는 **심사 전용 테스트 계정 요청에 대해 항상 날짜 검증을 패스시키고, Mocking된 스트림키와 Ingest Endpoint를 정상 리턴**해 주도록 백엔드를 임시 패치해야 합니다. (혹은 앱 단에서 심사 기간 한정으로 테스트 플래그를 켜서 밸리데이션과 실제 SDK 개시 단계를 bypass하도록 처리해야 합니다.)

---

## 2. 🚷 판매자 전용 폐쇄형 앱 설명 방어 (Guideline 2.5.11)
일반 구매자가 가입할 수 없고 스토어에 이미 가입된 판매자만 사용하는 어드민 성격의 앱이므로, 일반 소비자의 혼란을 막기 위해 가이드라인 방어가 필요합니다.

* **대비 방안**:
  - 심사 제출 시 메모(Review Notes)에 다음과 같은 설명을 명시해야 합니다.
    > *"본 앱은 fanbird.live에 정식 등록된 입점 판매자들의 모바일 스트리밍 송출을 돕기 위한 전용 어드민 도구(Seller App)입니다. 일반 소비자의 결제 및 라이브 시청은 웹 사이트(https://fanbird.live)를 통해 진행되며, 앱 내부에서는 일반 구매자 회원가입 및 결제를 제공하지 않습니다."*

---

## 3. 🧾 [면제 대상] 회원 탈퇴(계정 삭제) 기능 탑재 의무 (Guideline 5.1.1(v) 면제)
현재 송출앱([LoginScreen.tsx](file:///Users/linkcampus02/fanbird-broadcast/src/screens/Login/LoginScreen.tsx)) 내부에는 소셜 로그인이나 회원 가입, 계정 찾기 등의 기능이 일절 없이 **순수 로그인 창구만 존재**하므로, Apple의 *"계정 생성을 지원하는 앱에만 탈퇴 기능을 의무화한다"*는 규정에 따라 **기능 구현 면제 대상**입니다.

* **심사 대응 및 소명 방안**:
  - 간혹 심사관이 로그인 화면의 존재만 보고 기계적으로 리젝트하는 경우가 있습니다. 이 경우 앱을 수정하지 않고 **App Store Connect 해결 센터(Resolution Center)**를 통해 아래와 같이 소명하여 해결합니다.
  - 소명 템플릿:
    > *"Our app is a dedicated streaming utility for registered merchants on fanbird.live. It does not support or provide any account creation (sign-up) flow within the app. Therefore, according to Guideline 5.1.1(v), this app is exempt from the in-app account deletion requirement."*

---

## 📹 4. 하드웨어 권한 안내 및 사전 고지 정책 대응 (Info.plist / OS별 차이)
앱이 카메라와 마이크 권한을 사용하므로 양대 마켓의 권한 정책에 맞게 대비해야 합니다. **iOS와 Android는 권한 안내의 작동 메커니즘이 다릅니다.**

*   **iOS (Info.plist 시스템 팝업 텍스트 커스텀)**:
    - iOS는 시스템이 띄우는 권한 팝업 내 텍스트를 개발자가 직접 지정할 수 있으며, 설명이 구체적이지 않으면 거절됩니다.
    - `NSCameraUsageDescription`: *"라이브 방송 송출 시 실시간 비디오 화면을 캡처하고 렌더링하기 위해 카메라 권한이 필요합니다."*
    - `NSMicrophoneUsageDescription`: *"라이브 방송 송출 시 방송 오디오 및 목소리를 송출하기 위해 마이크 권한이 필요합니다."*
*   **Android (눈에 잘 띄는 사전 고지 - Prominent Disclosure 의무)**:
    - 안드로이드는 시스템 권한 팝업의 텍스트를 개발자가 임의로 수정할 수 없습니다. (OS 기본 문구 고정 노출)
    - 대신 구글 플레이 정책에 따라, 시스템 권한 팝업이 뜨기 전에 **앱 내 자체 UI 팝업(Disclosure)을 먼저 띄워 "카메라/마이크 권한이 필요한 구체적인 목적"을 안내하고 사용자의 명시적인 동의(확인 버튼 클릭)를 받는 동선**이 존재해야 합니다.
    - 개인정보 처리방침 내에만 고지하거나, 사전 안내 팝업 없이 곧바로 시스템 팝업을 띄울 시 심사에서 거절될 수 있습니다. (코어 기능이라 팝업이 면제되는 경우에도 플레이 콘솔 내 Data Safety 섹션 작성이 필수적입니다.)

---

## 📡 5. 네트워크 단절 등 예외 상황 방어 (Guideline 2.1)
심사관은 앱 동작 중 임의로 인터넷 연결을 차단(비행기 모드 활성화)하여 앱이 크래시되는지 테스트하곤 합니다.

* **대비 방안**:
  - API 호출 에러 시 앱이 꺼지지 않고 "네트워크 연결이 불안정합니다" 등 토스트나 팝업으로 Graceful하게 얼럿 처리하도록 가드해야 합니다.
  - Native Bridge 단에서 스트리밍 순단 시 SDK가 자동 재연결(`RetryState`)을 시도하는 과정이 UI 화면(예: '재연결 중...' 로딩 인디케이터 노출)에 안전하게 반영되도록 화면 단을 보완해야 합니다.
