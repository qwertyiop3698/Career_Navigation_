# Career Navigation AI

비전공자와 주니어 구직자가 목표 IT 직무에 지원할 수 있도록, 현재 역량 진단부터 12주 실행 로드맵, 프로젝트 증명, 채용공고 근거 확인까지 연결하는 모바일 앱 프로젝트입니다.

이 문서는 **2026-05-27 기준 현재 구현 상태와 데이터 현황**을 정리합니다.

## 1. 서비스 목표

서비스의 핵심 목표는 단순히 기술 목록을 추천하는 것이 아니라, 사용자가 12주 뒤 실제 지원에 사용할 수 있는 근거를 완성하도록 돕는 것입니다.

현재 제품 흐름은 다음과 같습니다.

```text
회원가입/로그인
-> 목표 직무 및 관심 소재 선택
-> 현재 보유 기술을 수행 수준 체크리스트로 입력
-> 채용공고 근거 기반 부족 역량과 프로젝트 추천
-> 12주 로드맵 실행 및 재진단
-> 프로젝트 결과물 제출과 평가
-> 지원 준비 근거 누적
```

앱에서 표시하는 `12주 취업 준비 달성률`은 취업 성공 확률이 아닙니다. 다음 준비 영역에서 증명 가능한 결과물을 완성한 정도입니다.

| 영역 | 최대 점수 | 의미 |
|---|---:|---|
| 기술 수행 체크리스트 | 60 | 목표 직무 핵심 기술을 실제로 수행할 수 있는 수준 |
| 프로젝트 증명도 | 25 | 제출한 프로젝트의 구현, 측정, 문서화 근거 |
| 지원 서류/면접 준비 | 15 | 로드맵에서 완료한 지원 행동 |
| 합계 | 100 | 지원 준비 근거 완성도 |

## 2. 현재 구현 상태

| 기능 | 상태 | 설명 |
|---|---|---|
| 회원가입/로그인 | 완료 | Bearer token 기반, 회원별 데이터 분리 |
| 사용자 GitHub 주소 저장 | 완료 | 내정보에서 저장 후 표시 모드, `수정하기` 지원 |
| 목표 직무/관심 소재 입력 | 완료 | 직무는 7개, 소재는 프로젝트 주제 맥락에 사용 |
| 기술 수준 체크리스트 | 완료 | 기술별 0~5 수준 입력, 최대 가중치 0.60 |
| 채용공고 근거 기반 역량 진단 | 완료 | `JobRoleSkillEvidence` 테이블 사용 |
| 12주 로드맵 | 완료 | 6주 사이클 2개, 주차별 task 완료 관리 |
| 재진단 | 완료 | 6주차/12주차 체크포인트에서 계획 업데이트 |
| 추천 프로젝트 블루프린트 | 완료 | 직무별 구현 기술, 평가 기준, 산출물 제시 |
| 과제검증 탭 | 완료 | 결과물 입력, 무료 규칙 평가, 선택형 AI 리뷰 |
| Data Scientist 자격증 일정 BETA | 완료 | 사이드바 전용 화면, SQLD/ADsP 4주 계획 추가 |
| 해외 채용공고 자동 수집 | 완료 | 공개 ATS 수집, 기본 주기 하루 1회 |
| 분석용 CSV 및 직무/스킬 집계 | 완료 | 7개 직무 필터, 결측 스킬 보완 결과 보유 |
| RAG 문서 저장 및 임베딩 | 부분 완료 | 문서/벡터 저장은 완료, 현재 추천 엔진에는 미연결 |
| 과거 시장 데이터 | 부분 완료 | Adzuna 월별 평균 연봉 저장, 기술 수요 예측 근거로는 제한적 |
| 협업 필터링 | 미구현 | 사용자 행동 데이터가 축적된 이후 검토 예정 |

## 3. 지원 직무와 추천 원칙

### 지원 직무 7개

