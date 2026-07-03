# 📤 클또리 → 젬또리 아웃박스 (outbox)

> 클또리가 젬또리(Antigravity)에게 넘길 요청/수정사항을 쌓아두는 **수동 드롭박스**.
> ⚠️ 이 파일에 쓰는 것 자체는 아무것도 자동 실행하지 않는다. PM이 손으로 `agy`를 돌릴 때
>   "outbox.md 읽고 처리해"라고 짚어주면 젬또리가 처리한다(T1 사람운전 유지, 자동 트리거·루프 금지).
> 처리 완료분은 해당 날짜 일지 아카이브로 옮기고 여기선 지운다.

---

## #1 — 송출앱_기술설계서.md §5.1 팩트 수정 (2026-07-02, from 클또리)

**대상 파일:** `projects/close/Docs/송출앱_기술설계서.md` §5.1(SDK 확정 사항)
**배경:** 실제 Native Bridge 구현하며 클또리가 실측(iOS 헤더 / Android AAR `javap`, context7 AWS 공식문서)으로 확인한 결과, 설계서 초안과 다른 점 2건 발견. 젬또리가 문서에 반영해줘.

1. **Android gradle 의존성 표기 수정**
   - 현재: `implementation 'com.amazonaws:ivs-broadcast:1.43.0:stages@aar'`
   - 수정: `implementation 'com.amazonaws:ivs-broadcast:1.43.0'` (`:stages@aar` 분류자 제거)
   - 근거: `:stages` 분류자는 **Real-Time/Stages(WebRTC)용**. 우리는 **Low-Latency RTMPS 송출**이므로 순수 아티팩트를 써야 함. (Expo `expo-realtime-ivs-broadcast`가 Stages용이라 기각한 것과 동일한 함정)

2. **iOS 배포 방식 표기 수정**
   - 현재 뉘앙스: "SPM 지원(CocoaPods 배포 중단)"
   - 수정: iOS는 **CocoaPods 배포가 1.39.0부터 완전 중단**(CocoaPods trunk엔 1.9.1까지만 잔존). 최신 **1.43.0**은 CDN xcframework(`https://broadcast.live-video.net/1.43.0/AmazonIVSBroadcast.xcframework.zip`) 또는 SPM으로만 배포. 우리 구현은 **xcframework를 로컬 podspec으로 vendoring**(`ios/LocalPods/`)해서 pod install에 태우는 방식 채택.

**[검색 원칙] (교차검증 시)**
1. 공식 문서(AWS IVS docs, Maven Central, CocoaPods trunk) 우선
2. 버전은 날짜/릴리스 명시 (Android maven 최신 안정판 1.43.0, 1.45.0-rc.1은 RC라 제외 / iOS xcframework 1.43.0)
3. 상충 시 최신 공식 출처 우선, 근거 URL 첨부

> 이 항목은 클또리가 실측 확인 완료 — 젬또리는 재조사보다 **문서 반영**에 집중하면 됨(원하면 위 근거만 교차확인).

---

## #2 — [의견 요청] 송출자용 Tap-to-Focus / 노출 / BT마이크 제어 실현성 (2026-07-03, from 클또리)

**주제:** 모바일 RN 송출 앱에 ①화면 터치 초점(Tap-to-Focus)·노출점 ②블루투스 마이크 스위칭/오디오 세션 튜닝 도입 검토 중. PM이 젬또리 의견도 듣고 싶어함.

**전제 확인(클또리 실측 완료):**
- **기존 팬버드 웹엔 포커싱 기능 없음** — 웹은 `getUserMedia`로 웹캠 스트림만 받아 IVS Web SDK에 주입(`addVideoInputDevice`). 초점 제어 코드 전무. → 이건 **모바일 신규 기능**(웹 이식 아님).
- **IVS Broadcast SDK 실측(iOS 헤더 / Android AAR javap):**
  - iOS: `IVSImageDevice`가 **zoom(`setVideoZoomFactor`)·torch만** 노출. **focus/exposure/AVCaptureDevice 접근 API 없음.** 단 iOS `AVCaptureDevice`는 물리카메라당 공유 싱글턴이라, AVFoundation으로 같은 카메라를 직접 얻어 `lockForConfiguration`→`focusPointOfInterest`/`exposurePointOfInterest` 병렬 제어는 이론상 가능(IVS와 동시 제어 리스크).
  - Android: `CameraSource.Options`가 **zoom·torch만** 노출. **AF/AE regions 제어 없음.** IVS가 Camera2 `CameraDevice`를 **단독(exclusive) 점유**해 우리가 두 번째 핸들 못 얻음 → Tap-to-Focus 하려면 카메라 파이프라인을 우리가 통째로 떠안는 커스텀 이미지소스(`createImageInputSource`) 재설계 필요(대공사).
  - 오디오: iOS `IVSMicrophone`+`underlyingInputSourceChangedForMicrophone` 델리게이트로 BT 연결/해제 감지·전환은 IVS가 자체 처리. 세션은 IVS 소유.

**젬또리에게 묻고 싶은 것:**
1. **iOS 공유 AVCaptureDevice 병렬 제어**의 실사용 사례/리스크 — IVS가 세션을 소유한 상태에서 외부가 focus/exposure를 lock·설정할 때 config-lock 경합/충돌 보고 있는지(공식/커뮤니티 근거).
2. **Android에서 IVS Broadcast SDK + Tap-to-Focus** 구현 선례가 있는지 — 커스텀 이미지소스로 Camera2를 직접 몰고 AF/AE 제어 후 IVS 주입한 사례/공수/함정.
3. **IVS 로드맵**에 focus/exposure 제어 API 추가 계획 — 공식 docs/GitHub 이슈/릴리스노트 기준.
4. 대안 아키텍처(우리가 카메라 통째 관리 → IVS는 인코딩/송출만)의 실무 난이도·리스크·유지보수 관점 의견.

**[검색 원칙]**
1. 공식 문서(AWS IVS docs, Apple AVFoundation, Android Camera2) + IVS 공식 GitHub 샘플 우선
2. 날짜/버전 명시(IVS SDK 1.43.0 기준, 2026-07)
3. 커뮤니티 글은 공식 문서로 교차검증, 근거 URL·날짜 첨부
4. 상충 정보는 최신 공식 우선 + 양쪽 명시
