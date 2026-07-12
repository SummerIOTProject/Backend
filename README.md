<<<<<<< HEAD
# Backend
=======
# 스마트 급식 섭취 분석 및 맞춤 배식 추천 시스템

RFID 카드로 사용자를 식별하고, 날짜별 식단과 메뉴를 관리하며, 식전·식후 이미지를 기반으로 메뉴별 섭취 비율을 분석하고 다음 배식 단계를 추천하는 FastAPI 백엔드 프로젝트입니다.

## 주요 기능

- 사용자 등록/조회/수정
- RFID 카드 등록, 스캔, 비활성화
- 날짜별 식단 및 메뉴 관리
- 사용자별 식사 기록 생성 및 조회
- 식전/식후 이미지 업로드 및 정적 파일 제공
- 결정적 MOCK 분석 및 향후 확장 가능한 비전 분석 구조
- 메뉴별 섭취 비율 저장 및 재분석
- 과거 동일 메뉴 이력 기반 배식 추천
- 관리자 대시보드 및 잔반 요약 통계

## 폴더 구조

```text
Backend/
├── app/
├── alembic/
├── tests/
├── uploads/
├── .env
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
├── Dockerfile
└── README.md
```

## Python 3.12 가상환경 생성

```bash
python3 -m venv venv
source venv/bin/activate
```

## 설치 명령

```bash
python3 -m pip install -r requirements.txt
```

## .env 생성 방법

```bash
cp .env.example .env
```

필요 시 `DATABASE_URL`, `ADMIN_API_KEY`, `VISION_API_KEY` 값을 수정합니다.

## Alembic 명령

```bash
alembic upgrade head
alembic downgrade -1
```

## 서버 실행 명령

macOS 실행 예시:

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

또는 기본 실행:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Swagger 주소

```text
http://127.0.0.1:8000/docs
```

## 테스트 실행 명령

```bash
python -m compileall app
pytest -q
```

## 대표 API 호출 순서

1. 사용자 등록
2. RFID 카드 등록
3. 식단 등록
4. 식사 기록 생성
5. 식전 이미지 업로드
6. 식후 이미지 업로드
7. MOCK 분석 실행
8. 분석 결과 조회
9. 배식 추천 조회

## curl 예시

사용자 등록:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name":"정준서","student_number":"20223137"}'
```

RFID 등록:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/rfid-cards \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"uid":"04A3B29C7F6180"}'
```

식단 등록:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/meals \
  -H "Content-Type: application/json" \
  -d '{
    "meal_date":"2026-07-12",
    "meal_type":"LUNCH",
    "school_name":"국민대학교",
    "menu_items":[
      {"name":"쌀밥","category":"RICE","tray_section":1,"display_order":1},
      {"name":"제육볶음","category":"MAIN_DISH","tray_section":2,"display_order":2},
      {"name":"김치","category":"SIDE_DISH","tray_section":3,"display_order":3}
    ]
  }'
```

식사 기록 생성:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/meal-records \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"meal_id":1}'
```

## 이미지 업로드 curl 예시

식전 이미지 업로드:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/meal-records/1/images/before \
  -F "file=@./before.jpg"
```

식후 이미지 업로드:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/meal-records/1/images/after \
  -F "file=@./after.jpg"
```

## MOCK 분석 실행 예시

```bash
curl -X POST http://127.0.0.1:8000/api/v1/meal-records/1/analyze \
  -H "Content-Type: application/json" \
  -d '{"analysis_type":"MOCK"}'
```

추천 조회:

```bash
curl "http://127.0.0.1:8000/api/v1/users/1/serving-recommendations?meal_id=1"
```

관리자 대시보드:

```bash
curl "http://127.0.0.1:8000/api/v1/admin/dashboard?date=2026-07-12" \
  -H "X-Admin-Key: admin-secret"
```
>>>>>>> ce2299d (Initial backend commit)