- `Backend Developer`
- `Frontend Developer`
- `AI Backend Developer`
- `Data Analyst`
- `Data Engineer`
- `Data Scientist`
- `Builder`

### 추천 원칙

추천 프로젝트에서 **직무와 채용공고 근거가 기술 선택을 결정**하고, **관심 소재는 흥미를 유지할 프로젝트 문맥으로만 반영**됩니다.

예를 들어 `Data Scientist` 사용자는 관심 소재가 스포츠든 커머스든 다음과 같은 역량 증명 구조를 추천받습니다.

- 분류 프로젝트: `Logistic Regression` 베이스라인, `RandomForest Classifier` 비교, 변수 중요도 또는 SHAP 분석
- 회귀 프로젝트: 다중선형 회귀 베이스라인, `RandomForest Regressor` 비교, 교차검증과 오차 개선

관심 소재가 `스포츠`이면 선수 부상 위험이나 경기 성과 데이터를 예시로 사용하고, `커머스`이면 고객 이탈이나 구매 금액 데이터를 예시로 사용합니다. 모델 선정 자체가 관심 소재에 의해 바뀌지는 않습니다.

### 스킬 우선순위 계산

현재 로드맵은 채용공고에서 확인된 기술과 사용자의 체크리스트 수준을 함께 사용합니다.

```text
보완 우선순위 = 시장 근거 점수 x (5 - 현재 수준) / 5
```

시장 근거는 분석용 공고 데이터에서 다음 가중치를 적용해 집계합니다.

| 스킬 근거 | 가중치 |
|---|---:|
| 본문 키워드로 직접 추출 | 1.0 |
| 모델 예측 점수 0.65 이상 | 0.7 |
| 모델 예측 점수 0.55 이상 | 0.4 |
| 모델 예측 점수 0.55 미만 | 제외 |

## 4. 모바일 앱 화면

### 로그인 / 회원 관리

- 이메일, 닉네임, 비밀번호로 회원가입 및 로그인
- 토큰이 없는 상태에서는 개인 로드맵, 프로젝트 평가 API 접근 불가
- 다른 계정으로 로그인하면 이전 계정의 앱 표시 상태 초기화

### 홈

홈은 반복 사용을 위한 요약 대시보드입니다.

- 목표 직무와 `12주 취업 준비 달성률`
- 기술 / 프로젝트 / 지원 준비 점수 구성
- 지금 집중할 보완 기술 최대 2개
- 다음 할 일
- 로드맵, 과제 검증, 상세 결과, 재분석 빠른 이동

### 새로 분석하기

- 목표 직무 선택
- 관심 소재 선택 또는 직접 입력
- 직무별 주요 기술 수행 수준 체크리스트 입력
- 분석 완료 후 홈 대시보드로 이동

### 결과

결과 탭은 긴 요약 화면이 아니라 상세 근거 확인 화면입니다.

- 채용공고 기반 기술 근거
- 현재 역량 진단
- 보완 우선순위
- 직무 근거 기반 추천 프로젝트
- 프로젝트의 추천 근거, 관심 소재 적용 예시, 구현 기술 및 모델, 평가 기준, 산출물, 검증 체크리스트

### 로드맵

- 12주 주차별 실행 task 확인
- 완료 체크에 따라 진행률 저장
- 6주차와 12주차 재진단으로 이후 계획 반영
- 선택한 자격증 준비 task 포함 가능

### 과제검증

- 추천 프로젝트별 결과물 제출
- 내정보에 저장한 GitHub 주소를 제출 양식 기본값으로 자동 입력
- 문제 정의, 데이터/목표 변수, 측정 결과, 개선 계획 필수 입력 검증
- 무료 규칙 기반 평가 수행
- 사용자가 별도로 누른 경우에만 OpenAI 기반 엄격 리뷰 수행

무료 규칙 평가는 제출한 텍스트와 README 근거를 평가합니다. 저장소 코드를 실행하거나 GitHub의 사실 여부를 자동 검증하는 기능은 아닙니다.

