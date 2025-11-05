# AutoShorts 테스팅 가이드

## 개요

이 문서는 AutoShorts의 각 모듈을 개별적으로 테스트하는 방법을 설명합니다.

---

## 테스트 환경 설정

### 1. 필수 소프트웨어

- Python 3.11+
- Redis Server
- Jupyter Notebook (선택)

### 2. API 키 준비

`.env` 파일을 프로젝트 루트에 생성하고 다음 키들을 설정하세요:

```bash
# 필수
OPENAI_API_KEY=sk-...                    # GPT-4o-mini (플롯 생성)
REDIS_URL=redis://localhost:6379         # Redis (Celery 브로커, FSM 저장소)
CELERY_BROKER_URL=redis://localhost:6379
CELERY_RESULT_BACKEND=redis://localhost:6379

# 선택 (없으면 Stub 모드로 동작)
COMFYUI_URL=http://localhost:8188        # ComfyUI (이미지 생성)
MUBERT_LICENSE=your_license_key          # Mubert (음악 생성)
ELEVENLABS_API_KEY=your_api_key          # ElevenLabs (음성 생성)

# 또는
PLAYHT_USER_ID=your_user_id              # PlayHT (ElevenLabs 대체)
PLAYHT_API_KEY=your_api_key
```

### 3. API 키 발급 방법

#### OpenAI (필수)
1. https://platform.openai.com/signup 에서 계정 생성
2. API Keys 섹션에서 새 키 생성
3. 요금: GPT-4o-mini는 매우 저렴 (1M 토큰당 $0.15)

#### ComfyUI (선택)
1. https://github.com/comfyanonymous/ComfyUI 에서 설치
2. `python main.py` 실행 (기본 포트 8188)
3. 로컬에서 무료 사용 가능 (GPU 필요)

#### Mubert (선택)
1. https://mubert.com/render/api 에서 계정 생성
2. License 키 발급
3. 요금: 무료 플랜 제공, 유료는 월 $14~

#### ElevenLabs (선택)
1. https://elevenlabs.io 에서 계정 생성
2. Profile → API Key에서 키 발급
3. 요금: 무료 10,000 문자/월, 유료는 월 $5~

#### PlayHT (선택, ElevenLabs 대체)
1. https://play.ht 에서 계정 생성
2. API Access에서 User ID, API Key 발급
3. 요금: 무료 12,500 단어, 유료는 월 $31~

### 4. 서비스 실행

```bash
# 1. Redis 서버 실행
redis-server --daemonize yes

# 2. ComfyUI 실행 (선택)
cd /path/to/ComfyUI
python main.py

# 3. 가상환경 활성화
cd /path/to/Kurz_Studio_AI
source kvenv/bin/activate  # 또는 Windows: kvenv\Scripts\activate

# 4. 패키지 설치
pip install -r backend/requirements.txt

# 5. Jupyter Notebook 실행 (선택)
jupyter notebook test_modules.ipynb
```

---

## Jupyter Notebook 테스트

### 실행 방법

```bash
jupyter notebook test_modules.ipynb
```

### 테스트 순서

1. **환경 설정** (셀 0-1)
   - Python path 설정
   - API 키 로드 및 확인

2. **플롯 생성** (셀 2-5)
   - GPT 프롬프트 확인
   - CSV 생성 (GPT-4o-mini)
   - JSON 변환
   - 자막 포맷 확인 (text_type → 큰따옴표)

3. **이미지 생성** (셀 6-7)
   - ComfyUI 프롬프트 확인
   - 캐릭터/배경 이미지 생성
   - Seed 기반 일관성 확인

4. **음악 생성** (셀 8-9)
   - Mubert 파라미터 확인
   - 배경음악 생성
   - 오디오 재생

5. **음성 생성** (셀 10-11)
   - TTS 프롬프트 확인
   - 대사 음성 생성
   - 감정 표현 확인

6. **통합 테스트** (셀 12-13)
   - 모든 씬의 에셋 생성
   - JSON 업데이트
   - 결과 파일 저장

7. **프롬프트 분석** (셀 14)
   - 생성된 모든 프롬프트 확인
   - 최적화 포인트 확인

---

## 수동 테스트 (Python 스크립트)

Jupyter 없이 Python 스크립트로 테스트하려면:

```bash
# 플롯 생성 테스트
python -c "
import sys
sys.path.insert(0, 'backend')
from app.utils.csv_to_json import generate_csv_from_prompt
csv_path = generate_csv_from_prompt(
    run_id='test_20251105_1430_테스트',
    prompt='우주를 여행하는 고양이',
    num_characters=2,
    num_cuts=5,
    mode='story'
)
print(f'CSV 생성: {csv_path}')
"
```

---

## 단위 테스트 (pytest)

개별 함수/클래스를 테스트하려면:

```bash
# 테스트 파일 생성 (예시)
cat > backend/tests/test_csv_to_json.py << 'EOF'
import pytest
from app.utils.csv_to_json import generate_csv_from_prompt, csv_to_json

def test_csv_generation():
    csv_path = generate_csv_from_prompt(
        run_id="test_run",
        prompt="테스트 프롬프트",
        num_characters=1,
        num_cuts=3,
        mode="story"
    )
    assert csv_path.exists()

def test_json_conversion():
    # CSV → JSON 변환 테스트
    pass
EOF

# pytest 실행
cd backend
pytest tests/ -v
```

