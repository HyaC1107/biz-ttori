# stack.md — 기술 스택 및 환경 트러블슈팅 가이드

이 문서는 **Biz-Ttori** 워크스페이스 내에서 진행되는 풀스택, React, React Native 프로젝트들의 주요 기술 스택과 환경 설정, 그리고 자주 발생하는 트러블슈팅 솔루션을 기록합니다.

---

## 🛠️ 표준 기술 스택

| 레이어 | 기술 | 비고 |
|:---|:---|:---|
| **Frontend** | React, TypeScript, Tailwind CSS, Zustand | CSR 및 Next.js 병용 |
| **Mobile** | React Native (Expo / React Native CLI) | 크로스 플랫폼 |
| **Backend** | Node.js (NestJS, Express, FastAPI) | 풀스택 백엔드 |
| **Database** | PostgreSQL, Supabase, Redis | 관계형 및 캐시 |
| **Infra** | AWS, Vercel, Docker | 클라우드 배포 |

---

## ⚠️ 모바일 (React Native) 트러블슈팅 가이드

### 1. iOS 빌드 및 CocoaPods 캐시 이슈
* **증상**: `npx pod-install` 또는 `pod install` 실행 시 의존성 버전 충돌 혹은 빌드 실패.
* **해결책**:
  ```bash
  # iOS 빌드 디렉토리 및 캐시 제거
  rm -rf ios/Build ios/Pods ios/Podfile.lock
  # pod clean install
  cd ios && pod cache clean --all && pod install && cd ..
  ```

### 2. Android 빌드 및 Gradle 캐시 이슈
* **증상**: Android Studio 또는 CLI에서 `npx react-native run-android` 실행 시 Gradle task 에러.
* **해결책**:
  ```bash
  cd android
  ./gradlew clean
  cd ..
  # Gradle daemon이 꼬였을 경우
  ./gradlew --stop
  ```

### 3. Metro Bundler 캐시 꼬임
* **증상**: 코드 변경 사항이 시뮬레이터에 반영되지 않거나, 모듈을 찾을 수 없다는 에러 발생.
* **해결책**: Metro 서버를 캐시를 비우고 다시 시작한다.
  ```bash
  npx react-native start --clear
  # Expo인 경우
  npx expo start -c
  ```

### 4. RN Android 커스텀 네이티브 뷰(카메라 프리뷰 등) 검은 화면 [fanbird-broadcast, 2026-07-06 실증]
* **증상**: `requireNativeComponent`로 만든 커스텀 뷰(`FrameLayout`)에 `addView`한 자식(카메라 프리뷰 등)이 **화면에 안 보이고 검은 배경만** 나옴. 카메라 하드웨어는 정상 동작(logcat에 Qualcomm 카메라 파이프라인 프레임 활발) → 즉 attach는 되는데 **렌더만 안 됨**.
* **원인**: RN(Android)은 커스텀 네이티브 뷰의 자식을 measure/layout 하지 않아 자식이 **0 크기**로 렌더된다. (iOS는 `layoutSubviews`에서 프레임을 갱신해줘서 이 문제가 없음 — Android만 발생)
* **해결책**: 커스텀 뷰에서 `requestLayout`을 오버라이드해 자식을 강제로 재측정·배치한다.
  ```kotlin
  private val measureAndLayout = Runnable {
      measure(
          MeasureSpec.makeMeasureSpec(width, MeasureSpec.EXACTLY),
          MeasureSpec.makeMeasureSpec(height, MeasureSpec.EXACTLY),
      )
      layout(left, top, right, bottom)
  }
  override fun requestLayout() {
      super.requestLayout()
      post(measureAndLayout)
  }
  ```
* **진단 팁**: 검은 화면일 때 `adb logcat -d | grep -iE "camera|ivs"`로 카메라 프레임이 도는지 먼저 확인 → 프레임이 돌면 권한/세션이 아니라 **뷰 레이아웃 문제**로 좁혀진다.

### 5. Android 15+/targetSdk 35+ edge-to-edge에서 키보드가 입력창을 가림 [fanbird-broadcast, 2026-07-06 실증]
* **증상**: 로그인 등 화면에서 키보드가 뜨면 입력창을 가림. `AndroidManifest`에 `windowSoftInputMode="adjustResize"`가 있고 `KeyboardAvoidingView`·`ScrollView`를 다 써도 **화면이 위로 안 밀림**.
* **원인**: Android 15(SDK 35)+부터 **edge-to-edge가 강제**돼(targetSdk 35+) `adjustResize`가 **무시**된다. 앱 창 높이가 키보드만큼 줄지 않아 KAV/ScrollView가 밀어올릴 근거를 못 받는다. (`gradle.properties`의 `edgeToEdgeEnabled=false`여도 OS가 강제)
* **해결책(국소, JS만)**: `Keyboard` 이벤트로 높이를 직접 받아 스크롤 컨테이너에 `paddingBottom`으로 밀어올린다. 전역 `edgeToEdgeEnabled=true`는 다른 화면 레이아웃(상태바 겹침)에 영향이 커서 국소 대응이 안전.
  ```tsx
  const [kbH, setKbH] = useState(0);
  useEffect(() => {
    const s = Keyboard.addListener('keyboardDidShow', e => setKbH(e.endCoordinates.height));
    const h = Keyboard.addListener('keyboardDidHide', () => setKbH(0));
    return () => { s.remove(); h.remove(); };
  }, []);
  // ScrollView contentContainerStyle: [base, Platform.OS==='android' && kbH>0 && { paddingBottom: kbH }]
  ```
* **진단 팁**: `adb exec-out screencap -p > s.png`로 키보드 뜬 상태를 캡처해 **화면이 밀렸는지** 눈으로 확인. 안 밀렸으면 adjustResize가 무시되는 것. `adb shell getprop ro.build.version.sdk`로 기기 SDK, `android/build.gradle`의 targetSdkVersion 확인.

---

## 💻 풀스택 & 데이터베이스 트러블슈팅 가이드

### 1. Node.js 메모리 부족 (OOM)
* **증상**: 빌드 타임이나 테스트 실행 중 `JavaScript heap out of memory`로 프로세스가 죽는 현상.
* **해결책**: `package.json`의 스크립트 실행 시 메모리 제한 값을 조정해 준다.
  ```json
  "build": "NODE_OPTIONS='--max-old-space-size=4096' next build"
  ```

### 2. Prisma Connection Pool 고갈
* **증상**: Serverless 환경(Vercel, AWS Lambda)에서 데이터베이스 연결 수 초과로 `PrismaClientInitializationError` 발생.
* **해결책**: 
  - Connection Pooler를 연결(Supabase Transaction Pooler:6543 등)하고, URL 끝에 `?pgbouncer=true&connection_limit=1`을 추가하여 커넥션을 관리한다.