### 내정보

- 닉네임, 이메일 표시
- GitHub 주소 저장
- GitHub 주소가 저장된 후에는 입력칸 대신 주소와 `수정하기`, `열기` 표시
- 현재 활성 로드맵과 진행률 확인

### 사이드바 / 자격증 일정 BETA

- 상단 메뉴 버튼에서 사이드바 열기
- 홈, 분석 입력, 분석 결과, 12주 캘린더, 과제 검증, 내정보 이동
- `자격증 일정 BETA` 전용 화면 제공

현재 자격증 BETA는 `Data Scientist` 로드맵만 대상으로 합니다.

| 자격증 | 제공 기능 |
|---|---|
| `ADsP` | 시험 일정 확인, 권장 시작일 표시, 4주 준비 task 추가 |
| `SQLD` | 시험 일정 확인, 권장 시작일 표시, 4주 준비 task 추가 |

시험 일정은 한국데이터산업진흥원 공식 일정 기준으로 입력되어 있습니다.

- 공식 일정: <https://www.dataq.or.kr/www/accept/schedule.do>
- 자격증은 현재 달성률 점수에 반영하지 않는 선택 항목입니다.

## 5. 데이터 파이프라인 현황

### 해외 채용공고 수집

해외 채용공고는 접근 가능한 공개 ATS API만 사용합니다.

- Greenhouse Job Board API
- Lever Postings API
- Ashby Public Job Posting API

LinkedIn, Indeed 등 스크래핑 제한 가능성이 있는 사이트를 직접 수집하지 않습니다.

백엔드가 시작되면 스케줄러가 실행되며 기본 설정은 다음과 같습니다.

```env
EXTERNAL_JOBS_AUTO_COLLECT_ENABLED=true
EXTERNAL_JOBS_INITIAL_DELAY_SECONDS=60
EXTERNAL_JOBS_INTERVAL_SECONDS=86400
```

즉, 기본적으로 서버 시작 60초 후 한 번 수집하고 이후 하루에 한 번 수집합니다.

### 현재 DB 데이터 스냅샷

2026-05-27 조회 기준입니다.

| 데이터 | 건수 |
|---|---:|
| `external_job_postings` 해외 채용공고 | 12,468 |
| 해외 채용공고 회사 수 | 83 |
| `job_role_skill_evidence` 직무-스킬 근거 행 | 178 |
| `job_role_market_history` 과거 시장 데이터 행 | 84 |
| `documents` RAG 문서 | 1,929 |
| `embeddings` 벡터 | 1,929 |

### 분석용 CSV

원본 DB는 자동 수집용으로 유지하고, 분석은 별도 CSV와 근거 테이블로 진행합니다.

| 파일 | 상태 |
|---|---|
| `backend/data/exports/external_job_postings.csv` | 원본 내보내기 스냅샷, 12,148행 |
| `backend/data/exports/external_job_postings_role_analysis_ml_skills_v2.csv` | 7개 직무 분석용 정제 데이터, 1,299행 |

정제 데이터의 직무별 행 수:

| 직무 | 행 수 |
|---|---:|
| AI Backend Developer | 400 |
| Backend Developer | 215 |
| Builder | 252 |
| Data Analyst | 52 |
| Data Engineer | 106 |
| Data Scientist | 219 |
| Frontend Developer | 55 |

- `final_skills` 결측 행: `0`
- 목표는 직무별 최대 400개였으나 현재 공고 분포에 따라 직무별 수량 차이가 남아 있습니다.
- 특정 회사 쏠림을 낮추기 위해 직무별 회사당 선택 상한을 둔 균형 추출 로직이 있습니다.

### 분석 스크립트

