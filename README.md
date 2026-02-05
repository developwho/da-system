# DA System - 데이터분석 자동화 에이전트

AI 에이전트 기반 자동 데이터 분석 시스템

## 빠른 시작

### 1. 환경 설정
```bash
# Python 가상환경
python -m venv venv
venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일에서 API 키 설정
```

### 3. Redis 시작
```bash
# Docker 사용
docker run -d -p 6379:6379 redis:7-alpine

# 또는 Windows용 Redis 설치
```

### 4. 서비스 시작
```bash
# Celery Workers
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo

# FastAPI (별도 터미널)
uvicorn app.main:app --reload --port 8000
```

### 5. API 문서 확인
브라우저에서 http://localhost:8000/docs

## 프로젝트 구조
자세한 내용은 [CLAUDE.md](CLAUDE.md) 참조

## 개발 계획
- Phase 1: 기본 인프라 (Week 1-2) ✅ 진행 중
- Phase 2: AutoML 파이프라인 (Week 3-5)
- Phase 3: 에이전트 시스템 (Week 6-8)
- Phase 4: 외부 API 통합 (Week 9-10)
- Phase 5: 인사이트 & 리포팅 (Week 11-12)

## 문서
- [프로젝트 개요](CLAUDE.md)
- [구현 계획서](.claude/plans/declarative-dancing-sloth.md)

## 라이선스
MIT License
