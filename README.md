# Career Navigation AI

비전공자와 주니어 구직자를 위한 IT 취업 로드맵 앱입니다. Expo React Native 앱에서 목표 직무와 보유 기술을 입력하면 FastAPI 백엔드가 분석 결과와 12주 로드맵을 생성하고, 사용자는 주차별 task를 체크하며 진행률을 관리할 수 있습니다.

## 1. 프로젝트 소개

Career Navigation AI는 IT 직무 준비를 "분석 → 로드맵 생성 → 12주 실행 관리" 흐름으로 연결하는 MVP입니다.

- 프론트엔드: Expo React Native 모바일 앱
- 백엔드: FastAPI + SQLAlchemy
- 데이터베이스: PostgreSQL + pgvector
- 현재 인증 정책: 회원가입/로그인 후에만 개인 기능 사용 가능
- 사용자 정책: 로그인 계정별 1개 활성 로드맵과 프로젝트 평가 관리

## 2. MVP 핵심 기능

- 사용자 프로필 생성
- 목표 직무 기반 커리어 분석
- RandomForest mock 예측 결과 반환
- RAG mock 문서 저장/검색 구조
- 회원별 활성 로드맵 1개 관리
- 12주 로드맵 자동 생성
- 주차별 task 완료 체크
- 완료 task 비율 기반 진행률 계산
- Home / Result / Roadmap / MyInfo 화면에서 최근 결과와 로드맵 확인
- 채용공고 데이터 수집 파이프라인 기본 구조

## 3. 지원 직무 7개

현재 MVP에서 지원하는 IT 직무는 아래 7개입니다.

- Backend Developer
- Frontend Developer
- AI Backend Developer
- Data Analyst
- Data Engineer
- Data Scientist
- Builder

한국어 입력 매핑도 일부 지원합니다.

- 백엔드 개발자 → Backend Developer
- 프론트엔드 개발자 → Frontend Developer
- AI 백엔드 개발자 → AI Backend Developer
- 데이터 분석가 → Data Analyst
- 데이터 엔지니어 → Data Engineer
- 데이터 사이언티스트 → Data Scientist
- 빌더 / 서비스 빌더 / AI 빌더 / 노코드 빌더 / MVP 빌더 → Builder

## 4. 앱 화면 흐름

1. Splash 화면
   - 앱 실행 시 logo.png를 1초 동안 표시합니다.

2. Home
   - 앱 첫 화면입니다.
   - 활성 로드맵이 있으면 목표 직무와 진행률을 보여줍니다.
   - 로드맵이 없으면 새 분석 시작 버튼을 보여줍니다.

3. 새로 분석하기
   - 목표 직무, 관심 기술, 경험 수준, 보유 기술, 목표 기간을 입력합니다.
   - 기존 분석 API 흐름을 유지합니다.

4. Result
   - `12주 취업 준비 달성률`과 추천 학습/프로젝트 설계를 보여줍니다.
   - 달성률은 취업 성공 확률이 아니라 기술, 프로젝트, 서류/면접 준비의 증명 완료 비율입니다.

5. Roadmap
   - 12주 로드맵과 주차별 task를 표시합니다.
   - task 체크 시 백엔드에 저장되고 진행률이 즉시 업데이트됩니다.

6. 과제검증
   - 프로젝트 결과물 제출, 무료 규칙 평가, 요청형 AI 엄격 리뷰를 수행합니다.

7. MyInfo
   - 로그인 계정 정보와 해당 계정의 저장 로드맵 진행률을 표시합니다.

## 5. 기술 스택

### Frontend

- Expo
- React Native
- React Navigation Bottom Tabs
- Axios
- AsyncStorage
- lucide-react-native
- react-native-safe-area-context

### Backend

- FastAPI
- SQLAlchemy
- PostgreSQL
- psycopg2
- pgvector
- scikit-learn
- Pydantic

### Infra / Data

- Docker Compose
- PostgreSQL pgvector image
- mock RAG embedding
- mock RandomForest prediction
- 공공데이터/WorkNet/HRD 데이터 수집 모듈 구조

## 6. API 목록

### User

- `POST /api/v1/users/profile`
  - 사용자 프로필을 생성하고 skills / user_skills 관계를 저장합니다.

