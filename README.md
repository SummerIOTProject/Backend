# 스마트 급식 분석 시스템 백엔드

학생 웹 로그인과 Arduino RFID 현장 식별을 분리한 FastAPI 백엔드입니다. 학생은 `login_id + password + JWT`로 본인 기록을 조회하고, 현장 장치는 `X-Device-Key + RFID UID`로 학생을 식별합니다.

## 시스템 개요

- 학생 웹
  - 회원가입, 로그인, Refresh Token, 로그아웃, 비밀번호 변경
  - 내 정보, 알레르기 19종, RFID 카드, 식사 기록, 최근 5일 기록, 섭취율 보정, 영양소, 배식량 추천 조회
- Arduino UNO R4 WiFi
  - RFID UID 읽기
  - `meal_type`과 함께 `/api/v1/device/rfid/scan` 호출
  - TFT/LED/부저용 JSON 표시
- VLM 서버
  - 식전/식후 사진 비교
  - 메뉴별 `consumed_ratio`, `confidence`, `note` 추정
  - 영양소 계산, 알레르기 판정, 추천 로직은 서버 코드가 결정적으로 처리

## VLM 기반 분석 방식

이 프로젝트는 YOLO/SAM/OpenCV 면적 비교 대신 VLM을 사용합니다.

- 입력: 식전 이미지, 식후 이미지, 당일 메뉴 목록
- 출력: 메뉴별 섭취율, 신뢰도, 간단한 메모
- 제한: 실제 무게 측정값이 아니라 시각적 추정값입니다.

## 알레르기 19종

`EGGS`, `MILK`, `BUCKWHEAT`, `PEANUT`, `SOYBEAN`, `WHEAT`, `MACKEREL`, `CRAB`, `SHRIMP`, `PORK`, `PEACH`, `TOMATO`, `SULFITES`, `WALNUT`, `CHICKEN`, `BEEF`, `SQUID`, `SHELLFISH`, `PINE_NUT`

## 설치 방법

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 환경변수

```env
APP_NAME=smart-meal-api
APP_ENV=development
DEBUG=true
PORT=8000

DATABASE_URL=sqlite:///./meal_service.db
DATABASE_URL_UNPOOLED=
SCHOOL_NAME=국민대학교
APP_TIMEZONE=Asia/Seoul

JWT_SECRET_KEY=replace-with-secure-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=14

DEVICE_API_KEY=replace-with-device-key
RUN_MIGRATIONS_ON_START=true

OPENAI_API_KEY=
OPENAI_MODEL=

GEMINI_API_KEY=
GEMINI_MODEL=

VISION_ANALYSIS_MODE=MOCK
VISION_TIMEOUT_SECONDS=60
VISION_MAX_RETRIES=2

STORAGE_BACKEND=LOCAL
BLOB_READ_WRITE_TOKEN=
VERCEL_OIDC_TOKEN=

UPLOAD_DIR=uploads
MAX_IMAGE_SIZE_MB=4
ANALYSIS_IMAGE_MAX_DIMENSION=1600
ANALYSIS_IMAGE_JPEG_QUALITY=80

CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

운영 환경에서는 `JWT_SECRET_KEY=replace-with-secure-secret`, `DEVICE_API_KEY=replace-with-device-key` 상태로 시작할 수 없습니다.
실제 비밀키와 API Key는 Git에 커밋하지 마세요.

## DB와 Migration

이 저장소는 개발 DB 초기화 방식으로 정리되어 있습니다.

- 최종 기준 DB 파일명: `meal_service.db`
- Alembic URL: `sqlite:///./meal_service.db`
- Alembic migration용 direct URL이 있으면 `DATABASE_URL_UNPOOLED`를 우선 사용합니다.
- 서비스 기준 학교명: `SCHOOL_NAME=국민대학교`
- 서비스 기준 시간대: `APP_TIMEZONE=Asia/Seoul`
- 기존 개발 DB가 있으면 삭제 후 다시 생성하는 것을 권장합니다.

