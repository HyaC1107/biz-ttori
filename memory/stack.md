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
