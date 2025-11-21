# Kurz AI Studio

## LLM Agent 기반 AI 숏폼 영상 자동 제작 서비스

Kurz AI Studio는 사용자 프롬프트를 입력받아 스토리 기획, 이미지 생성, 음성 합성, 배경음악 작곡, 영상 합성까지 완전 자동으로 수행하는 AI 기반 숏폼 영상 제작 파이프라인입니다.

**[데모 영상 보기](https://youtu.be/9BYbdmK_lzg)**

---

## 목차

- [프로젝트 개요](#프로젝트-개요)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [시작하기](#시작하기)
- [프로젝트 구조](#프로젝트-구조)
- [워크플로우](#워크플로우)
- [모드별 특징](#모드별-특징)
- [최신 업데이트](#최신-업데이트)
- [문서화](#문서화)

---

## 프로젝트 개요

### 주제
**LLM Agent 기반 AI 숏폼 영상 자동 제작 서비스**

### 배경
- 숏폼 콘텐츠 수요 급증: YouTube Shorts, Instagram Reels, TikTok 등
- 영상 제작에 필요한 기획, 디자인, 편집, 성우, 음악 작업의 시간/비용 부담
- Gemini, ElevenLabs 등 생성형 AI 기술의 발전

### 핵심 목표
1. **프롬프트 → 완성 영상** 원스톱 자동화
2. **다중 Agent 협업** 구조: 기획자 → 디자이너, 작곡가, 성우 → 감독 → QA
3. **3가지 모드 지원**: Story Mode (캐릭터 중심), General Mode (일반 영상), Ad Mode (광고)
4. **확장 가능한 아키텍처**: 모듈형 설계 + Celery 비동기 처리
5. **사용자 인증 및 데이터 관리**: PostgreSQL 기반 멀티 유저 지원

---

## 주요 기능

~~### 1. Story Mode (스토리 모드)~~
- ~~사용자가 캐릭터를 정의하고 스토리 진행~~
- ~~캐릭터 초상화(2:3) + 배경 이미지(9:16) 분리 렌더링~~
- ~~배경 투명화(rembg) 적용~~
- ~~캐릭터별 음성, 표정, 포즈 제어~~

### 2. General Mode (일반 모드)
- 프롬프트만으로 자동 시나리오 생성
- 정방형(1:1, 1080x1080) 통합 이미지 생성
- 백색 배경 + 투명화 없음
- 간결한 스키마로 빠른 생성
- AI 기반 프롬프트 향상 기능

### 3. Ad Mode (광고 모드)
- 제품/서비스 홍보용 영상 생성
- General Mode와 동일한 파이프라인
- 광고 특화 프롬프트 엔지니어링

### 4. 자동화된 Asset 생성
- **이미지**: Google Gemini Flash 2.5 Image (nanobanana)
- **음성**: ElevenLabs TTS (한국어 지원)
- **배경음악**: ElevenLabs Sound Effects
- **영상 합성**: FFmpeg 기반 고속 렌더링 (9:16 세로형, 30fps)

### 5. 사용자 관리 및 인증
- JWT 기반 사용자 인증
- PostgreSQL 데이터베이스로 사용자/프로젝트 관리
- 사용자별 영상 생성 이력 추적
- 소유권 기반 접근 제어

### 6. QA Agent
- 생성된 영상 자동 검수
- 오디오/비디오 품질 체크
- 실패 시 자동 재생성 로직

---

## 기술 스택

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Task Queue**: Celery + Redis (gevent pool, concurrency=10)
- **Database**: PostgreSQL 16 + SQLAlchemy 2.0 (async)
- **Migration**: Alembic
- **Authentication**: JWT (python-jose)
- **LLM**: Google Gemini 2.5 Flash
- **Image Generation**: Google Gemini Flash 2.0 Experimental (Imagen 3)
- **TTS**: ElevenLabs API
- **Music**: ElevenLabs Sound Effects
- **Video Rendering**: FFmpeg (하드웨어 가속 지원)
- **State Management**: Redis (FSM 저장)
- **Background Removal**: rembg (U2Net)

### Frontend
- **Framework**: React 18 + TypeScript + Vite
- **UI**: Tailwind CSS
- **State Management**: React Context API
- **Authentication**: JWT Token 기반
- **Real-time**: WebSocket (progress updates)
- **Routing**: React Router v6

### Infrastructure
- **Database**: PostgreSQL 16
- **Queue Broker**: Redis 7
- **Storage**: Local filesystem (app/data/outputs)
- **Video Codec**: H.264 (libx264)
- **Audio Codec**: AAC (192kbps)

---

## 🚀 시작하기

### 필수 요구사항
- **Python 3.11 이상**
- **Node.js 18 이상**
- **PostgreSQL 16** (데이터베이스)
- **Redis Server** (작업 큐)
- **FFmpeg** (영상 렌더링)
- **API Keys**:
  - Google Gemini API Key (2.5 Flash + Flash 2.0 Experimental)
  - ElevenLabs API Key (TTS + Music)

### 설치 및 실행

#### 1. 저장소 클론
```bash
git clone <repository_url>
cd Kurz_Studio_AI
```

#### 2. PostgreSQL 데이터베이스 설정
```bash
# macOS (Homebrew)
brew install postgresql@16
brew services start postgresql@16

# 데이터베이스 생성
createdb kurz_studio_ai

# 또는 psql로 직접 생성
psql postgres
CREATE DATABASE kurz_studio_ai;
\q
```

#### 3. Backend 설정
```bash
cd backend

# 가상환경 생성 (kvenv 이름 사용)
python -m venv kvenv
source kvenv/bin/activate  # Windows: kvenv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 및 데이터베이스 URL 입력
```

**.env 예시**:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/kurz_studio_ai

# API Keys
GEMINI_API_KEY=your_gemini_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# JWT Secret (랜덤 생성 권장)
SECRET_KEY=your-secret-key-here

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

#### 4. 데이터베이스 마이그레이션
```bash
cd backend
source kvenv/bin/activate

# Alembic 마이그레이션 실행
alembic upgrade head
```

#### 5. FFmpeg 설치
```bash
# macOS (Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg
```

#### 6. Redis 실행
```bash
# macOS (Homebrew)
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

#### 7. Celery Worker 실행
```bash
# Terminal 1: Celery Worker
cd backend
source kvenv/bin/activate
celery -A app.celery_app worker --loglevel=info --pool=gevent --concurrency=10
```

#### 8. FastAPI 서버 실행
```bash
# Terminal 2: Backend Server
cd backend
source kvenv/bin/activate
uvicorn app.main:app --reload --port 8000
```

#### 9. Frontend 실행
```bash
# Terminal 3: Frontend Dev Server
cd frontend
npm install
npm run dev
```

#### 10. 접속
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database**: PostgreSQL on port 5432

---

## 프로젝트 구조

```
Kurz_Studio_AI/
├── backend/
│   ├── alembic/                       # Database migrations
│   │   ├── versions/                  # Migration scripts
│   │   └── env.py                     # Alembic config
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── config.py                  # Environment config
│   │   ├── celery_app.py              # Celery configuration
│   │   ├── database.py                # SQLAlchemy setup
│   │   ├── models/                    # SQLAlchemy models
│   │   │   ├── user.py                # User model
│   │   │   └── run.py                 # Run model
│   │   ├── routers/                   # API routers
│   │   │   ├── auth.py                # Authentication endpoints
│   │   │   └── runs.py                # Run management endpoints
│   │   ├── schemas/                   # Pydantic schemas
│   │   │   ├── user.py                # User schemas
│   │   │   └── run_spec.py            # Run specification schemas
│   │   ├── orchestrator/
│   │   │   └── fsm.py                 # Finite State Machine
│   │   ├── tasks/
│   │   │   ├── plan.py                # 기획자 Agent (Plot 생성)
│   │   │   ├── designer.py            # 디자이너 Agent (이미지 생성)
│   │   │   ├── composer.py            # 작곡가 Agent (BGM 생성)
│   │   │   ├── voice.py               # 성우 Agent (TTS)
│   │   │   ├── director.py            # 감독 Agent (FFmpeg 렌더링)
│   │   │   └── qa.py                  # QA Agent (품질 검수)
│   │   ├── providers/
│   │   │   ├── llm/                   # Gemini 2.5 Flash client
│   │   │   ├── image/                 # Gemini Flash 2.0 image generation
│   │   │   ├── tts/                   # ElevenLabs TTS
│   │   │   └── music/                 # ElevenLabs Music
│   │   ├── utils/
│   │   │   ├── plot_generator.py      # LLM 기반 plot 생성
│   │   │   ├── json_converter.py      # plot.json → layout.json 변환
│   │   │   ├── ffmpeg_renderer.py     # FFmpeg 기반 영상 렌더링
│   │   │   ├── auth.py                # JWT 인증 유틸리티
│   │   │   ├── security.py            # 비밀번호 해싱
│   │   │   └── progress.py            # 진행률 publish
│   │   └── data/
│   │       └── outputs/{run_id}/      # 생성된 파일 저장
│   │           ├── characters.json    # 캐릭터 정의
│   │           ├── plot.json          # LLM 생성 시나리오
│   │           ├── layout.json        # 렌더링용 레이아웃
│   │           ├── images/            # 생성된 이미지
│   │           ├── audio/             # TTS + BGM
│   │           ├── frames/            # FFmpeg 렌더링 프레임
│   │           └── final_video.mp4    # 최종 영상
│   ├── requirements.txt
│   ├── alembic.ini                    # Alembic configuration
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Main app component
│   │   ├── main.tsx                   # Entry point
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx        # Authentication context
│   │   ├── components/
│   │   │   ├── AuthModal.tsx          # Login/Register modal
│   │   │   ├── HeroChat.tsx           # Chat interface
│   │   │   ├── RunForm.tsx            # Video generation form
│   │   │   ├── RunStatus.tsx          # Progress display
│   │   │   ├── PlotReviewModal.tsx    # Plot review modal
│   │   │   ├── LayoutReviewModal.tsx  # Layout review modal
│   │   │   └── Library.tsx            # User video library
│   │   ├── api/
│   │   │   └── client.ts              # API client
│   │   └── styles/
│   │       └── globals.css            # Global styles
│   ├── package.json
│   └── vite.config.ts
│
├── voices.json                        # ElevenLabs 음성 설정
├── README.md
└── .gitignore
```

---

## 워크플로우

### FSM 상태 전이도
```
IDLE
  ↓ (POST /api/runs)
PLOT_GENERATION (기획자)
  ↓
PLOT_REVIEW (사용자 검토)
  ↓ (POST /api/v1/runs/{run_id}/plot-confirm)
ASSET_GENERATION (디자이너 + 작곡가 + 성우 병렬 처리)
  ↓
RENDERING (감독 - FFmpeg 렌더링)
  ↓
QA (품질 검수)
  ↓ (통과) / ↺ (실패 시 재생성)
END
```

### Agent별 역할

| Agent | 역할 | 입력 | 출력 |
|-------|------|------|------|
| **기획자** (plan.py) | 시나리오 생성 | prompt, mode, num_cuts | characters.json, plot.json, layout.json |
| **디자이너** (designer.py) | 이미지 생성 | layout.json | images/*.png (Gemini Imagen 3) |
| **작곡가** (composer.py) | 배경음악 생성 | layout.json | audio/global_bgm.mp3 (ElevenLabs) |
| **성우** (voice.py) | 음성 합성 | layout.json, characters.json | audio/{scene}_{line}.mp3 (ElevenLabs TTS) |
| **감독** (director.py) | 영상 합성 | layout.json + assets | final_video.mp4 (FFmpeg) |
| **QA** (qa.py) | 품질 검수 | final_video.mp4 | QA report (통과/재생성) |

---

## 모드별 특징

### General Mode / Ad Mode
**Schema (plot.json)**:
```json
{
  "title": "영상 제목",
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
- `image_prompt=""`일 경우 이전 이미지 재사용
- `bgm_prompt`로 상세한 BGM 생성
- 서술 말투 및 플롯 구조 커스터마이징 지원

---

## 최신 업데이트

### v0.2 - 데이터베이스 및 FFmpeg 통합 (2025-01)

#### 1. 사용자 인증 시스템
- JWT 기반 인증 구현
- 회원가입/로그인 기능
- 사용자별 영상 생성 이력 관리
- 소유권 기반 접근 제어

#### 2. PostgreSQL 데이터베이스 통합
- **User 모델**: 사용자 정보 저장
  - `id`, `username`, `email`, `hashed_password`
  - `created_at`, `updated_at`
- **Run 모델**: 영상 생성 이력 저장
  - `run_id`, `user_id`, `mode`, `prompt`
  - `state`, `progress`, `video_url`
  - `num_cuts`, `num_characters`
- SQLAlchemy 2.0 async 엔진 사용
- Alembic 마이그레이션 관리

#### 3. FFmpeg 기반 고속 렌더링
- MoviePy → FFmpeg 전환으로 **10배 이상 성능 향상**
- 하드웨어 가속 지원 (H.264 인코딩)
- 프레임 단위 렌더링으로 메모리 효율성 개선
- Title block + Subtitle 고품질 렌더링
- 한글 폰트 지원 (Paperlogy)

#### 4. 프롬프트 향상 기능
- Gemini 기반 프롬프트 자동 향상
- 서술 말투 선택 (격식형, 친근한반말, 진지한나레이션 등)
- 플롯 구조 선택 (기승전결, 고구마사이다, 3막구조 등)

#### 5. UI/UX 개선
- 사용자 라이브러리 기능
- 실시간 진행률 표시 개선
- Plot/Layout 검수 모달
- 애니메이션 효과 추가

---

## 문서화

### API 문서
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 주요 엔드포인트

#### 인증
- `POST /api/auth/register` - 회원가입
- `POST /api/auth/login` - 로그인
- `GET /api/auth/me` - 현재 사용자 정보

#### 영상 생성
- `POST /api/runs` - 새로운 영상 생성 시작 (인증 필요)
- `GET /api/runs/{run_id}` - 진행 상태 조회
- `GET /api/v1/runs/{run_id}/plot` - Plot JSON 조회
- `POST /api/v1/runs/{run_id}/plot-confirm` - Plot 확인 및 다음 단계 진행 (인증 필요)

#### 사용자 라이브러리
- `GET /api/v1/users/me/runs` - 내 영상 목록 조회 (인증 필요)

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
- `metadata`: 추가 설정 (title, bgm_prompt, review_mode)

### 환경 변수 (.env)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kurz_studio_ai

# JWT
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# LLM
GEMINI_API_KEY=AI...

# TTS
ELEVENLABS_API_KEY=sk_...

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Server
API_HOST=0.0.0.0
API_PORT=8000
ENV=dev
```

---

## 참고 자료

### 기술 문서
- [Google Gemini API](https://ai.google.dev/gemini-api/docs) - LLM & Image Generation
- [ElevenLabs API](https://elevenlabs.io/docs) - TTS & Music
- [FastAPI](https://fastapi.tiangolo.com/) - Backend Framework
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) - ORM
- [Alembic](https://alembic.sqlalchemy.org/) - Database Migrations
- [Celery](https://docs.celeryq.dev/) - Task Queue
- [FFmpeg](https://ffmpeg.org/documentation.html) - Video Rendering
- [PostgreSQL](https://www.postgresql.org/docs/) - Database

### 프로젝트 구조 설계
- **Finite State Machine (FSM)**: 워크플로우 상태 관리
- **Celery Chord Pattern**: 병렬 작업 → 콜백 구조
- **Multi-Agent Orchestration**: 역할 분담형 Agent 설계
- **Schema Validation**: Pydantic을 활용한 데이터 검증
- **JWT Authentication**: 토큰 기반 인증
- **Async SQLAlchemy**: 비동기 데이터베이스 처리

---

## 최종 산출물

### 1. 완성된 영상
- **포맷**: MP4 (H.264 video + AAC audio)
- **해상도**: 1080x1920 (9:16 세로형)
- **프레임레이트**: 30fps
- **비트레이트**: Video ~2Mbps, Audio 192kbps
- **저장 위치**: `backend/app/data/outputs/{run_id}/final_video.mp4`

### 2. 중간 Artifacts
- `characters.json`: 캐릭터 정의
- `plot.json`: LLM 생성 시나리오
- `plot.csv`: 사용자 검수용 CSV
- `layout.json`: 렌더링용 레이아웃
- `images/`: 생성된 이미지 파일들
- `audio/`: TTS + BGM 파일들
- `frames/`: FFmpeg 렌더링 프레임 이미지

### 3. 데이터베이스 레코드
- User 테이블: 사용자 정보
- Run 테이블: 영상 생성 이력
  - 상태, 진행률, 결과 URL 저장
  - 사용자별 생성 이력 추적

---

## 알려진 이슈

1. **Gemini API Rate Limit**: 이미지 생성 시 429 에러 발생 가능 → 재시도 로직 구현됨
2. **ElevenLabs 한국어 발음**: 일부 단어 부정확 → 텍스트 전처리 필요
3. **FFmpeg 메모리**: 매우 긴 영상(50+ 씬) 생성 시 메모리 사용량 증가 가능

---

## 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'feat: Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 라이선스

This project is licensed under the MIT License.

---

## Contact

프로젝트 관련 문의: [이메일 또는 이슈 트래커]

**Project Link**: [GitHub Repository URL]