### Job Postings

- `POST /api/v1/jobs`
  - 채용공고와 요구 기술을 저장합니다.

### Trends

- `POST /api/v1/trends`
  - 기술 트렌드 점수를 저장합니다.
- `GET /api/v1/trends/keywords`
  - 저장된 기술 트렌드 목록을 조회합니다.

### Model

- `POST /api/v1/model/predict`
  - mock RandomForest 기반 수요 확률을 반환합니다.

### RAG

- `POST /api/v1/rag/documents`
  - 문서와 mock embedding을 저장합니다.
- `POST /api/v1/rag/query`
  - pgvector 기반 유사 문서를 검색합니다.

### Agent

- `POST /api/v1/agent/career-path`
  - 커리어 분석 결과를 생성합니다.
  - 응답에 `roadmap_id`, `progress_percent`, `roadmap_12_weeks`를 포함합니다.

### Roadmaps

- `POST /api/v1/roadmaps`
  - 로그인한 사용자의 활성 로드맵을 생성합니다.
  - 새 로드맵 생성 시 기존 활성 로드맵은 비활성화됩니다.
- `GET /api/v1/roadmaps/me`
  - 현재 활성 로드맵을 조회합니다.
- `PATCH /api/v1/roadmaps/tasks/{task_id}/toggle`
  - task 완료 상태를 토글하고 진행률을 다시 계산합니다.
- `GET /api/v1/roadmaps/me/progress`
  - 진행률, 완료 task 수, 전체 task 수를 조회합니다.

### Project Evidence Review

- `POST /api/v1/projects/submissions`
  - 프로젝트 결과물 설명과 README 발췌를 무료 규칙 평가하고 `프로젝트 증명도`에 반영합니다.
  - 이 단계는 제출된 문서 근거의 충실도를 평가하며, 원격 코드 실행이나 저장소 진위 확인을 대신하지 않습니다.
- `POST /api/v1/projects/submissions/{submission_id}/ai-review`
  - 사용자가 명시적으로 요청했을 때만 OpenAI API로 엄격한 텍스트 리뷰를 실행합니다.
  - AI 리뷰는 점수를 올리지 않으며, 확인된 근거와 수정할 항목만 반환합니다.

### Data Collection

- `POST /api/v1/data/jobs/collect`
  - 채용공고 데이터를 수집하고 raw / processed 파일로 저장합니다.
- `GET /api/v1/data/jobs`
  - 정제된 채용공고 데이터를 조회합니다.
- `POST /api/v1/data-collection/jobs`
  - 기존 호환용 데이터 수집 endpoint입니다.

## 7. Docker 실행 방법

프로젝트 루트에서 실행합니다.

```powershell
docker compose down
docker compose up -d --build
docker compose logs -f backend
```

백엔드 Swagger:

```text
http://127.0.0.1:8000/docs
```

### External Jobs ATS Collector

- This collector does not scrape LinkedIn, Indeed, or other sites where scraping may be restricted.
- It only collects public ATS job postings that are available without API keys.
- Supported public APIs are Greenhouse Job Board API, Lever Postings API, and Ashby Public Job Posting API.
- Company slugs or ATS providers can change, so collection for an individual company may fail.
- Failed companies are recorded in the `failed_companies` response field while the remaining companies continue.
- Collected posting text is intended for internal analysis and skill keyword extraction. Public API list responses expose company, title, location, source URL, extracted skills, and a short summary instead of the full original posting body.

Swagger test order:

1. Start the server.
2. Call `POST /api/v1/external-jobs/collect`.
3. Call `GET /api/v1/external-jobs`.
4. Call `GET /api/v1/external-jobs/skills/summary`.

헬스 체크:

```text
http://127.0.0.1:8000/health
```

Docker Compose 구성:

- `backend`: FastAPI 서버, 8000 포트
- `db`: PostgreSQL + pgvector, 5432 포트

## 8. Frontend 실행 방법

프론트엔드 폴더에서 실행합니다.

```powershell
cd frontend
npm install
npm start -- --clear
```

Expo Go로 실제 휴대폰에서 테스트할 경우 `EXPO_PUBLIC_API_BASE_URL`은 `127.0.0.1`이 아니라 PC의 IPv4 주소를 사용해야 합니다.