| 스크립트 | 목적 |
|---|---|
| `backend/scripts/export_external_job_postings_csv.py` | DB 공고를 CSV로 내보내기 |
| `backend/scripts/export_role_analysis_v2_csv.py` | 7개 직무 엄격 필터링 및 회사 균형 추출 |
| `backend/scripts/predict_missing_skills.py` | TF-IDF + Logistic Regression으로 스킬 결측 후보 예측 |
| `backend/scripts/rebuild_job_role_skill_evidence.py` | 현재 추천 엔진이 사용하는 직무-스킬 근거 테이블 재구축 |
| `backend/scripts/export_job_role_skill_trends.py` | 직무별 스킬 빈도 CSV 출력 |
| `backend/scripts/index_rag_documents.py` | 공고/트렌드 데이터를 RAG 문서로 인덱싱 |
| `backend/scripts/rebuild_embeddings.py` | 문서 임베딩 재생성 및 비용 상한 적용 |
| `backend/scripts/collect_adzuna_market_history.py` | Adzuna 과거 시장 데이터 수집 |

## 6. RAG 및 임베딩 상태

### 구현된 구조

RAG 저장 구조는 다음과 같습니다.

```text
documents
  - content
  - source
  - metadata

embeddings
  - document_id
  - embedding vector(1536)
```

`POST /api/v1/rag/documents`는 문서를 저장하면서 임베딩을 생성하고, `POST /api/v1/rag/query`는 질문 임베딩과 `pgvector` 유사도 검색으로 가까운 문서를 반환합니다.

### 현재 저장된 임베딩 문서

| 문서 source | 건수 |
|---|---:|
| `external_job_posting` | 1,899 |
| `skill_trend` | 20 |
| `hrdk` | 9 |
| `global_startup` | 1 |
| 합계 | 1,929 |

현재 문서 1,929건의 metadata에는 다음 임베딩 정보가 기록되어 있습니다.

```text
embedding_provider = openai
embedding_model = text-embedding-3-small
```

### 현재 제한 사항

임베딩 저장과 검색 API는 준비되어 있지만, **현재 앱의 로드맵 추천 결과에는 RAG 검색 결과를 연결하지 않았습니다.**

현재 RAG 문서에는 목표 직무 7개 외 공고도 포함되어 있습니다. 예를 들어 영업 직군 공고가 문서에 포함될 수 있으므로, 이 상태로 추천 근거에 직접 연결하면 관련 없는 문서가 섞일 위험이 있습니다.

RAG 연결 전에 필요한 작업:

1. 7개 목표 직무용 RAG 문서만 새로 구성합니다.
2. 문서 metadata에 `job_role_category`를 추가합니다.
3. 검색 시 선택한 직무로 필터링한 뒤 유사도 검색합니다.
4. 새 문서 본문이 달라지므로 해당 문서만 임베딩을 새로 생성합니다.
5. 검색된 공고를 추천 근거 카드에 회사명, 기술, 공고 링크와 함께 노출합니다.

## 7. 현재 추천 엔진과 에이전트 상태

### 실제 앱에서 사용 중인 추천 흐름

현재 앱의 `POST /api/v1/agent/career-path`는 이름은 agent API이지만, 실제로는 다음 흐름으로 동작합니다.

```text
사용자 직무/관심 소재/기술 수준 입력
-> JobRoleSkillEvidence에서 해당 직무의 strong/moderate 기술 조회
-> 시장 점수와 사용자 수준으로 보완 우선순위 계산
-> 직무별 프로젝트 블루프린트 조립
-> 12주 로드맵 저장
```

즉, 현재 사용자에게 노출되는 추천 결과는 **RAG 문서 검색이나 LLM 생성 결과가 아니라, 정제된 공고 집계 근거 기반 추천 엔진의 결과**입니다.

### 코드상 존재하지만 현재 앱 흐름에서 사용하지 않는 부분

`backend/app/services/agent_service.py`에는 RAG 검색 결과와 RandomForest 예측 서비스를 조합하는 초기 `AgentCareerService` 구현이 있습니다. 그러나 현재 `/api/v1/agent/career-path` endpoint는 이 클래스를 호출하지 않으며 응답의 `evidence_documents`도 빈 배열로 반환합니다.

