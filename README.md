# Kurz AI Studio 🎬

## LLM Agent 기반 AI 숏폼 영상 자동 제작 서비스

Kurz AI Studio는 사용자 프롬프트를 입력받아 스토리 기획, 이미지 생성, 음성 합성, 배경음악 작곡, 영상 합성까지 완전 자동으로 수행하는 AI 기반 숏폼 영상 제작 파이프라인입니다.

---

## 📋 목차

- [프로젝트 개요](#프로젝트-개요)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [시작하기](#시작하기)
- [프로젝트 구조](#프로젝트-구조)
- [워크플로우](#워크플로우)
- [모드별 특징](#모드별-특징)
- [Rules & Guidelines](#rules--guidelines)
- [문서화](#문서화)

---

## 🎯 프로젝트 개요

### 주제
**LLM Agent 기반 AI 숏폼 영상 자동 제작 서비스**

### 배경
- 숏폼 콘텐츠 수요 급증: YouTube Shorts, Instagram Reels, TikTok 등
- 영상 제작에 필요한 기획, 디자인, 편집, 성우, 음악 작업의 시간/비용 부담
- GPT-4, Gemini, ElevenLabs 등 생성형 AI 기술의 발전

### 핵심 목표
1. **프롬프트 → 완성 영상** 원스톱 자동화
2. **다중 Agent 협업** 구조: 기획자 → 디자이너, 작곡가, 성우 → 감독 → QA
3. **3가지 모드 지원**: Story Mode (캐릭터 중심), General Mode (일반 영상), Ad Mode (광고)
4. **확장 가능한 아키텍처**: 모듈형 설계 + Celery 비동기 처리

---

## ✨ 주요 기능

### 1. Story Mode (스토리 모드)
- 사용자가 캐릭터를 정의하고 스토리 진행
- 캐릭터 초상화(2:3) + 배경 이미지(9:16) 분리 렌더링
- 배경 투명화(rembg) 적용
- 캐릭터별 음성, 표정, 포즈 제어

### 2. General Mode (일반 모드)
- 프롬프트만으로 자동 시나리오 생성
- 정방형(1:1, 1080x1080) 통합 이미지 생성
- 백색 배경 + 투명화 없음
- 간결한 스키마로 빠른 생성

### 3. Ad Mode (광고 모드)
- 제품/서비스 홍보용 영상 생성
- General Mode와 동일한 파이프라인
- 광고 특화 프롬프트 엔지니어링

### 4. 자동화된 Asset 생성
- **이미지**: Gemini Flash 2.0 Experimental
- **음성**: ElevenLabs TTS (한국어 지원)
- **배경음악**: ElevenLabs Sound Effects / Mubert
- **영상 합성**: MoviePy (9:16 세로형, 30fps)

### 5. QA Agent
- 생성된 영상 자동 검수
- 오디오/비디오 품질 체크
- 재생성 로직 (최대 3회)

---

## 🛠 기술 스택

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Task Queue**: Celery + Redis
- **LLM**: OpenAI GPT-4o-mini
- **Image Generation**: Google Gemini Flash 2.0 Experimental
- **TTS**: ElevenLabs API
- **Music**: ElevenLabs Sound Effects / Mubert
- **Video**: MoviePy
- **State Management**: Redis (FSM 저장)
- **Background Removal**: rembg (U2Net)

### Frontend
- **Framework**: React + TypeScript + Vite
- **UI**: Tailwind CSS
- **State Management**: React Hooks
- **Real-time**: WebSocket (progress updates)

### Infrastructure
- **Containerization**: Docker (optional)
- **Storage**: Local filesystem (app/data/outputs)
- **Queue Broker**: Redis

---

## 🚀 시작하기

### 필수 요구사항
- Python 3.11 이상
- Node.js 18 이상
- Redis Server
- API Keys:
  - OpenAI API Key (GPT-4o-mini)
  - Google Gemini API Key (Flash 2.0 Experimental)
  - ElevenLabs API Key (TTS + Music)
  - Mubert License (optional, BGM 폴백용)

### 설치 및 실행

#### 1. 저장소 클론
```bash
git clone <repository_url>
cd Kurz_Studio_AI
```

#### 2. Backend 설정
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

#### 3. Redis 실행
```bash
# macOS (Homebrew)
brew services start redis

# Linux
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

#### 4. Celery Worker 실행
```bash
# Terminal 1: Celery Worker
cd backend
source kvenv/bin/activate
celery -A app.celery_app worker --loglevel=info --pool=gevent --concurrency=10
```

#### 5. FastAPI 서버 실행
```bash
# Terminal 2: Backend Server
cd backend
source kvenv/bin/activate
uvicorn app.main:app --reload --port 8000
```

#### 6. Frontend 실행
```bash
# Terminal 3: Frontend Dev Server
cd frontend
npm install
npm run dev
```

#### 7. 접속
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 📁 프로젝트 구조

```
Kurz_Studio_AI/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── config.py                  # Environment config
│   │   ├── celery_app.py              # Celery configuration
│   │   ├── orchestrator/
│   │   │   └── fsm.py                 # Finite State Machine
│   │   ├── tasks/
│   │   │   ├── plan.py                # 기획자 Agent (Plot 생성)
│   │   │   ├── designer.py            # 디자이너 Agent (이미지 생성)
│   │   │   ├── composer.py            # 작곡가 Agent (BGM 생성)
│   │   │   ├── voice.py               # 성우 Agent (TTS)
│   │   │   ├── director.py            # 감독 Agent (영상 합성)
│   │   │   └── qa.py                  # QA Agent (품질 검수)
│   │   ├── providers/
│   │   │   ├── llm/                   # OpenAI GPT-4 client
│   │   │   ├── image/                 # Gemini image generation
│   │   │   ├── tts/                   # ElevenLabs TTS
│   │   │   └── music/                 # ElevenLabs Music / Mubert
│   │   ├── utils/
│   │   │   ├── plot_generator.py      # LLM 기반 plot 생성
│   │   │   ├── json_converter.py      # plot.json → layout.json 변환
│   │   │   └── progress.py            # 진행률 publish
│   │   └── data/
│   │       └── outputs/{run_id}/      # 생성된 파일 저장
│   │           ├── characters.json    # 캐릭터 정의
│   │           ├── plot.json          # LLM 생성 시나리오
│   │           ├── layout.json        # 렌더링용 레이아웃
│   │           ├── images/            # 생성된 이미지
│   │           ├── audio/             # TTS + BGM
│   │           └── final_video.mp4    # 최종 영상
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Main app component
│   │   ├── components/
│   │   │   ├── VideoRequest.tsx       # 영상 생성 요청 UI
│   │   │   ├── RunStatus.tsx          # 진행 상태 표시
│   │   │   └── VideoPlayer.tsx        # 영상 재생
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── voices.json                        # ElevenLabs 음성 설정
├── README.md
└── .gitignore
```

---

## 🔄 워크플로우

### FSM 상태 전이도
```
IDLE
  ↓ (POST /v1/runs)
PLOT_GENERATION (기획자)
  ↓
ASSET_GENERATION (디자이너 + 작곡가 + 성우 병렬 처리)
  ↓
VIDEO_COMPOSITION (감독)
  ↓
QA (품질 검수)
  ↓ (통과) / ↺ (실패 시 재생성)
END
```

### Agent별 역할

| Agent | 역할 | 입력 | 출력 |
|-------|------|------|------|
| **기획자** (plan.py) | 시나리오 생성 | prompt, mode, num_cuts | characters.json, plot.json, layout.json |
| **디자이너** (designer.py) | 이미지 생성 | layout.json | images/*.png (Gemini Flash 2.0) |
| **작곡가** (composer.py) | 배경음악 생성 | layout.json | audio/global_bgm.mp3 (ElevenLabs/Mubert) |
| **성우** (voice.py) | 음성 합성 | layout.json, characters.json | audio/{scene}_{line}.mp3 (ElevenLabs TTS) |
| **감독** (director.py) | 영상 합성 | layout.json + assets | final_video.mp4 (MoviePy) |
| **QA** (qa.py) | 품질 검수 | final_video.mp4 | QA report (통과/재생성) |

---

## 🎨 모드별 특징

### Story Mode
**Schema (plot.json)**:
```json
{
  "scenes": [
    {
      "scene_id": "scene_1",
      "char1_id": "char_1",
      "char1_expression": "happy",
      "char1_pose": "standing",
      "char1_pos": "center",
      "speaker": "char_1",
      "text": "안녕!",
      "background_img": "밝은 아침 배경",
      "duration_ms": 5000
    }
  ]
}
```

**특징**:
- 캐릭터 초상화(2:3, 512x768) + 배경(9:16, 1080x1920) 분리
- rembg로 캐릭터 배경 투명화
- 다크 배경(20, 20, 40)
- 캐릭터 표정/포즈/위치 제어

### General Mode / Ad Mode
**Schema (plot.json)**:
```json
{
  "bgm_prompt": "upbeat, cheerful, acoustic guitar",
  "scenes": [
    {
      "scene_id": "scene_1",
      "image_prompt": "귀여운 고양이가 웃고 있는 모습, 밝은 배경",
      "text": "안녕하세요!",
      "speaker": "char_1",
      "duration_ms": 5000
    }
  ]
}
```

**특징**:
- 정방형 이미지(1:1, 1080x1080) 통합 생성
- 백색 배경(255, 255, 255)
- 투명화 없음
- image_prompt=""일 경우 이전 이미지 재사용
- bgm_prompt로 상세한 BGM 생성

---

## 📐 Rules & Guidelines

### Git Flow
- **main**: 프로덕션 브랜치 (stable)
- **develop**: 개발 통합 브랜치
- **feature/xxx**: 기능 개발 브랜치
  - 예: `feature/story-mode-implementation`
  - 예: `feature/plot-refactoring`
- **hotfix/xxx**: 긴급 버그 수정

**브랜치 전략**:
1. `develop`에서 `feature/xxx` 브랜치 생성
2. 기능 개발 후 `develop`으로 PR/Merge
3. `develop` 테스트 완료 후 `main`으로 Merge

### Commit Message Convention
```
feat: 새로운 기능 추가
fix: 버그 수정
refactor: 코드 리팩토링
docs: 문서 수정
chore: 기타 작업 (의존성, 설정 등)
test: 테스트 추가/수정
```

**예시**:
```
feat: Add general mode image generation pipeline
fix: Fix race condition in asset generation
refactor: Update log messages to reflect JSON-only workflow
chore: Add test folders to gitignore
```

### 코드 스타일
- **Python**: PEP 8 준수, type hints 사용 권장
- **TypeScript**: ESLint + Prettier
- **Logging**: `logger.info(f"[{run_id}] message")` 형식 통일

---

## 📚 문서화

### API 문서
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 주요 데이터 구조

#### characters.json
```json
{
  "characters": [
    {
      "char_id": "char_1",
      "name": "윤아",
      "gender": "female",
      "age": 25,
      "appearance": "긴 검은 머리, 밝은 눈동자",
      "personality": "활발하고 긍정적인",
      "role": "주인공",
      "voice_id": "xi3rF0t7dg7uN2M0WUhr"
    }
  ]
}
```

#### layout.json (핵심 필드)
- `mode`: "story" | "general" | "ad"
- `characters`: 캐릭터 목록
- `scenes`: 장면별 이미지/텍스트/오디오 슬롯
- `timeline`: 전체 타임라인 정보
- `global_bgm`: 배경음악 메타데이터

### 환경 변수 (.env)
```bash
# LLM
OPENAI_API_KEY=sk-...

# Image Generation
GEMINI_API_KEY=AI...

# TTS
TTS_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=sk_...

# Music
MUBERT_LICENSE=your_license_key

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Seeds (재현성)
CHAR_SEED_BASE=12345
BG_SEED_BASE=54321
```

---

## 🎓 학습 자료

### 참고한 기술
- [OpenAI GPT-4 API](https://platform.openai.com/docs)
- [Google Gemini API](https://ai.google.dev/gemini-api/docs)
- [ElevenLabs TTS API](https://elevenlabs.io/docs)
- [Celery Documentation](https://docs.celeryq.dev/)
- [MoviePy Documentation](https://zulko.github.io/moviepy/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

### 프로젝트 구조 설계
- **Finite State Machine (FSM)**: 워크플로우 상태 관리
- **Celery Chord Pattern**: 병렬 작업 → 콜백 구조
- **Multi-Agent Orchestration**: 역할 분담형 Agent 설계
- **Schema Validation**: Pydantic을 활용한 데이터 검증

---

## 📦 최종 산출물

### 1. 완성된 영상
- 포맷: MP4 (H.264, AAC)
- 해상도: 1080x1920 (9:16 세로형)
- 프레임레이트: 30fps
- 저장 위치: `backend/app/data/outputs/{run_id}/final_video.mp4`

### 2. 중간 Artifacts
- `characters.json`: 캐릭터 정의
- `plot.json`: LLM 생성 시나리오
- `layout.json`: 렌더링용 레이아웃
- `images/`: 생성된 이미지 파일들
- `audio/`: TTS + BGM 파일들

### 3. QA Report
- 영상 길이, 해상도, 코덱 검증
- 오디오 싱크 체크
- 재생성 이력

---

## 🐛 알려진 이슈

1. **Gemini API Rate Limit**: 이미지 생성 시 429 에러 발생 가능 → 재시도 로직 구현됨
2. **ElevenLabs 한국어 발음**: 일부 단어 부정확 → 텍스트 전처리 필요
3. **MoviePy 메모리 사용량**: 긴 영상 생성 시 메모리 부족 가능 → 장면 단위 합성 권장

---

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'feat: Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 라이선스

This project is licensed under the MIT License.

---

## 👥 Contact

프로젝트 관련 문의: [이메일 또는 이슈 트래커]

**Project Link**: [GitHub Repository URL]