```bash
rm -f meal_service.db
alembic upgrade head
```

기존 `EGG` 코드는 `EGGS`, `SULFITE` 코드는 `SULFITES`로 정규화됩니다.

## Docker 및 실행 준비

Docker 이미지는 `.env`를 포함하지 않습니다.

- `.env`를 이미지에 복사하지 않습니다.
- 환경변수는 컨테이너 실행 환경에서 주입해야 합니다.
- `start.sh`는 기본적으로 migration 실행 후 Uvicorn을 시작합니다.
- `RUN_MIGRATIONS_ON_START=false`이면 migration 없이 서버만 시작합니다.
- 서버 포트는 `PORT` 환경변수를 사용합니다.

SQLite 개발 예시:

```env
DATABASE_URL=sqlite:///./meal_service.db
UPLOAD_DIR=uploads
```

영구 볼륨 예시:

```env
DATABASE_URL=sqlite:////data/meal_service.db
UPLOAD_DIR=/data/uploads
```

PostgreSQL 예시:

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/smart_meal
```

Neon 운영 예시:

```env
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+psycopg://pooled-user:password@host/db
DATABASE_URL_UNPOOLED=postgresql+psycopg://direct-user:password@host/db
STORAGE_BACKEND=VERCEL_BLOB
BLOB_READ_WRITE_TOKEN=...
```

Vercel은 `app/main.py`의 FastAPI app을 Function entrypoint로 사용합니다.

- `pyproject.toml`: `app.main:app`
- `vercel.json`: `app/main.py` max duration 설정
- `Dockerfile`과 `start.sh`는 Vercel 배포에 사용되지 않습니다.
- migration은 Vercel Function 시작 시 실행하지 않습니다.
- Neon pooled URL은 애플리케이션 요청용입니다.
- Neon direct URL은 migration용입니다.
- Preview와 Production DB는 분리하는 것을 권장합니다.

영구 저장소가 없는 환경에서는 SQLite DB 파일과 업로드 이미지가 컨테이너 재시작 시 사라질 수 있습니다.

컨테이너 내부에서도 관리자 생성 스크립트를 사용할 수 있습니다.

```bash
python scripts/create_admin.py \
  --login-id admin1 \
  --name 관리자 \
  --student-number ADMIN001 \
  --password AdminPassword123!
```

## 관리자 생성

SQL 직접 수정 대신 스크립트를 사용합니다.

```bash
python scripts/create_admin.py \
  --login-id admin1 \
  --name 관리자 \
  --student-number ADMIN001 \
  --password AdminPassword123!
```

## 인증 API 예시

회원가입:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "login_id": "junseo0309",
    "password": "Password123!",
    "name": "정준서",
    "student_number": "20223137",
    "allergen_codes": ["MILK", "PINE_NUT"]
  }'
```

로그인:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login_id":"junseo0309","password":"Password123!"}'
```

Refresh Token:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"REFRESH_TOKEN"}'
```

내 정보:

```bash
curl http://127.0.0.1:8000/api/v1/me \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

## 알레르기 수정

```bash
curl -X PUT http://127.0.0.1:8000/api/v1/me/allergens \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"allergen_codes":["MILK","SHRIMP","PINE_NUT"]}'
```

## RFID 카드 정책

현재 구조는 학생 1명당 여러 RFID 카드를 허용합니다.

- `GET /api/v1/me/rfid-cards`
- `POST /api/v1/me/rfid-cards`
- `PATCH /api/v1/me/rfid-cards/{card_id}/deactivate`

UID는 전체 unique이며, 비활성 카드는 스캔되지 않습니다.

## Arduino Device Key

장치 API는 JWT 대신 `X-Device-Key`를 사용합니다.

## RFID scan + meal_type

장치 스캔과 식사 기록 생성은 다음 기준을 함께 검증합니다.

- 오늘 날짜는 `APP_TIMEZONE` 기준으로 계산합니다.
- 급식은 `meal_date + meal_type + SCHOOL_NAME`으로 조회합니다.
- 비활성 RFID 카드와 비활성 사용자 계정은 거부합니다.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/device/rfid/scan \
  -H "X-Device-Key: replace-with-device-key" \
  -H "Content-Type: application/json" \
  -d '{"uid":"04A3B29C7F6180","meal_type":"LUNCH"}'
```

