# DA System - Setup Guide

새로운 환경에서 프로젝트를 클론하고 실행하는 방법입니다.

## 1. 저장소 클론

```bash
git clone https://github.com/developwho/da-system.git
cd da-system
```

## 2. Python 환경 설정

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

## 3. 프론트엔드 설정

```bash
cd frontend/da-insights-hub
npm install
```

## 4. 환경 변수 설정

`.env.example`을 복사하여 `.env` 파일 생성 후 API 키 입력:

```bash
# 루트 디렉토리에서
cp .env.example .env
```

`.env` 파일 편집:
```env
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
HUGGINGFACE_TOKEN=your_hf_token_here
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_key
```

## 5. Redis 실행

```bash
# Docker 사용
docker run -d -p 6379:6379 --name redis-da redis:7-alpine

# 또는 로컬 Redis 실행
redis-server
```

## 6. 데이터 파일 (선택사항)

대용량 데이터 파일이 필요한 경우:
- `data/train.csv`, `data/test.csv` 등을 별도로 다운로드
- Kaggle 등에서 원본 데이터셋 다운로드 후 `data/` 디렉토리에 배치

## 7. 실행

### 백엔드
```bash
# 루트 디렉토리에서
venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

### 프론트엔드
```bash
cd frontend/da-insights-hub
npm run dev
# http://localhost:8080
```

### Celery Worker (선택사항)
```bash
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

### MLflow UI (선택사항)
```bash
mlflow ui --backend-store-uri file:./mlruns
# http://localhost:5000
```

## 확인 사항

- ✅ Redis가 실행 중인가? → `redis-cli ping` (응답: PONG)
- ✅ Python 패키지 설치 완료? → `pip list | grep flaml`
- ✅ Node 패키지 설치 완료? → `ls frontend/da-insights-hub/node_modules`
- ✅ 환경 변수 설정 완료? → `.env` 파일 존재 확인

## 트러블슈팅

### Redis 연결 오류
```bash
docker ps | grep redis  # Redis 컨테이너 확인
docker start redis-da   # 중지된 경우 재시작
```

### Python 패키지 오류
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### 포트 충돌
- 백엔드 포트 변경: `uvicorn app.main:app --port 8001`
- 프론트엔드 포트는 `vite.config.ts`에서 변경

---

**최초 설정 소요 시간**: 약 10~15분
**다음 실행부터**: 백엔드 + 프론트엔드 실행만 하면 됨 (2분)
