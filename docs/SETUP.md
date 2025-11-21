# Kurz AI Studio - 설치 및 실행 가이드

**최종 업데이트**: 2025-11-21

## 필수 요구사항

- Python 3.11+
- Node.js 18+
- Redis Server
- API Keys:
  - Google Gemini API Key
  - ElevenLabs API Key

---

## 1. 저장소 클론

```bash
git clone <repository_url>
cd Kurz_Studio_AI
```

---

## 2. Backend 설정

```bash
cd backend

# 가상환경 생성 (kvenv 이름 사용)
python -m venv kvenv
source kvenv/bin/activate  # Windows: kvenv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 입력
```

### 환경 변수 (.env)

```bash
# LLM & Image Generation
GEMINI_API_KEY=AI...

# TTS & Music
ELEVENLABS_API_KEY=sk_...

# Redis
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379
CELERY_RESULT_BACKEND=redis://localhost:6379
```

---

## 3. Redis 실행

```bash
# macOS (Homebrew)
brew services start redis

# Linux
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

---

## 4. Celery Worker 실행

```bash
cd backend
source kvenv/bin/activate

# gevent pool로 실행 (병렬 처리 필수!)
celery -A app.celery_app worker --loglevel=info --pool=gevent --concurrency=10
```

**중요**: `--pool=solo` 사용 금지! 병렬 실행이 불가능해집니다.

---

## 5. FastAPI 서버 실행

```bash
cd backend
source kvenv/bin/activate
uvicorn app.main:app --reload --port 8000
```

---

## 6. Frontend 실행

```bash
cd frontend
npm install
npm run dev
```

---

## 7. 접속

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs

---

## Celery Worker 재시작

`backend/app/` 하위 Python 파일 수정 시 **반드시 Worker 재시작 필요**:

```bash
# 1. 기존 Worker 종료
pkill -f "celery.*worker"

# 2. Worker가 종료되었는지 확인
ps aux | grep -i celery | grep -v grep

# 3. Worker 재시작
cd backend
source kvenv/bin/activate
celery -A app.celery_app worker --loglevel=info --pool=gevent --concurrency=10
```

---

## 트러블슈팅

### Redis 연결 실패

```bash
redis-cli ping
# 응답: PONG (정상)
```

### Celery 태스크가 실행되지 않음

```bash
# Worker 로그 확인
celery -A app.celery_app worker --loglevel=debug

# 등록된 태스크 목록 확인
celery -A app.celery_app inspect registered
```

### Python 모듈 import 에러

```bash
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```