## 메뉴 등록

```bash
curl -X POST http://127.0.0.1:8000/api/v1/admin/menus \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "제육볶음",
    "standard_serving_g": 120,
    "nutrition_per_100g": {
      "calories_kcal": 220,
      "carbohydrate_g": 12,
      "protein_g": 18,
      "fat_g": 11
    },
    "ingredients": ["돼지고기", "양파", "고추장", "간장"],
    "allergen_codes": ["SOYBEAN", "WHEAT", "PORK"]
  }'
```

## 급식 등록

```bash
curl -X POST http://127.0.0.1:8000/api/v1/admin/meals \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "meal_date": "2026-07-13",
    "meal_type": "LUNCH",
    "school_name": "국민대학교",
    "menu_ids": [1, 2, 3]
  }'
```

## 식사 기록 생성

```bash
curl -X POST http://127.0.0.1:8000/api/v1/device/meal-records \
  -H "X-Device-Key: replace-with-device-key" \
  -H "Content-Type: application/json" \
  -d '{"rfid_uid":"04A3B29C7F6180","meal_id":1}'
```

## 핸드폰 식전/식후 사진 업로드

```bash
curl -X POST http://127.0.0.1:8000/api/v1/me/meal-records/1/images/before \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -F "file=@before.jpg"
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/me/meal-records/1/images/after \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -F "file=@after.png"
```

이미지는 업로드 시 다음 정책을 적용합니다.

- MIME 타입 검사
- 확장자 검사
- Pillow 검증
- EXIF 방향 보정
- 긴 변 리사이즈
- UUID 파일명
- 최대 4MB

Vercel 환경에서는 요청 본문 제한 때문에 원본 이미지가 4MB를 넘으면 애플리케이션 도달 전 거부될 수 있습니다.

- 프론트엔드에서 업로드 전에 긴 변 1600px 이하로 압축해야 합니다.
- 업로드 전에 4MB 이하인지 확인해야 합니다.
- Vercel 요청/응답 크기 제한을 고려해 저장 단계에서 4MB 이하를 유지합니다.

식전 또는 식후 이미지를 다시 업로드하면 기존 분석 결과는 무효화됩니다.

- 기존 `meal_item_records` 삭제
- `completed_at` 초기화
- `failure_reason` 초기화
- 추천 캐시 삭제
- 실제 DB에 존재하는 BEFORE/AFTER 이미지 기준으로 상태 재계산

현재 상태 정책:

- BEFORE + AFTER 있음: `IMAGES_UPLOADED`
- BEFORE만 있음: `BEFORE_IMAGE_UPLOADED`
- AFTER만 있음: `CREATED`
- 둘 다 없음: `CREATED`

## Private Vercel Blob

