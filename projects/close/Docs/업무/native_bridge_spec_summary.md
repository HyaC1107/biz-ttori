---
type: spec
status: 완료
project: "fanbird (close)"
created: 2026-07-06
updated: 2026-07-06
author: "Antigravity"
is_public: false
tags: [type/spec, status/완료, fanbird, rn, native-bridge]
related: ["[[projects/close/close|fanbird]]", "[[송출앱_기술설계서]]", "[[Native_Bridge_구현계획]]", "[[g-brain-map]]"]
---

# 🎬 fanbird-broadcast Native Bridge 작업 요약 및 설명

본 문서는 **fanbird-broadcast** 프로젝트(React Native bare CLI 기반 송출 앱)의 iOS 및 Android Native Bridge 구현 작업 현황과 핵심 아키텍처 결정을 요약한 보고서입니다.

상세 개발 계획 및 설계 스펙은 [[Native_Bridge_구현계획]] 및 [[송출앱_기술설계서]]에서 확인하실 수 있습니다.

---

## 1. 🎯 직접 구현 배경 (Why Native Bridge?)

1. **공식 React Native 송출 SDK 부재**
   - AWS 공식 IVS SDK는 라이브 시청용 Player에 대해서만 React Native 패키지를 배포하고 있으며, **라이브 송출용(Broadcast) SDK는 공식 RN 버전을 제공하지 않습니다.** (오직 iOS/Android 네이티브 라이브러리만 공식 배포)
2. **커뮤니티 패키지 기술 부패 (Maintenance Stopped)**
   - 기존 서드파티 오픈소스 패키지(`amazon-ivs-react-native-broadcast`)는 2022년 12월 이후 유지보수가 중단되어 최신 React Native(0.86.0) 버전 및 신규 아키텍처(New Arch)에서 빌드가 불가능한 호환성 에러가 발생합니다.
3. **최신 SDK 사양 확보**
   - 최신 IVS 기능(고주파 비디오 스트림 튜닝, 오디오 세션 튜닝 등)을 활용하기 위해 AWS 공식 최신 안정판 SDK(**v1.43.0** / 2026-06-04 기준)를 직접 연동하는 Native Bridge 개발을 확정했습니다.

---

## 2. 🏗️ 아키텍처 결정 사항

### 2.1 New Architecture (Bridgeless) 호환성 확보
- 앱에 New Architecture(`newArchEnabled=true`)가 활성화되어 있으나, 빠른 개발 및 초기 리스크 관리를 위해 **Legacy Interop Layer**를 활용합니다.
- 별도의 Codegen 스펙 정의 없이 legacy 스타일(`RCTBridgeModule`/`RCTEventEmitter`/`RCTViewManager`)로 작성하고 Interop Layer에 태우도록 아키텍처를 결정했습니다.

### 2.2 iOS SDK 통합: "로컬 podspec + vendored xcframework"
- AWS IVS Broadcast SDK는 **iOS 1.39.0부터 CocoaPods 공식 배포를 중단**했습니다.
- Cocoapods 기반인 이 프로젝트에서 수동 `project.pbxproj` 링킹 편집 위험을 피하고자, `AmazonIVSBroadcast.xcframework`(1.43.0)를 직접 다운로드하여 `LocalPods/AmazonIVSBroadcast/` 내에 **로컬 podspec으로 vendoring**하였습니다. `pod install`이 빌드 링킹, 임베딩, 서명 처리를 모두 안전하게 자동화합니다.

### 2.3 Android SDK 통합: Maven Central 연동 및 JDK 17 설정
- Android는 iOS와 달리 배포 중단 없이 Maven Central을 통해 의존성 주입이 가능합니다. (`com.amazonaws:ivs-broadcast:1.43.0`)
  - WebRTC/Stages용인 `:stages@aar` 분류자를 사용하면 RTMPS 송출이 불가능하므로, **순수 `ivs-broadcast` 아티팩트를 링킹**했습니다.
- 빌드 머신에 미리 설치되어 있던 Temurin JDK 17.0.9 버전을 빌드 시점에 연동하여 JDK 11 기준의 Android 빌드 블로커를 성공적으로 해소했습니다.

---

## 3. 📱 플랫폼별 구현 상세 및 이식된 파일 목록

세션을 단독 소유하는 싱글턴 `Controller`를 내부에 두고, JS 레이어와 이벤트를 주고받는 `Module` 및 `ViewManager`를 대칭 구조로 설계했습니다.

### 🍏 iOS (Swift / Objective-C)
- **`IVSBroadcastController.swift`**
  - AWS `IVSBroadcastSession`의 생명주기를 독점 소유하는 싱글턴 객체입니다.
- **`IVSBroadcastModule.swift` / `IVSBroadcastModule.m`**
  - JS 레이어로 네이티브 제어 메서드를 내보내고 `RCTEventEmitter`를 통해 방송 상태 및 에러 이벤트를 에미팅합니다.
- **`IVSCameraPreviewView.swift` / `IVSCameraPreviewViewManager.swift`**
  - JS 컴포넌트 `<IVSCameraPreview>`가 런타임에 직접 화면 레이아웃으로 사용할 수 있는 카메라 프리뷰 컴포넌트를 노출합니다. React Native 0.74+ New Renderer Interop이 자동 작동하여 legacy ViewManager도 정상적으로 호환됩니다.
