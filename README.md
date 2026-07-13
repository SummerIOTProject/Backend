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

DATABASE_URL=sqlite:///./meal_service.db

JWT_SECRET_KEY=replace-with-secure-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=14

DEVICE_API_KEY=replace-with-device-key

OPENAI_API_KEY=
VISION_MODEL=gpt-4o-mini
VISION_ANALYSIS_MODE=MOCK
VISION_TIMEOUT_SECONDS=60
VISION_MAX_RETRIES=2

UPLOAD_DIR=uploads
MAX_IMAGE_SIZE_MB=10
ANALYSIS_IMAGE_MAX_DIMENSION=2048
ANALYSIS_IMAGE_JPEG_QUALITY=85

CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

운영 환경에서는 `JWT_SECRET_KEY=replace-with-secure-secret`, `DEVICE_API_KEY=replace-with-device-key` 상태로 시작할 수 없습니다.

## DB와 Migration

이 저장소는 개발 DB 초기화 방식으로 정리되어 있습니다.

- 최종 기준 DB 파일명: `meal_service.db`
- Alembic URL: `sqlite:///./meal_service.db`
- 기존 개발 DB가 있으면 삭제 후 다시 생성하는 것을 권장합니다.

```bash
rm -f meal_service.db
alembic upgrade head
```

기존 `EGG` 코드는 `EGGS`, `SULFITE` 코드는 `SULFITES`로 정규화됩니다.

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

## 이미지 접근 권한

이미지 정적 공개를 사용하지 않습니다.

- `GET /api/v1/me/meal-images/{image_id}`
- 본인 기록 또는 관리자만 조회 가능

개인정보 제한사항:

- URL 직접 추측으로는 이미지를 볼 수 없도록 인증 API를 사용합니다.
- 식판 이미지는 개인정보로 취급해야 합니다.

## MOCK VLM

```env
VISION_ANALYSIS_MODE=MOCK
VISION_MODEL=gpt-4o-mini
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/me/meal-records/1/analyze \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

## OPENAI_VLM

```env
OPENAI_API_KEY=sk-...
VISION_ANALYSIS_MODE=OPENAI_VLM
VISION_MODEL=gpt-4o-mini
VISION_TIMEOUT_SECONDS=60
VISION_MAX_RETRIES=2
```

분석 요청 body는 사용하지 않습니다. 서버 실행 모드는 `VISION_ANALYSIS_MODE`가 결정합니다.

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