예:

```env
EXPO_PUBLIC_API_BASE_URL=http://192.168.35.167:8000
```
HRD/HRDK OpenAPI URL notes:

- `HRDK_*_URL` must be the actual request URL / End Point from the public data portal usage guide, not a data.go.kr detail page.
- Wrong example: `https://www.data.go.kr/data/.../openapi.do`
- Correct example: `http://openapi.q-net.or.kr/api/service/rest/InquiryQualInfo/getList`
- If the response `Content-Type` is `text/html`, the configured URL is likely a web page, not an API endpoint.
- `save_format=json` controls only the local raw/processed file format. The external API response can still be XML.

For HRDK national technical qualification item collection, configure:

```env
PUBLIC_DATA_API_KEY=공공데이터포털_서비스키
HRDK_CERT_ITEMS_URL=http://openapi.q-net.or.kr/api/service/rest/InquiryQualInfo/getList
```

`seriesCd` is required by the Q-Net qualification item API:

- `01`: 기술사
- `02`: 기능장
- `03`: 기사
- `04`: 기능사

Swagger test example:

```text
POST /api/v1/data/jobs/collect?source=hrd&save_format=json&save_to_rag=true&seriesCd=03&pageNo=1&numOfRows=10
```

Direct browser test example:

```text
http://openapi.q-net.or.kr/api/service/rest/InquiryQualInfo/getList?seriesCd=03&ServiceKey=본인서비스키
```

Check saved RAG documents:

```sql
SELECT COUNT(*)
FROM documents
WHERE source = 'hrdk';

SELECT id, source, metadata, created_at
FROM documents
WHERE source = 'hrdk'
ORDER BY created_at DESC
LIMIT 10;
```

프론트엔드 Expo 환경변수는 `frontend/.env`에도 둘 수 있습니다.

```env
EXPO_PUBLIC_API_BASE_URL=http://192.168.35.167:8000
```

환경변수를 바꾼 뒤에는 Expo 캐시를 비우고 재시작합니다.

```powershell
cd frontend
npm start -- --clear
```

주의:

- API 키는 코드에 하드코딩하지 않습니다.
- AI 프로젝트 리뷰는 버튼을 누를 때만 실행되며, `OPENAI_REVIEW_MONTHLY_BUDGET_USD` 기본값 `$1.00` 범위에서 이 기능의 예상 사용료를 제한합니다.
- 기본 리뷰 모델은 `gpt-5.4-mini`, 응답 한도는 `OPENAI_REVIEW_MAX_OUTPUT_TOKENS=900`입니다.
- Docker 내부 DB 주소는 `db:5432`를 사용합니다.
- 로컬에서 직접 uvicorn을 실행할 경우 DB 주소를 환경에 맞게 조정해야 합니다.

## 10. 현재 로그인 정책

현재 로그인 기능이 활성화되어 있습니다.

```js
// frontend/src/config.js
export const AUTH_ENABLED = true;
```

- 회원가입 또는 로그인 후에만 개인 로드맵 화면에 진입합니다.
- 프로필, 분석 결과, 로드맵, 재진단, 프로젝트 평가는 로그인한 사용자 ID 기준으로 저장됩니다.
- 로그아웃하거나 다른 계정으로 로그인하면 앱의 이전 분석/로드맵 표시 상태가 초기화됩니다.
- 사용자 전용 API는 토큰이 없으면 `401`을 반환합니다.

## 11. 향후 확장 계획

- 토큰 갱신과 비밀번호 재설정 흐름
- 회원별 로드맵 저장 목록 제공
- 로드맵 수정/삭제 기능
- 주차별 메모, 학습 링크, 증빙 자료 업로드
- 실제 RandomForest 학습 데이터 연결
- OpenAI embedding 또는 실제 embedding 모델 연동
- RAG 검색 품질 개선
- 채용공고 데이터 수집 자동화
- WorkNet / HRD / 공공데이터 API 실연동 강화
- 직무별 로드맵 템플릿 고도화
- Builder / 데이터 / 개발 직무별 포트폴리오 예시 추천
- 푸시 알림 및 주차별 리마인더
- Expo 앱 배포 준비
