---
title: Native Bridge 구현계획
project: "[[projects/close/close|fanbird]]"
tags: [plan, native-bridge]
status: 진행중
created: 2026-07-02
---

[[송출앱_기술설계서]] §5의 인터페이스 초안을 실제 구현 순서/방식으로 구체화한 문서.

## 1. 목적/범위 & 직접 구현 사유 (Why Native Bridge?)

`fanbird-broadcast`의 `src/native/IVSBroadcastModule.ts`는 JS 인터페이스만 고정된 스텁 상태입니다. 실제 iOS(Swift) 및 Android(Kotlin) 네이티브 모듈을 작성해 AWS IVS Broadcast SDK와 물리적으로 연결합니다.

### ⚠️ 왜 라이브러리를 쓰지 않고 직접 구현(Native Bridge)하나요?
1. **공식 React Native 송출 SDK 부재:** AWS는 라이브 시청용 플레이어 SDK만 RN 버전을 배포할 뿐, **라이브 송출용(Broadcast) SDK는 공식 React Native 패키지를 제공하지 않고 있습니다.** (오직 iOS/Android 네이티브 라이브러리만 공식 배포)
2. **커뮤니티 패키지의 기술 부패 (Maintenance Stopped):** 과거에 배포되었던 서드파티 패키지(`amazon-ivs-react-native-broadcast`)는 2022년 12월 이후 메인터넌스가 영구 중단되었습니다. 이로 인해 최신 React Native(0.86.0) 버전 및 신규 아키텍처(New Arch)에서 빌드가 불가능한 심각한 호환성 에러가 발생합니다.
3. **최신 SDK 버전(v1.43.0+) 및 최신 기능 확보:** 구버전 서드파티 패키지는 IVS의 고주파 비디오 스트림 튜닝 및 최신 기기 스위칭 인터페이스를 담아내지 못합니다. 
4. **iOS CocoaPods 배포 동결 대응:** AWS가 iOS CocoaPods 배포를 정지함에 따라, 수동으로 `XCFramework`를 임베딩하는 선언적 빌드 링킹 환경을 직접 제어하기 위함입니다.

* **이번 착수 범위: iOS만.** Android는 JDK 11 → 17~20 미설치로 빌드 자체가 안 되는 상태(기존 확인된 블로커) — JDK 설치 전까지 보류. (단, JDK 설치 시 이 문서를 토대로 대칭 구현 시작)
- 카메라 프리뷰(UI 컴포넌트)까지 포함 — `BroadcastScreen.tsx`의 `previewPlaceholder`(현재 정적 이미지)를 실제 네이티브 카메라 뷰로 교체하는 것까지가 이번 스코프.

## 2. 아키텍처 결정: TurboModule(Codegen) 대신 Legacy Interop

프로젝트는 `newArchEnabled=true`(New Architecture)다. 그러나:

- 현재 `package.json`에 `codegenConfig`가 없고, 커스텀 네이티브 모듈 인프라가 전혀 세팅 안 되어 있음.
- New Architecture는 **Legacy Interop Layer**를 통해 기존 `RCTBridgeModule`/`RCTEventEmitter` 스타일 모듈과 `RCTViewManager`를 별도 Codegen 스펙 없이도 그대로 지원한다.
- 1인 개발 체제 + 타이트한 일정(RN CLI를 Expo 대신 택한 것과 같은 이유 — 직접 제어·낮은 초기 리스크)을 고려해 **Legacy 스타일로 작성하고 Interop Layer에 태운다.** Codegen 전환은 향후 여유 있을 때 검토.

### 2.1 SDK 통합 방식: SPM 대신 "vendored xcframework + 로컬 podspec" 채택 [실제 진행, 2026-07-02]

