# AutoShorts 빠른 시작 가이드

## 1분 안에 시작하기

### 1. 환경 설정

```bash
# 프로젝트 루트에서
cp .env.example .env
```

`.env` 파일을 열고 최소 설정:
```bash
# OpenAI API (필수 - 스토리 생성용)
OPENAI_API_KEY=sk-proj-your_key_here

# ComfyUI 주소 (이미지 생성용)
COMFY_URL=http://localhost:8188

# ElevenLabs API (TTS/음성 생성용)
ELEVENLABS_API_KEY=sk_your_key_here

# Provider 설정
IMAGE_PROVIDER=comfyui
TTS_PROVIDER=elevenlabs
MUSIC_PROVIDER=elevenlabs
```

> **참고**: ElevenLabs API 키 설정 가이드는 [ELEVENLABS_FIX.md](ELEVENLABS_FIX.md) 참조

### 2. 백엔드 실행 (3개 터미널)

**터미널 1: Redis**
```bash
cd backend
docker-compose up -d redis
```

**터미널 2: Celery Worker**
```bash
cd backend
#python -m venv kvenv
source kvenv/bin/activate
pip install -r requirements.txt
celery -A app.celery_app worker --loglevel=info --pool=solo
```

**터미널 3: FastAPI**
```bash
cd backend
source kvenv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 3. 프론트엔드 실행

```bash
cd frontend
npm install  # 또는 pnpm install
npm run dev
```

브라우저에서 http://localhost:5173 접속

### 4. ComfyUI 준비 (이미지 생성용)

ComfyUI를 별도로 실행하거나 없으면 stub 모드로 테스트 가능.

```bash
# ComfyUI 실행 예시 (별도 설치 필요)
cd /path/to/ComfyUI
python main.py --listen 0.0.0.0 --port 8188
```

### 5. 첫 숏츠 생성

1. 프론트엔드에서 입력:
   - 모드: 스토리텔링
   - 프롬프트: "우주를 여행하는 고양이"
   - 컷 수: 3

2. "숏츠 생성 시작" 클릭

3. 진행 상황 실시간 모니터링

4. 완료 후 영상 재생/다운로드

## 테스트

### 간단한 모듈 테스트
```bash
# ElevenLabs TTS 테스트
python test_tts_simple.py

# 전체 모듈 테스트 (Jupyter 노트북)
jupyter notebook simple_test.ipynb
```

### API 키 검증
```bash
python verify_api_key.py
```

## 문제 해결

### Redis 연결 안 됨
```bash
docker ps  # Redis 확인
docker-compose restart redis
```

### Celery worker 에러
```bash
# 로그 확인
celery -A app.celery_app worker --loglevel=debug
```

### ComfyUI 없을 때
ComfyUI 없이도 전체 플로우 테스트 가능 (placeholder 이미지 생성)

### ElevenLabs TTS 에러
자세한 트러블슈팅은 [ELEVENLABS_FIX.md](ELEVENLABS_FIX.md) 참조

## 다음 단계

- [상세 README](README.md)
- [API 문서](docs/API.md)
- [워크플로 설명](docs/WORKFLOW.md)