- **권한**: `Info.plist`에 `NSCameraUsageDescription` / `NSMicrophoneUsageDescription` 문구를 추가 완료하였습니다.

### 🤖 Android (Kotlin)
- **`IvsBroadcastController.kt`**
  - Android 네이티브 IVS Session 싱글턴 컨트롤러입니다.
- **`IvsBroadcastModule.kt`**
  - `ReactContextBaseJavaModule`을 상속하여 JS 브릿지 역할을 담당합니다. IVS SDK의 스레드 제한 규칙 준수를 위해 `UiThreadUtil.runOnUiThread` 가드가 설정되어 있습니다.
- **`IvsCameraPreviewView.kt` / `IvsCameraPreviewViewManager.kt`**
  - `FrameLayout` 기반으로 IVS Session의 `getPreviewView()`를 바인딩하여 렌더링하는 뷰 컴포넌트입니다.
- **`IvsBroadcastPackage.kt`**
  - `MainApplication.kt`에 등록하기 위한 RN 패키지 래퍼 클래스입니다.
- **권한**: `AndroidManifest.xml` 내 권한 선언 및 `BroadcastScreen.tsx` 측에서 Android 전용 런타임 권한 획득 플로우(`PermissionsAndroid`)를 보강했습니다.

---

## 4. ⚙️ 제공하는 브릿지 인터페이스 (JS ↔ Native)

```ts
// IVSBroadcastModule 스텁 구조
interface IVSBroadcastModule {
  // 사용 가능한 카메라/마이크 기기 목록 취득 (URN, 명칭 매핑)
  listAvailableDevices(): Promise<{ video: DeviceInfo[]; audio: DeviceInfo[] }>;
  
  // 송출 세션 시작 (AWS EndPoint 및 스트림 키, 선택 기기 바인딩)
  startSession(params: {
    streamKey: string;
    ingestEndpoint: string;
    videoDeviceId: string;
    audioDeviceId: string;
  }): Promise<void>;
  
  // 송출 중단 및 리소스 해제
  stopSession(): Promise<void>;
  
  // 실시간 기기 스위칭 (전면/후면 카메라, 마이크 전환)
  exchangeDevice(oldDeviceId: string, newDeviceId: string): Promise<void>;

  // [이벤트 수신 - NativeEventEmitter]
  // - onConnectionStateChange: "connected" | "disconnected" | "reconnecting"
  // - onError: { code: string; message: string }
}
```
* **재연결 제어**: SDK 내장 `RetryState` 메커니즘을 적극 활용하여 임의 연결 유실 시 SDK가 자동으로 재연결을 시도하며, JS 측에는 상태값 갱신 및 UI 표시용 이벤트만 emit하도록 구성했습니다.

---

## 5. 🔍 핵심 검토 의사결정 및 특이사항

### 5.1 카메라 포커스 정책 결정 (Continuous Auto Focus)
- 기획 단계에서 제안되었던 "수동 터치 포커싱(Tap-to-Focus)"은 Android IVS SDK의 `CameraSource` API 제약상 기본 지원되지 않는 것으로 파악되었습니다. 
- 수동 제어를 강제하려면 커스텀 이미지 소스를 구성하고 CameraX를 모듈 내에서 100% 직접 핸들링해야 하므로 큰 규모의 추가 공수가 발생합니다. 
- 따라서 일정 준수를 위해 수동 터치 포커싱 기획은 기각(Drop)하고, 양대 플랫폼 모두 기본 디바이스가 보장하는 **연속 자동 초점(Continuous Auto Focus)** 정책을 그대로 유지하기로 최종 합의되었습니다.

### 5.2 백그라운드 / 화면 잠금 정책의 차이
- **Android**: Foreground Service + 지속 알림(Notification) 등록 메커니즘을 통해 백그라운드 기동 중에도 카메라/마이크 송출 유지가 기술적으로 지원됩니다 (Phase 1 대상).
- **iOS**: OS의 정책상 앱이 백그라운드로 전환되는 즉시 카메라 하드웨어 캡처가 강제 차단됩니다. 우회가 불가능하므로, iOS에서는 방송이 진행 중일 때 **자동 화면 잠금을 방지**하는 `UIApplication.shared.isIdleTimerDisabled = true` 수준으로 1차 조치하고 포그라운드 방송 유지를 권장하는 것으로 노선을 조율했습니다.

### 5.3 현재 빌드 및 검증 현황 (2026-07-02 기준)
- iOS 시뮬레이터 빌드(`xcodebuild`) 및 Android gradle 빌드(`:app:assembleDebug`)가 모두 **성공**적으로 클린 컴파일 통과 및 APK 생성을 완료했습니다.
- **Android 에뮬레이터 검증**: listAvailableDevices 호출 및 런타임 권한 승인, Android Camera API Open 단계까지 모두 정상 동작 확인(logcat 기준). 단, 에뮬레이터 특유의 GPU EGL 드라이버 한계로 에뮬레이터 화면 상의 프리뷰 렌더는 검은 화면으로 확인되어 실기기 테스트 단계에서 교차 검증이 필요합니다.
- **iOS 시뮬레이터 검증**: 카메라 기기가 탑재되지 않은 시뮬레이터 환경을 위해 코드 내 `TEST_MODE` 분기를 두어 모의 기기 바인딩 및 프리뷰 화면 상에 목업 커버를 적용하여 동작이 정상적으로 지속되도록 예외 처리를 완비했습니다.
