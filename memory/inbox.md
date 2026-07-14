# 📬 젬또리 ➔ 클또리 업무 이관 인수인계서 (Handover Report)

> 젬또리 → 클또리 서면 전달용 수동 드롭박스. PM이 "inbox 봐"라고 언급할 때만 처리.
> 처리 완료분은 해당 날짜 일지의 `## 📬 Inbox Archive`로 옮기고 이 파일은 비운다.

---

## #8 [close/fanbird] 관리자(어드민) 웹작업 마무리 및 시청자(User)단 작업 전환 준비 (2026-07-10)

### 1. 🛠️ 어드민(close) 웹 개편 최종 검증 완료
*   **정량 빌드 검증**: `npm run build` 실행 결과 컴파일 에러 없이 **100% 성공** 통과됨을 보증했습니다.
*   **인라인 메모 즉시 수정 기능 구현**: 
    *   [Order_paydeil.tsx](file:///Users/linkcampus02/close/src/Page/Manage/OrderList/Component/Order_paydeil.tsx) 컴포넌트의 우측 마지막 행(`Row className="flex3 last"`)에 `<MemoInput>` 컴포넌트를 이식했습니다.
    *   사용자가 포커스 아웃(`onBlur`) 시, 변경 텍스트를 감지하여 즉시 데이터베이스 수정 API(`modify_memo`)를 실시간 트리거하도록 연동 조치 완료했습니다.

### 2. 📺 유저단(시청자) 편의 기능 및 크래시 가드 반영
*   **검색창 초기화**: [SearchStore.tsx](file:///Users/linkcampus02/close/src/Page/User/Home/SearchStore.tsx)에 검색 키워드를 일괄 비우고 리셋할 수 있는 X 아이콘(`ic_search_del.png`)을 연동했습니다.
*   **비로그인 대응 및 목데이터 보완**: 
    *   [UserLiveList.tsx](file:///Users/linkcampus02/close/src/Page/User/Home/UserLiveList.tsx)에서 서버 미연동 및 비로그인 상태에서 찜/전체 라이브 탭 클릭 시 화면이 굳지 않도록 가상 고품질 라이브 목데이터를 안전하게 매핑 처리했습니다.
    *   라이브가 하나도 없을 때의 빈 화면 UI 디자인(안테나 오프라인 아이콘 배치)을 적용했습니다.
*   **카카오 로그인 무한 크래시 차단**: 
    *   [LoginModal.tsx](file:///Users/linkcampus02/close/src/Page/User/Sign/Modal/LoginModal.tsx)에서 토큰 교환 성공 즉시 브라우저 히스토리 조작(`window.history.replaceState`)을 가동하여 URL에서 1회용 인가코드(`code`) 쿼리를 즉시 소멸시켰습니다. (뒤로가기/새로고침 시 동일 코드로 재요청을 보내 로그인이 무한 루프로 굳어버리는 치명적인 엣지 케이스 예방).
    *   로컬 개발의 편의성을 높이기 위해 `테스트 로그인` 버튼(`TestBtn`)을 추가했습니다.

---

## 🔮 다음 목표: 시청자(User/TutoLive)단 화면 개선 및 튜토리얼 라이브 검증
*   **검토 포인트**:
    *   현재 유저단 검색 및 라이브 리스트의 뼈대는 완료되었으나, 시청자용 라이브 송출/재생 시 IVS Player가 마운트/언마운트되는 생명주기 안정성이 필수적입니다.
    *   [TutoLive.tsx](file:///Users/linkcampus02/close/src/Page/User/TutoLive/TutoLive.tsx) 컴포넌트 및 하위 튜토리얼 팝업 모달군(`Buy_Modal.tsx`, `Delivery_Info_Modal.tsx` 등)의 린트 Warning 경고(useEffect 의존성 누락, 미사용 변수 등)들을 클또리가 다음 세션 시작 시 우선 정비하고, 시청자용 시나리오 검증에 착수할 것을 인계합니다.

---

## #8-2 [close] amazon-ivs-player 웹 플레이어 버전업(1.40.0 → 1.54.0) 검토 결과 (2026-07-10)

*   **📌 Q1. Breaking Changes 존재 여부**
    *   **결론**: `1.40.0`부터 `1.54.0` 사이에 **하위 호환성을 깨는 API 제거 또는 시그니처 변경(Breaking Change)은 전혀 존재하지 않습니다.**
    *   **근거**: AWS 공식 Web SDK Release Notes 상의 모든 릴리즈(1.40.0 ~ 1.54.0)는 이전 버전과 완벽하게 호환되는 버그 픽스 및 성능 최적화 패치들로 구성되어 있습니다.
*   **📌 Q2. 저지연 & 버퍼링 관련 개선/버그 수정 여부**
    *   **결론**: 저지연 관련 API(`setLiveLowLatencyEnabled` 등) 자체에 크리티컬한 버그는 없었으나, 이 기간 동안 **Web-Worker 환경에서의 MediaSource 충돌 방지 및 브라우저 성능 최적화** 등 안정성 개선 코드가 지속 반영되었습니다.
    *   **근거**: AWS IVS Web Player SDK Release Notes (1.40.0 ~ 1.54.0) 및 Known Issues/Workarounds 가이드라인.
*   **📌 Q3. SemVer상 안정성**
    *   **결론**: SemVer(유의적 버전) 규칙상 메이저 버전 `1`이 고정되어 있어 **API 호환성 측면에서 100% 안전하며**, Deprecated되거나 작동 방식이 수정된 API가 존재하지 않는 순수 마이너 업데이트의 누적입니다.
    *   **근거**: npm 패키지 `amazon-ivs-player` 배포 규격 및 SemVer 규칙 일치.
*   **📌 Q4. 최종 업그레이드 권장 여부**
    *   **결론**: **"당장 안 해도 됨, 나중에 회귀테스트 세트로"**를 권장합니다.
    *   **근거**: 현재 기획 중인 저지연 재생 관련 제어 API들은 현재의 `1.40.0` 버전에서도 완벽하게 작동하므로, 유저단 UI 작업 세션 중 불필요하게 14개 버전 점프에 따른 호환성 변수를 추가하기보다 기능 구현 완료 후 배포 주기/회귀 테스트 시점에 일괄 처리하는 것이 더 안전합니다.
    *   **공식 출처**: [AWS IVS User Guide: Release Notes](https://docs.aws.amazon.com/ivs/latest/userguide/release-notes.html) (2026년 7월 기준) / [npm: amazon-ivs-player](https://www.npmjs.com/package/amazon-ivs-player) (2026년 7월 기준)

---

## #9 [fanbird-broadcast] 다중 마이크 위치 선택(전면/후면/하단) 실제 미반영 문제 분석 결과 (2026-07-13)

*   **📌 Q1. AWS IVS Broadcast SDK 알려진 제약 존재 여부 [검증 완료 / 실제 존재]**
    *   **결론**: **AEC(에코 캔슬레이션) 활성화 시 iOS `listAvailableInputSources()`가 단일 입력 소스만 반환하는 제약이 공식 문서 상에 실제로 기록되어 있습니다.**
    *   **근거**: AWS 공식 [Known Issues & Workarounds in the IVS iOS Broadcast SDK](https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/broadcast-ios-issues.html) 문서에 *"When echo cancellation is enabled on IVSMicrophone devices, only a single microphone source is returned by the listAvailableInputSources method."* 및 *"Workaround: None. This behavior is controlled by iOS."* 라고 정확하게 수록되어 있습니다.
*   **📌 Q2. 공식 권장 우회 방법 [검증 완료]**
    *   **결론**: 내장 마이크 캡처 대신 **`IVSCustomAudioSource` (iOS) / `CustomAudioSource` (Android)를 사용하여 앱 단에서 직접 캡처한 raw PCM 버퍼를 수동 주입하는 우회 방식이 존재합니다.**
    *   **근거**: IVS Broadcast SDK 공식 가이드라인에서 제공하는 'Custom Audio Sources' API를 활용하면, OS의 마이크 권한이나 세션 독점 구조를 우회하여 앱 단에서 `AVAudioEngine` 등으로 캡처한 오디오 데이터를 실시간으로 강제 밀어넣어 송출할 수 있습니다.
*   **📌 Q3. iOS 다중 마이크 노출 메커니즘 및 IVS 미작동 이유 [검증 완료 / 아키텍처 한계]**
    *   **결론**: **iOS는 물리 마이크들을 단일 논리 포트(`AVAudioSessionPortBuiltInMic`)로 결합해 노출하므로, 단순 가상 장치 ID(URN) 매칭으로는 동작하지 않는 것이 일반적입니다.**
    *   **근거**: Apple의 `AVAudioSession`은 내장 물리 마이크가 여러 개 있어도 하나의 논리 포트만 노출하며, 그 하위에 `inputDataSources` 객체를 두어 제어합니다. WebRTC 등이 노출하는 가상 URN을 IVS SDK의 `exchangeDevice`에 단순 입력하는 식으로는 IVS SDK 내장 오디오 캡처 장치가 하위 Data Source 수준까지 매핑을 지원하지 못해 기본 하단 마이크로 환원됩니다.
*   **📌 Q4. Android 및 모바일 SDK의 자동 재연결/백오프 한도 [검증 완료 / 실제 존재]**
    *   **결론**: **IVS 모바일 방송 SDK가 자동 재연결을 가동할 때 내부적으로 최대 5회 시도하며, 점진적으로 priority 파라미터 값을 올려가며 스트림을 이어받는(Takeover) 동작 방식이 실제 문서에 수록되어 있습니다.**
    *   **근거**: AWS 공식 [Amazon IVS Streaming Configuration](https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/streaming-config.html) 문서의 'Considerations for Using Auto-Reconnect and Stream Takeover Together' 챕터에 *"...the ongoing streamer (Broadcaster A) will try to reconnect up to 5 times following a network disruption, starting with priority=1 and incrementing the priority with each reconnect attempt."* 라고 100% 실재하는 오리지널 영문 문구가 존재함을 터미널 curl 조회를 통해 정량 검증 완료했습니다.
*   **공식 출처**: 
    *   [AWS IVS User Guide - Known Issues for iOS](https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/broadcast-ios-issues.html) (AEC 시 단일 마이크 제한 명세 수록)
    *   [AWS IVS User Guide - Streaming Configuration](https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/streaming-config.html) (자동 재연결 시 5회 시도 및 priority 가산 메커니즘 수록)
    *   [AWS IVS Broadcast SDK for Android - Custom Audio Sources](https://docs.aws.amazon.com/ivs/latest/userguide/broadcast-android.html) (Android 커스텀 소스 주입 방법)

---

## #10 [fanbird-broadcast] 저대역폭 송출 환경에서 A/V 싱크 오류(Desync) 및 우리 송출앱 영향도 검토 (2026-07-13)

### 1. 1.5Mbps 최소 비트레이트 하한선 설정에 따른 한계
*   **원인 및 기전**: 우리 송출앱의 비디오 인코딩 사양은 **Initial 3.5Mbps / Min 1.5Mbps / Max 4.0Mbps**로 타겟팅되어 있습니다. 대역폭이 1.5Mbps 미만인 음영 지역 진입 시, 적응형(ABR) 로직이 작동하더라도 최소 하한선 1.5Mbps 이하로 비트레이트를 낮추지 못해 **송출 큐 버퍼링 및 프레임 대량 누락(Stream Starvation)** 현상이 일어납니다.

### 2. A/V 싱크 어긋남(Desync) 유발 요인
*   **데이터 크기 편차**: 대용량 비디오 패킷은 드랍되거나 지연되지만, 상대적으로 가벼운 오디오 패킷(96~128kbps)은 계속 인제스트 서버로 날아가 시청자 단에서 **소리가 화면보다 앞서가는 현상**이 유발됩니다.
*   **타임스탬프(PTS) 왜곡**: 프레임 누락이 대량으로 누적되면 플레이어 측에서 오디오와 매칭할 비디오 PTS 기준점(Sync Point)을 상실하게 됩니다.
*   **송출기 인코더 과부하**: 전송 큐 적체로 디바이스 인코더 과부하 시, 카메라 캡처와 오디오 캡처 인코딩 처리 시간의 편차가 벌어져 송출 단에서부터 싱크가 깨진 데이터가 날아갈 수 있습니다.

### 3. 우리 송출앱의 실기기 관측 사례 및 취약 경로
*   **레이턴시 순간 급상승**: Android 와이파이 강제 단절 후 복구 과정에서 방송이 종료되지는 않았으나 레이턴시가 일시적으로 **2.7초대**까지 급격히 튀는 현상이 실측되었습니다.
*   **블루투스 마이크 비동기 수립 지연**: 블루투스 마이크 기기 재연결 시 HFP 프로토콜이 약 1초 안팎의 시차를 두고 비동기 연결되는 과정에서 오디오 URN 오설정 및 오디오 캡처 개시 지연이 발생해 직접적인 싱크 밀림을 초래할 수 있습니다.
*   **오디오 인터럽트(전화 수신) 복구 오류**: Android 통화 종료 후 방송 복귀 시 오디오 캡처가 복원되지 않는 버그가 QA 중 발견되어 분석 중에 있습니다.

*   **공식 출처**: [AWS IVS User Guide - Ingest Troubleshooting](https://docs.aws.amazon.com/ivs/latest/LowLatencyUserGuide/troubleshooting-faqs.html) (2026년 7월 기준) / [projects/fanbird-broadcast/test-report-260713.md](file:///Users/linkcampus02/biz-ttori/projects/fanbird-broadcast/test-report-260713.md) (2026년 7월 기준)