설계서 초안은 "SPM"이었으나, 실제 착수 시 다음을 확인하고 방식을 조정했다:
- IVS Broadcast SDK는 **iOS 1.39.0부터 CocoaPods 배포 완전 중단**(CocoaPods trunk엔 1.9.1까지만 잔존). 공식 권장은 SPM 또는 xcframework 직접 통합. [context7/AWS 공식 문서 확인]
- 최신 버전 **1.43.0** 확정(CDN `https://broadcast.live-video.net/1.43.0/AmazonIVSBroadcast.xcframework.zip`, 그 이상 버전은 403). 젬또리 리서치와 일치.
- 이 프로젝트는 **CocoaPods 기반 RN CLI**다. 여기에 raw SPM을 섞으려면 `project.pbxproj` 손편집이 필요해 위험 → 대신 **xcframework를 내려받아 로컬 podspec으로 vendoring**(`ios/LocalPods/AmazonIVSBroadcast/`). `pod install`이 링킹·임베딩·코드사인 pbxproj 수술을 전부 자동 처리 → 손편집 위험 제거. xcframework에 device(`ios-arm64`)+simulator 슬라이스 모두 포함 확인.

### 2.2 New Architecture(bridgeless) 확인

iOS도 `RCT_NEW_ARCH_ENABLED=1`(bridgeless) 활성 상태.
- **NativeModule**(메서드+이벤트): TurboModule interop으로 legacy `RCT_EXTERN_MODULE`이 자동 지원 → 그대로 동작(빌드/링크 검증 완료).
- **커스텀 View**(카메라 프리뷰): legacy ViewManager interop을 별도로 켜야 함 → §3의 프리뷰 작업으로 분리, RN 공식 문서로 정확한 활성화 방법 확인 후 진행.

## 3. iOS 작업 순서

1. ~~SPM 의존성 추가~~ → **vendored xcframework + 로컬 podspec** (위 §2.1). ✅ 완료 — Podfile에 `pod 'AmazonIVSBroadcast', :path => 'LocalPods/AmazonIVSBroadcast'`, `pod install` 성공(1.43.0 통합 확인).
2. ✅ **완료** — 세션 소유권을 `IVSBroadcastController.swift`(싱글턴)에 두고, `IVSBroadcastModule.swift`(`RCTEventEmitter`)는 얇은 어댑터로 구현. 모듈/프리뷰뷰가 같은 세션을 공유.
   - `listAvailableDevices()` → `IVSBroadcastSession.listAvailableDevices()`(클래스 메서드)를 type(camera/microphone)로 필터, `{id: urn, name: friendlyName}`로 매핑
   - `startSession({streamKey, ingestEndpoint, videoDeviceId, audioDeviceId})` → `ensureSession`(선택 장치 attach)→`start(with:streamKey:)`. ingest는 `rtmps://<endpoint>:443/app`로 정규화
   - `stopSession()` → `session.stop()`
   - `exchangeDevice(oldUrn, newUrn)` → `exchangeOldDevice(_:withNewDevice:onComplete:)`
   - delegate: `didChange(state)` / `didChange(retryState)` / `didEmitError` → `onConnectionStateChange`(connected/disconnected/reconnecting) / `onError`(code,message)로 emit. **재연결은 SDK 내장 RetryState 활용**
3. ✅ **완료** — `IVSBroadcastModule.m`(`RCT_EXTERN_MODULE`/`RCT_EXTERN_METHOD`). New Arch interop으로 자동 등록.
4. **Bridging Header 불필요** — ObjC(.m)→Swift 방향 참조가 없어(RCT_EXTERN_MODULE은 런타임 룩업), Swift→ObjC는 `import AmazonIVSBroadcast` 모듈 임포트로 해결. 브릿징 헤더 없이 빌드 성공 확인.
5. ✅ **완료** — 카메라 프리뷰 뷰(`IVSCameraPreviewView.swift` + `IVSCameraPreviewViewManager.swift/.m`). JS `src/native/IVSCameraPreview.tsx`(`requireNativeComponent('IVSCameraPreviewView')`)로 노출, `BroadcastScreen`에 배경 레이어로 연결. **RN 0.74+에서 New Renderer Interop이 기본 활성이라 legacy ViewManager 별도 등록 불필요**(RN 공식 문서 확인). BUILD SUCCEEDED. 시뮬레이터는 카메라 없어 검은 화면 → TEST_MODE에서 기존 목업 배경을 위에 덮어 UI 확인 유지, 실기기(TEST_MODE off)에선 실제 프리뷰 노출.
6. ✅ **완료** — `Info.plist`에 `NSCameraUsageDescription`/`NSMicrophoneUsageDescription` 추가.