또한 `POST /api/v1/model/predict`의 RandomForest는 실제 과거 채용 데이터로 학습된 운영 모델이 아니라, 코드에 정의된 소규모 예시 feature로 즉시 학습하는 프로토타입 endpoint입니다. 현재 12주 로드맵 점수에는 사용하지 않습니다.

### 과거 시장 데이터

Adzuna 기반 과거 데이터 수집 모듈은 존재하며 DB에 84행이 저장되어 있습니다.

중요한 제한:

- 현재 endpoint에서 수집하는 값은 역사적 공고 수나 기술 수요가 아니라 **월별 평균 연봉**입니다.
- 따라서 “12주 뒤 어떤 스킬의 채용 수요가 증가한다”를 직접 예측하는 근거로 사용하기에는 부족합니다.
- 향후 공고 수 또는 기술 출현 빈도의 시간축 데이터가 확보되어야 트렌드 예측의 근거가 강화됩니다.

## 8. 프로젝트 평가와 AI 사용 정책

### 무료 규칙 평가

`과제검증` 탭에서 프로젝트 제출 시 무료 규칙 평가가 먼저 수행됩니다.

필수 입력:

| 입력 항목 | 최소 조건 |
|---|---|
| 문제 정의 | 10자 이상 |
| 데이터와 목표 변수 | 5자 이상 |
| 측정 결과와 비교 내용 | 5자 이상 |
| 실패 사례, 한계, 개선 계획 | 5자 이상 |

추가 입력인 GitHub URL, 사용 기술, 구현 방식, 평가 지표, README는 점수와 평가 충실도에 영향을 줍니다.

무료 평가는 다음을 확인합니다.

- 문제와 목표가 설명되었는지
- 추천 프로젝트의 기술 또는 모델 사용 근거가 있는지
- 평가 지표와 실제 수치가 있는지
- 실패 사례와 개선 계획이 있는지
- GitHub/README/실행 방법 등 전달 가능한 근거가 있는지

### 요청형 AI 엄격 리뷰

AI 리뷰는 사용자가 `AI에게 엄격 평가받기` 버튼을 누른 경우에만 실행됩니다.

- 기본 모델: `gpt-5.4-mini`
- 기본 응답 한도: `900` output tokens
- AI 리뷰 월별 예상 비용 상한 기본값: `$1.00`
- AI 리뷰는 무료 규칙 평가 점수를 올리지 않으며, 확인되지 않은 주장과 수정 우선순위를 텍스트로 제공합니다.
- 사용자가 명시적으로 요청하지 않는 한 OpenAI API를 임의로 호출하지 않는 운영 원칙을 따릅니다.

## 9. 아키텍처

```text
frontend/ (Expo React Native)
  -> Axios + Bearer token

backend/ (FastAPI)
  -> 인증/프로필/로드맵/프로젝트 평가/데이터 수집/RAG API
  -> 스케줄러: 공개 ATS 채용공고 일 1회 수집

PostgreSQL + pgvector
  -> 사용자 및 로드맵
  -> 해외 채용공고와 직무-스킬 근거
  -> 과거 시장 데이터
  -> 문서와 임베딩 벡터
```

### 기술 스택

| 구분 | 기술 |
|---|---|
| Frontend | Expo, React Native, React Navigation, Axios, AsyncStorage, lucide-react-native |
| Backend | FastAPI, SQLAlchemy, Pydantic, requests, scikit-learn |
| Database | PostgreSQL, pgvector |
| Infra | Docker Compose |
| Data | 공개 ATS API, Adzuna history API, HRDK/Q-Net 연계 구조 |
| AI | OpenAI Embeddings, 선택형 OpenAI 텍스트 리뷰 |

## 10. 주요 API

인증이 필요한 개인 API는 `Authorization: Bearer <token>` 헤더가 필요합니다.

### Auth / User