---

## Stub 모드 테스트

API 키 없이 전체 파이프라인을 테스트하려면:

```bash
# .env에서 API 키 주석 처리
# COMFYUI_URL=...
# MUBERT_LICENSE=...
# ELEVENLABS_API_KEY=...

# FastAPI 서버 실행
cd backend
uvicorn app.main:app --reload

# Celery Worker 실행 (다른 터미널)
celery -A app.celery_app worker --loglevel=info

# 프론트엔드 실행 (또 다른 터미널)
cd frontend
npm start
```

**Stub 모드 동작**:
- ComfyUI 없음 → 더미 이미지 생성 (단색 PNG)
- Mubert 없음 → 무음 MP3 생성
- ElevenLabs/PlayHT 없음 → 무음 MP3 생성

**장점**: API 비용 없이 전체 워크플로 테스트 가능

---

## 통합 테스트 (전체 파이프라인)

### 1. 서비스 시작

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: FastAPI
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 3: Celery
celery -A app.celery_app worker --loglevel=info

# Terminal 4: Frontend
cd frontend
npm start
```

### 2. API 테스트

```bash
# Run 생성
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "story",
    "prompt": "우주를 여행하는 고양이",
    "num_characters": 2,
    "num_cuts": 5,
    "art_style": "파스텔 수채화",
    "music_genre": "ambient"
  }'

# 응답:
# {"run_id":"20251105_1430_우주여행고양이","state":"PLOT_GENERATION","progress":0.0,...}

# 상태 확인
curl http://localhost:8000/api/runs/20251105_1430_우주여행고양이

# WebSocket 연결 (브라우저 콘솔)
const ws = new WebSocket('ws://localhost:8000/ws/20251105_1430_우주여행고양이')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
```

### 3. 진행도 모니터링

```bash
# Redis Pub/Sub 모니터링
redis-cli
> SUBSCRIBE autoshorts:progress
```

### 4. 결과 확인

```bash
# 생성된 파일 확인
ls -lh app/data/outputs/20251105_1430_우주여행고양이/

# 예상 파일:
# - plot.csv              (시나리오)
# - layout.json           (레이아웃)
# - scene_1_center.png    (이미지)
# - scene_1_line_1.mp3    (음성)
# - global_bgm.mp3        (배경음악)
# - final_video.mp4       (최종 영상)
```

---

## 트러블슈팅

### Q1. "ModuleNotFoundError: No module named 'app'"

**해결**:
```bash
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

또는 Jupyter에서:
```python
import sys
sys.path.insert(0, 'backend')
```

### Q2. "Connection refused (Redis)"

**해결**:
```bash
# Redis 실행 확인
redis-cli ping
# 응답: PONG

# 실행되지 않으면
redis-server --daemonize yes
```

### Q3. "OpenAI API error: Incorrect API key"

**해결**:
```bash
# .env 파일 확인
cat .env | grep OPENAI

# 환경 변수 재로드
python -c "from dotenv import load_dotenv; load_dotenv(); from app.config import settings; print(settings.OPENAI_API_KEY[:10])"
```

### Q4. "ComfyUI connection timeout"

**해결**:
```bash
# ComfyUI 실행 확인
curl http://localhost:8188/system_stats

# 실행되지 않으면 Stub 모드 사용
# .env에서 COMFYUI_URL 주석 처리
```

### Q5. "Celery task not found"

**해결**:
```bash
# Celery worker 재시작
pkill -f "celery worker"
celery -A app.celery_app worker --loglevel=info

# 등록된 태스크 확인
celery -A app.celery_app inspect registered
```

---

## 성능 벤치마크

### 예상 소요 시간 (5개 씬 기준)

| 단계 | 소요 시간 | 비용 (예상) |
|------|----------|-----------|
| 플롯 생성 (GPT-4o-mini) | 3-5초 | $0.001 |
| 이미지 생성 (ComfyUI) | 10-30초/장 | 무료 (로컬) |
| 음악 생성 (Mubert) | 5-10초 | $0 (무료 플랜) |
| 음성 생성 (ElevenLabs) | 2-5초/대사 | $0 (무료 플랜) |
| 영상 합성 (MoviePy) | 10-20초 | 무료 |
| **전체** | **2-3분** | **< $0.01** |

**Stub 모드**: 30초 이내 (API 호출 없음)

---

## 다음 단계

1. **기본 테스트 완료 후**:
   - 프롬프트 최적화 (이미지 품질 개선)
   - 음성 감정 표현 조정
   - 영상 전환 효과 추가

2. **프로덕션 배포 전**:
   - 에러 처리 강화
   - 재시도 로직 테스트
   - QA 검수 기준 조정

3. **확장 기능**:
   - 다중 캐릭터 대화
   - 카메라 앵글 제어
   - 실시간 스타일 변경

---

**작성일**: 2025-11-05
**버전**: 1.0