### 3.1 빌드 검증 결과 [2026-07-02]

- `xcodebuild` 시뮬레이터 빌드 **BUILD SUCCEEDED** — Swift 3파일 + xcframework 링크 정상.
- 발견·수정한 컴파일 이슈 1건: `didChangeRetryState:`의 Swift 임포트 이름이 state 콜백과 동일한 `broadcastSession(_:didChange:)`(파라미터 타입 오버로드) → 시그니처 정정.

## 4. Android 작업 순서 (블로커 해제 후 착수)

- JDK 17~20 설치 확인 → `android/app/build.gradle`에 `implementation 'com.amazonaws:ivs-broadcast:1.43.0:stages@aar'` 추가
- `IVSBroadcastModule.kt`(`ReactContextBaseJavaModule` + `RCTDeviceEventEmitter`), `IVSPreviewViewManager.kt`(`SimpleViewManager<View>`) — iOS와 동일한 메서드/이벤트 시그니처로 대칭 구현
- Foreground Service(백그라운드 유지)는 이번 Native Bridge 스코프에서 **제외** — §6 백그라운드 정책은 별도 작업으로 분리(기술설계서 §6 기준)

## 5. 검증 계획 (AWS 스트림키 미확보 상태 기준)

스트림키/실기기/Apple Developer 계정은 아직 미확보(PM: "프론트 정리 먼저") — 그 상태에서 iOS 시뮬레이터로 검증 가능한 범위와 불가능한 범위를 구분한다.

| 항목 | 시뮬레이터 검증 가능 여부 |
| :--- | :--- |
| SPM 빌드 성공(컴파일) | ✅ 가능 |
| 카메라/마이크 권한 프롬프트 노출 | ✅ 가능 (시뮬레이터는 가상 카메라 제공) |
| `listAvailableDevices()` 실제 목록 반환 | ✅ 가능 (시뮬레이터 기본 카메라·마이크 인식) |
| `IVSImagePreviewView` 프리뷰 렌더링 | ⚠️ 부분 가능 — 시뮬레이터 카메라가 실물 없이 빈 화면/테스트 패턴일 수 있음 |
| `startSession()` 실제 RTMPS 송출 성공 | ❌ 불가 — 유효한 스트림키/ingest endpoint 필요. 에러 핸들링 경로(잘못된 키로 실패 시 `onError` emit)까지만 확인 |
| 실기기 백그라운드/화면잠금 동작 | ❌ 불가 — 실기기 필요, 이번 스코프 아님(§4 참고) |

## 6. 리스크 (기술설계서 §6 재확인)

- iOS는 백그라운드 진입 시 OS가 카메라 캡처를 강제 중단 — 이번 Native Bridge 작업에는 백그라운드 대응 포함하지 않음(포그라운드 방송만).
- 실제 RTMPS 송출 성공 여부는 스트림키 확보 전까지 End-to-End 검증 불가 — Phase 3(실기기 테스트) 단계에서 재검증 필요.

## 7. 관련 노트

- [[송출앱_기술설계서]] §5(인터페이스 초안), §6(백그라운드 정책)
- 코드: `/Users/linkcampus02/fanbird-broadcast/src/native/IVSBroadcastModule.ts`(JS 인터페이스, 변경 없음 유지), `ios/FanbirdBroadcast/`(신규 Swift 파일 추가 예정)