| Method | Endpoint | 설명 |
|---|---|---|
| `POST` | `/api/v1/auth/signup` | 회원가입 |
| `POST` | `/api/v1/auth/login` | 로그인 |
| `GET` | `/api/v1/auth/me` | 현재 사용자 및 GitHub 주소 조회 |
| `POST` | `/api/v1/users/profile` | 목표 직무, 관심 소재, 기술 체크리스트 저장 |
| `PATCH` | `/api/v1/users/me/github` | GitHub 주소 저장/수정 |

### Roadmap / Analysis

| Method | Endpoint | 설명 |
|---|---|---|
| `POST` | `/api/v1/agent/career-path` | 공고 근거 기반 12주 분석 결과 생성 |
| `POST` | `/api/v1/roadmaps` | 활성 로드맵 생성 |
| `GET` | `/api/v1/roadmaps/me` | 회원의 현재 활성 로드맵 조회 |
| `GET` | `/api/v1/roadmaps/me/progress` | 진행률 조회 |
| `PATCH` | `/api/v1/roadmaps/tasks/{task_id}/toggle` | task 완료 토글 |
| `POST` | `/api/v1/roadmaps/me/reassessments` | 6/12주차 재진단 저장 |
| `GET` | `/api/v1/roadmaps/certifications/beta` | Data Scientist 자격증 일정 조회 |
| `POST` | `/api/v1/roadmaps/me/certifications/{code}/include` | 자격증 준비 task 추가 |

### Project Review

| Method | Endpoint | 설명 |
|---|---|---|
| `POST` | `/api/v1/projects/submissions` | 프로젝트 무료 규칙 평가 |
| `POST` | `/api/v1/projects/submissions/{submission_id}/ai-review` | 선택형 AI 엄격 리뷰 |

### Jobs / Trends / History

| Method | Endpoint | 설명 |
|---|---|---|
| `POST` | `/api/v1/external-jobs/collect` | 공개 ATS 채용공고 수집 |
| `GET` | `/api/v1/external-jobs` | 해외 공고 조회 |
| `GET` | `/api/v1/external-jobs/skills/summary` | 추출 스킬 집계 |
| `GET` | `/api/v1/trends/role-skills` | 직무별 스킬 근거 조회 |
| `GET` | `/api/v1/trends/role-history` | 과거 시장 지표 조회 |

### RAG / Data Collection

| Method | Endpoint | 설명 |
|---|---|---|
| `POST` | `/api/v1/rag/documents` | 문서와 임베딩 저장 |
| `POST` | `/api/v1/rag/query` | 벡터 유사 문서 검색 |
| `POST` | `/api/v1/data/jobs/collect` | 공공/외부 데이터 수집 및 파일 저장 |
| `GET` | `/api/v1/data/jobs` | 정제된 수집 데이터 조회 |

## 11. 실행 방법

### Backend / Database

프로젝트 루트에서 실행합니다.

```powershell
docker compose up -d --build
docker compose ps
docker compose logs -f backend
```

확인 URL:

```text
Health:  http://127.0.0.1:8000/health
Swagger: http://127.0.0.1:8000/docs
```

Docker Compose 구성:

| 서비스 | 역할 | 포트 |
|---|---|---:|
| `career-backend` | FastAPI 서버 | 8000 |
| `career-postgres` | PostgreSQL + pgvector | 5432 |

### Frontend

```powershell
cd frontend
npm install
npx expo start --lan
```

실제 휴대폰에서 Expo Go로 테스트할 경우 API URL에는 PC의 IPv4 주소를 사용합니다.

```env
EXPO_PUBLIC_API_BASE_URL=http://192.168.35.167:8000
```

## 12. 환경변수

키와 비밀번호는 `.env`에만 저장하고 README 또는 코드에 실제 값을 기록하지 않습니다. 필요한 변수 예시는 [.env.example](./.env.example)에 있습니다.

