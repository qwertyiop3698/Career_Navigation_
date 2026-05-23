# 취업 나침반 Frontend

Expo React Native 기반 모바일 앱입니다. 전체 프로젝트 소개, API, Docker 실행 방법은 루트 `README.md`를 참고하세요.

## 화면 흐름

- Splash: 로고를 1초 표시
- Home: 활성 로드맵과 진행률 요약
- 새로 분석하기: 목표 직무와 보유 기술 입력
- Result: 분석 결과와 로드맵 요약
- Roadmap: 12주 task 체크 및 진행률 업데이트
- MyInfo: 현재 로그인 정책 안내

## 실행 방법

```powershell
cd frontend
npm install
npm start -- --clear
```

## 환경변수

`frontend/.env` 또는 프로젝트 루트 `.env`에 백엔드 API 주소를 설정합니다.

```env
EXPO_PUBLIC_API_BASE_URL=http://192.168.35.167:8000
```

실제 휴대폰의 Expo Go에서 테스트할 때는 `127.0.0.1` 대신 PC의 IPv4 주소를 사용하세요.

## 현재 로그인 정책

현재는 로그인 기능을 스킵합니다.

```js
export const AUTH_ENABLED = false;
```

`LoginScreen`, `SignupScreen`, `AuthContext`는 보존되어 있으며, 나중에 `AUTH_ENABLED=true`로 전환해 로그인 흐름을 다시 연결할 수 있습니다.