- 공식 Python 패키지는 `vercel`입니다.
- 공식 Blob API는 `vercel.blob.BlobClient`를 사용합니다.
- `STORAGE_BACKEND=VERCEL_BLOB`일 때 Private Blob을 사용합니다.
- Private Blob은 읽기와 쓰기 모두 인증이 필요합니다.
- 현재 구현에서는 Vercel 환경이어도 `BLOB_READ_WRITE_TOKEN`이 필수입니다.
- `BLOB_STORE_ID`는 현재 BlobClient 기반 구현에서 필수가 아닌 선택 설정입니다.
- `VERCEL_OIDC_TOKEN`은 일반 Blob token처럼 직접 전달하지 않습니다.
- 공식 OIDC 인증 경로는 향후 별도 검증 후 적용해야 합니다.
- DB에는 공개 URL 대신 storage key를 저장합니다.
- 이미지 조회는 API 서버가 권한을 확인한 뒤 image bytes를 반환합니다.
- Private Blob `get`에는 `access=\"private\"`를 명시합니다.
- `exists`는 `head`를 사용하고, `read`는 `get`, `delete`는 `delete`를 사용합니다.
- 없는 파일과 인증·서비스 오류를 구분합니다.
- HTTP 상태 기반 fallback 분류가 필요할 때는 `exc.status_code`와 `exc.response.status_code`를 순서대로 사용합니다.
- Blob SDK 호출 실패 시 LOCAL 저장소로 자동 fallback하지 않습니다.
- readiness의 `storage=UP`은 설정이 유효하다는 의미이며, 실제 Blob 네트워크 연결을 매 요청 검증하지는 않습니다.
- 실제 Blob 동작은 배포 후 업로드, 조회, 재업로드 흐름으로 확인해야 합니다.
- Blob 토큰, Blob URL, 내부 저장 경로는 응답에 노출하지 않습니다.
- GitHub push 후 Vercel이 연결돼 있으면 자동 배포가 실행될 수 있습니다.
- 비밀키와 DB URL, Blob 토큰은 Git에 커밋하면 안 됩니다.

## 이미지 접근 권한

이미지 정적 공개를 사용하지 않습니다.

- `GET /api/v1/me/meal-images/{image_id}`
- 본인 기록 또는 관리자만 조회 가능
- DB 행은 있어도 실제 파일이 없으면 `IMAGE_FILE_NOT_FOUND`를 반환합니다.

개인정보 제한사항:

- URL 직접 추측으로는 이미지를 볼 수 없도록 인증 API를 사용합니다.
- 식판 이미지는 개인정보로 취급해야 합니다.

## MOCK VLM