```env
DATABASE_URL=
EXPO_PUBLIC_API_BASE_URL=

EXTERNAL_JOBS_AUTO_COLLECT_ENABLED=true
EXTERNAL_JOBS_INITIAL_DELAY_SECONDS=60
EXTERNAL_JOBS_INTERVAL_SECONDS=86400

PUBLIC_DATA_API_KEY=
HRDK_CERT_ITEMS_URL=

OPENAI_API_KEY=
OPENAI_REVIEW_MODEL=gpt-5.4-mini
OPENAI_REVIEW_MONTHLY_BUDGET_USD=1.00
OPENAI_REVIEW_MAX_OUTPUT_TOKENS=900
```

### HRDK/Q-Net 참고

- `HRDK_CERT_ITEMS_URL`은 공공데이터포털 상세 페이지 주소가 아니라 실제 OpenAPI 요청 endpoint여야 합니다.
- Q-Net 자격 종목 API의 `seriesCd` 예:
  - `01`: 기술사
  - `02`: 기능장
  - `03`: 기사
  - `04`: 기능사
- 현재 HRDK 관련 문서 9건은 RAG 문서로 저장되어 있으나, 자격증 BETA 일정 화면은 고정된 공식 일정 데이터를 사용합니다.

## 13. 현재 알려진 제한 및 주의사항

- RAG 임베딩 문서는 존재하지만 현재 추천 결과 생성에는 아직 사용하지 않습니다.
- 현재 RAG 문서에는 목표 7개 직무 외 공고가 포함되어 있어, 직무 필터링 후 재문서화가 필요합니다.
- 추천 알고리즘은 취업 성공 확률이나 12주 후 합격 가능성을 예측하지 않습니다.
- 프로젝트 AI 리뷰는 코드를 직접 실행하거나 GitHub 저장소의 진위를 확인하지 않습니다.
- Data Scientist 자격증 기능은 BETA이며 SQLD/ADsP만 지원합니다.
- 과거 시장 데이터는 현재 평균 연봉 지표이므로 기술 수요 변화 예측 자료로 직접 쓰기 어렵습니다.
- DB 실행 시 PostgreSQL collation version mismatch 경고가 확인됩니다. 현재 연결과 조회는 가능하지만 운영 전 정리가 필요합니다.
- Docker Compose의 `version` 필드 obsolete 경고가 표시됩니다. 동작에는 영향이 없지만 추후 설정 정리가 필요합니다.
- Expo가 `babel-preset-expo`의 권장 호환 버전 경고를 표시하고 있으므로 배포 전 dependency 정리가 필요합니다.

## 14. 다음 개발 우선순위

1. 정제된 7개 직무 공고만 대상으로 RAG 문서 컬렉션을 새로 구성합니다.
2. RAG metadata에 `job_role_category`, 회사명, 기술, URL을 저장하고 직무 필터 검색을 구현합니다.
3. 비용을 먼저 산정한 뒤 새 문서에 한해서 임베딩을 생성합니다.
4. 결과 화면에서 추천 기술마다 실제 근거 공고를 조회할 수 있도록 RAG 결과를 연결합니다.
5. 공고 수와 스킬 출현 빈도를 시간축으로 수집하여 과거 기반 트렌드 근거를 강화합니다.
6. 사용자 결과물과 진행 데이터가 축적되면 후속 사용자 추천에 활용할 학습/협업 필터링 구조를 검토합니다.

## 15. 보안 및 비용 정책

- `.env`의 API key, DB 비밀번호, 토큰 값은 Git 또는 문서에 기록하지 않습니다.
- OpenAI API를 사용하는 기능은 임베딩 생성/검색 질문 임베딩 및 사용자가 누른 AI 리뷰입니다.
- 프로젝트 AI 리뷰에는 기본 `$1.00` 월 예상 비용 상한 방어 로직이 있습니다.
- 임베딩 재생성은 실행 전에 대상 문서 수와 예상 비용을 먼저 확인한 뒤 진행합니다.
- 사용자 승인 없이 OpenAI 토큰을 사용하는 배치 작업을 실행하지 않습니다.