```env
VISION_ANALYSIS_MODE=MOCK
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/me/meal-records/1/analyze \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

## GEMINI_VLM

```env
VISION_ANALYSIS_MODE=GEMINI_VLM
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-2.5-flash
VISION_TIMEOUT_SECONDS=60
VISION_MAX_RETRIES=2
```

- Gemini API Key 발급이 필요합니다.
- 이미지 입력 지원 모델명은 Google AI Studio 문서를 확인해 설정하세요.
- 무료 티어에는 요청 한도가 있을 수 있습니다.
- 무료 티어 제공 모델과 한도는 변경될 수 있습니다.
- 무료 사용을 코드가 보장하지 않습니다.
- `VISION_TIMEOUT_SECONDS`는 Gemini 요청 1회당 제한 시간입니다.
- `VISION_MAX_RETRIES`는 최초 요청 이후 추가 재시도 횟수입니다.
- timeout, 연결 오류, 일부 5xx와 quota/rate limit 계열 오류는 제한 횟수 안에서 재시도합니다.
- 잘못된 API Key, 권한 오류, 요청 형식 오류는 재시도하지 않습니다.
- 한도 소진 시 `VISION_QUOTA_EXCEEDED` 오류가 발생할 수 있습니다.
- Gemini 실패 시 MOCK으로 자동 대체하지 않습니다.
- 학생 식별정보는 Gemini로 보내지 않습니다.
- 급식판만 촬영하고 얼굴, 학번, RFID 카드가 사진에 나오지 않도록 안내해야 합니다.

`POST /api/v1/analyses/compare-images`도 위 설정이 `GEMINI_VLM`이면 Gemini를 사용합니다. 이 API는 식전·식후 이미지 두 장만 메모리에서 비교하며 식사 기록, RFID, 당일 급식, 이미지·분석 결과 저장을 사용하지 않습니다. 직접 비교 API에서는 `MOCK` 모드를 허용하지 않으며 Gemini 실패 시 OpenAI 또는 MOCK으로 대체하지 않습니다.

직접 비교 이미지의 개별 최대 크기는 필요하면 다음 값으로 별도 조정할 수 있습니다.

```env
MAX_ANALYSIS_IMAGE_SIZE_MB=4
```

## OPENAI_VLM

```env
VISION_ANALYSIS_MODE=OPENAI_VLM
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini
VISION_TIMEOUT_SECONDS=60
VISION_MAX_RETRIES=2
```

분석 요청 body는 사용하지 않습니다. 서버 실행 모드는 `VISION_ANALYSIS_MODE`가 결정합니다.
기존 `VISION_MODEL`은 하위 호환용으로만 남아 있으며, 새 설정에서는 `OPENAI_MODEL` 사용을 권장합니다.

## Health Check

- `GET /health/live`: 프로세스 liveness 확인
- `GET /health` 또는 `GET /health/ready`: DB `SELECT 1`과 업로드 저장소 쓰기 가능 여부 확인

`/health`는 내부 경로나 `DATABASE_URL` 원문을 노출하지 않습니다.

## 분석 실패와 재분석 정책

- `POST /api/v1/me/meal-records/{id}/analyze`
  - 이미 `COMPLETED`면 기존 결과를 반환합니다.
  - `ANALYZING`이면 `409 ANALYSIS_ALREADY_RUNNING`
- `POST /api/v1/me/meal-records/{id}/reanalyze`
  - 보정된 항목이 있으면 `409`
  - 실패 시 `meal_records.status=FAILED`
  - `failure_reason`에는 내부 요약만 저장합니다.

## 최근 5일 계산 기준

`days=5`면 오늘 포함 최근 5개 날짜만 조회합니다.

- 오늘
- 1일 전
- 2일 전
- 3일 전
- 4일 전

계산식:

- `start_date = today - timedelta(days=days - 1)`

## 섭취율 보정과 confidence 의미

- `consumed_ratio`: 현재 적용되는 최종 값
- `confidence`: 원래 VLM 분석 신뢰도
- `is_corrected=true`가 되면 보정 후 `confidence=null`로 처리합니다.

## 영양소 계산

서버가 조회 시 계산합니다.

- `estimated_consumed_g = standard_serving_g × consumed_ratio`
- `calories_kcal = calories_per_100g × estimated_consumed_g / 100`
- 나머지 탄수화물/단백질/지방도 동일 방식

## 배식량 추천

- 기준: 최근 5일, 동일 `menu_id`, 완료된 기록만 사용
- 현재 추천 대상 `meal_id`의 분석 결과는 평균에서 제외
- `sample_count=0`: 이전 섭취 기록이 없어 기준 제공량 추천
- `sample_count=1`: 최근 데이터가 1건뿐이므로 참고용 추천
- `sample_count>=2`: 최근 5일 평균 섭취율 표시

## 메뉴 비활성화 정책

`DELETE /api/v1/admin/menus/{menu_id}`는 물리 삭제가 아니라 `is_active=false` 처리입니다. 과거 기록은 유지되고 비활성 메뉴는 새 급식에 연결할 수 없습니다.

## 관리자 통계

- `GET /api/v1/admin/users`
- `GET /api/v1/admin/dashboard?date=YYYY-MM-DD`
- `GET /api/v1/admin/leftover-summary?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

## 테스트와 실행

```bash
python -m compileall app scripts
alembic upgrade head
pytest -q
```

Docker 준비 상태를 확인할 때는 필요하면 다음을 실행할 수 있습니다.

```bash
DATABASE_URL=sqlite:///./deployment_test.db alembic upgrade head
```

```bash
uvicorn app.main:app --reload
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## 제한사항

- VLM 섭취율은 실제 계량값이 아니라 시각적 추정값입니다.
- 현재 프로젝트에는 별도 rate limit 미들웨어를 넣지 않았습니다.
  - 향후 `/auth/login`, `/auth/refresh`, `/device/rfid/scan`, `/analyze`에 rate limit 추가를 권장합니다.
