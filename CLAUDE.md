# Kurz AI Studio 🎬

## LLM Agent 기반 AI 숏폼 영상 자동 제작 서비스

Kurz AI Studio는 사용자 프롬프트를 입력받아 스토리 기획, 이미지 생성, 음성 합성, 배경음악 작곡, 영상 합성까지 완전 자동으로 수행하는 AI 기반 숏폼 영상 제작 파이프라인입니다.

---

## 📋 목차

- [프로젝트 개요](#프로젝트-개요)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [최근 업데이트](#최근-업데이트)
- [시작하기](#시작하기)
- [프로젝트 구조](#프로젝트-구조)
- [워크플로우](#워크플로우)
- [모드별 특징](#모드별-특징)
- [Rules & Guidelines](#rules--guidelines)

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
- **자막**: 흰색 글자 + 검은색 테두리 (어두운 배경에 최적화)

### 2. General Mode (일반 모드) ✨ NEW
- 프롬프트만으로 자동 시나리오 생성
- **정방형(1:1, 1080x1080) 통합 이미지** 생성
- **완전한 흰색 배경(#FFFFFF)** + 투명화 없음
- **검은색 자막 + 흰색 테두리** (흰 배경에 최적화)
- **자동 줄바꿈**: 화면 너비의 90% 내에서 자동 텍스트 랩핑
- 간결한 스키마로 빠른 생성

### 3. Ad Mode (광고 모드)
- 제품/서비스 홍보용 영상 생성
- General Mode와 동일한 파이프라인
- 광고 특화 프롬프트 엔지니어링

### 4. 자동화된 Asset 생성
- **이미지**: Gemini Flash 2.0 Experimental (Nano Banana)
- **음성**: ElevenLabs TTS (한국어 지원)
- **배경음악**: ElevenLabs Sound Effects / Mubert
- **영상 합성**: MoviePy (9:16 세로형, 30fps)

### 5. QA Agent
- 생성된 영상 자동 검수
- 오디오/비디오/이미지 품질 체크
- 재생성 로직 (최대 3회)

---

## 🛠 기술 스택

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Task Queue**: Celery + Redis (gevent pool, concurrency=10)
- **LLM**: OpenAI GPT-4o-mini
- **Image Generation**: Google Gemini Flash 2.0 Experimental
- **TTS**: ElevenLabs API
- **Music**: ElevenLabs Sound Effects / Mubert
- **Video**: MoviePy
- **State Management**: Redis (FSM 저장)
- **Background Removal**: rembg (U2Net) - Story Mode만 사용

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

## 🆕 최근 업데이트 (2025-11-07)

### General Mode 프로토타입 완성
1. **일반 모드 프론트엔드 추가**
   - `frontend/src/components/RunForm.tsx`: 일반 모드 옵션 추가
   - 모드 선택: General (일반) / Story (스토리텔링) / Ad (광고)

2. **백엔드 스키마 수정**
   - `backend/app/schemas/json_layout.py`:
     - `mode` Literal에 "general" 추가
     - `ImageSlot`에 `image_prompt`, `aspect_ratio`, `background` 필드 추가

3. **일반 모드 렌더링 로직**
   - `backend/app/tasks/director.py`:
     - **완전한 흰색 배경**: `(255, 255, 255)` RGB
     - **검은색 자막**: 흰 배경에 잘 보이도록 색상 반전
     - **자동 줄바꿈**: `method='caption'`, 화면 너비의 90% 제한
   - 1:1 이미지 중앙 배치

4. **디자이너 태스크 개선**
   - `backend/app/tasks/designer.py`:
     - General Mode용 1:1 이미지 생성 (1080x1080)
     - 씬 이미지 캐싱 및 재사용 로직
     - 배경 제거(rembg) 비활성화

5. **JSON 변환 로직**
   - `backend/app/utils/json_converter.py`:
     - General/Ad Mode용 단순 스키마 (`image_prompt` + `speaker`)
     - Story Mode용 복잡 스키마 (`char1_id` + `char2_id` + 위치/표정/포즈)
     - 모드 자동 감지

6. **플롯 생성**
   - `backend/app/utils/plot_generator.py`:
     - General Mode 전용 프롬프트 템플릿
     - `bgm_prompt` 메타데이터 생성

7. **QA 검증**
   - `backend/app/tasks/qa.py`:
     - `image_slots` → `images` 필드명 수정

### 디버깅 개선
- `backend/app/providers/images/gemini_image_client.py`:
  - Gemini API 응답 로깅 레벨을 `logger.info()`로 변경
  - Stub 이미지 생성 원인 추적 가능

---

## 🚀 시작하기

### 사전 요구사항
```bash
# Python 3.11+
python --version

# Redis
redis-server --version

# Node.js 18+
node --version
```

### 환경 변수 설정
`.env.example`을 복사하여 `.env` 파일 생성:
```bash
cp .env.example .env
```

필수 API 키 설정:
```env
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_gemini_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
```

### 백엔드 실행
```bash
cd backend

# 가상 환경 생성 및 활성화
python -m venv kvenv
source kvenv/bin/activate  # Windows: kvenv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# Redis 실행 (별도 터미널)
redis-server

# Celery 워커 실행 (별도 터미널)
source kvenv/bin/activate
celery -A app.celery_app worker --loglevel=info --pool=gevent --concurrency=10

# FastAPI 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 프론트엔드 실행
```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

접속: `http://localhost:5173`

---

## 📂 프로젝트 구조

```
Kurz_Studio_AI/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 엔트리포인트
│   │   ├── celery_app.py        # Celery 설정
│   │   ├── config.py            # 환경 변수 설정
│   │   ├── tasks/               # Celery 태스크
│   │   │   ├── plan.py          # 기획자: 플롯 & 캐릭터 생성
│   │   │   ├── designer.py      # 디자이너: 이미지 생성
│   │   │   ├── composer.py      # 작곡가: BGM 생성
│   │   │   ├── voice.py         # 성우: TTS 생성
│   │   │   ├── director.py      # 감독: 영상 합성
│   │   │   └── qa.py            # QA: 품질 검수
│   │   ├── orchestrator/        # FSM 상태 관리
│   │   │   └── fsm.py
│   │   ├── providers/           # 외부 API 클라이언트
│   │   │   ├── images/          # Gemini
│   │   │   ├── tts/             # ElevenLabs TTS
│   │   │   └── music/           # ElevenLabs Music
│   │   ├── schemas/             # Pydantic 스키마
│   │   │   └── json_layout.py
│   │   └── utils/               # 유틸리티
│   │       ├── plot_generator.py
│   │       └── json_converter.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── RunForm.tsx      # 영상 생성 폼
│   │   │   └── RunStatus.tsx    # 진행 상황 표시
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── voices.json                   # ElevenLabs 음성 설정
├── README.md
└── claude.md                     # 이 파일
```

---

## 🎬 워크플로우

### 전체 파이프라인
```
[사용자 프롬프트]
    ↓
[IDLE → PLOT_GENERATION]
    ├─ GPT-4o-mini: characters.json 생성
    └─ GPT-4o-mini: plot.json 생성
    ↓
[json_converter: layout.json 변환]
    ├─ Story Mode: char1_id/char2_id 스키마
    └─ General/Ad Mode: image_prompt 스키마
    ↓
[ASSET_GENERATION] (병렬 실행)
    ├─ Designer: Gemini 이미지 생성
    ├─ Composer: ElevenLabs BGM 생성
    └─ Voice: ElevenLabs TTS 생성
    ↓
[RENDERING]
    └─ Director: MoviePy 영상 합성
    ↓
[QA]
    ├─ Pass → END
    └─ Fail → PLOT_GENERATION (재시도)
```

### 모드별 차이점

| 항목 | Story Mode | General Mode | Ad Mode |
|------|------------|--------------|---------|
| **이미지 구성** | 캐릭터(2:3) + 배경(9:16) | 통합 이미지(1:1) | 통합 이미지(1:1) |
| **배경색** | 어두운 배경 (20, 20, 40) | 흰색 (255, 255, 255) | 흰색 (255, 255, 255) |
| **자막 색상** | 흰색 + 검은 테두리 | 검은색 + 흰 테두리 | 검은색 + 흰 테두리 |
| **배경 제거** | rembg 사용 | 사용 안 함 | 사용 안 함 |
| **JSON 스키마** | `char1_id`, `char2_id`, `pos`, `expression`, `pose` | `image_prompt`, `speaker` | `image_prompt`, `speaker` |
| **프롬프트** | 캐릭터 중심 스토리 | 일반 영상 | 광고 특화 |

---

## 📊 모드별 상세 설명

### Story Mode (스토리 모드)
**사용 사례**: 캐릭터 기반 스토리텔링, 웹툰 스타일 영상, 교육 콘텐츠

**특징**:
- 사용자가 캐릭터(이름, 외형, 성격)를 정의
- 각 씬마다 최대 2명의 캐릭터 배치 가능
- 위치: `left`, `center`, `right`
- 표정: `happy`, `sad`, `angry`, `surprised`, `neutral`, `excited`, `confident`
- 포즈: `standing`, `sitting`, `walking`, `pointing`
- 배경 이미지와 캐릭터 이미지 분리 생성
- rembg로 캐릭터 배경 제거 후 합성

**JSON 구조**:
```json
{
  "mode": "story",
  "scenes": [{
    "scene_id": "scene_1",
    "char1_id": "char_1",
    "char1_pos": "left",
    "char1_expression": "happy",
    "char1_pose": "standing",
    "char2_id": "char_2",
    "char2_pos": "right",
    "char2_expression": "surprised",
    "char2_pose": "standing",
    "speaker": "char_1",
    "text": "대사 내용",
    "background_img": "sunny park with trees"
  }]
}
```

### General Mode (일반 모드)
**사용 사례**: 일반 설명 영상, 튜토리얼, 브이로그 스타일

**특징**:
- 프롬프트만 입력하면 자동으로 시나리오 생성
- 씬당 1장의 통합 이미지 (캐릭터 + 배경 통합)
- 1:1 정방형 이미지 (1080x1080)
- 완전한 흰색 배경
- 검은색 자막 (가독성 최적화)
- 화면 너비 90% 내 자동 줄바꿈
- 이미지 재사용: `image_prompt`를 빈 문자열 `""`로 설정하면 이전 이미지 재사용

**JSON 구조**:
```json
{
  "mode": "general",
  "scenes": [{
    "scene_id": "scene_1",
    "image_prompt": "귀여운 고양이가 웃으며 손을 흔드는 모습, 밝은 햇살",
    "speaker": "char_1",
    "text": "안녕하세요!",
    "duration_ms": 5000
  }, {
    "scene_id": "scene_2",
    "image_prompt": "",  // 이전 이미지 재사용
    "speaker": "narration",
    "text": "해설 내용",
    "duration_ms": 4000
  }],
  "metadata": {
    "bgm_prompt": "upbeat, cheerful, acoustic guitar"
  }
}
```

### Ad Mode (광고 모드)
**사용 사례**: 제품 홍보, 서비스 소개, 브랜드 영상

**특징**:
- General Mode와 동일한 기술 스택
- 광고 특화 프롬프트 엔지니어링
- 제품/서비스 강조

---

## 📐 Rules & Guidelines

### 코딩 컨벤션
- **Python**: PEP 8, Type Hints 사용
- **TypeScript**: ESLint + Prettier
- **커밋 메시지**: Conventional Commits 형식
  ```
  feat: Add general mode to frontend
  fix: Fix QA stage field name (image_slots → images)
  refactor: Update director subtitle color by mode
  ```

### Agent 역할 분담
1. **Plan Agent**: GPT로 캐릭터 + 플롯 생성
2. **Designer Agent**: Gemini로 이미지 생성
3. **Composer Agent**: ElevenLabs/Mubert로 BGM 생성
4. **Voice Agent**: ElevenLabs TTS로 음성 생성
5. **Director Agent**: MoviePy로 영상 합성
6. **QA Agent**: 품질 검증 및 재생성 로직

### 상태 관리 (FSM)
```python
class RunState(Enum):
    IDLE = "IDLE"
    PLOT_GENERATION = "PLOT_GENERATION"
    ASSET_GENERATION = "ASSET_GENERATION"
    RENDERING = "RENDERING"
    QA = "QA"
    END = "END"
    FAILED = "FAILED"
```

### 에러 처리
- 모든 태스크는 실패 시 FSM에 `FAILED` 상태 기록
- QA 실패 시 최대 3회까지 PLOT_GENERATION부터 재시도
- Gemini API 실패 시 stub 이미지로 폴백 (70바이트 1x1 PNG)

---

## 🔧 트러블슈팅

### Stub 이미지 생성 문제
**증상**: 생성된 이미지가 70바이트의 1x1 픽셀 이미지

**원인**:
1. Gemini API 할당량 초과 (무료 티어: 분당 15 요청, 일일 1500 요청)
2. 프롬프트가 안전성 필터에 걸림
3. API 응답에 이미지 데이터 없음

**해결**:
- Gemini API 응답 로그 확인 (`logger.info` 레벨)
- API 키 할당량 확인
- 프롬프트 수정

### Celery 워커 재시작
```bash
# 모든 워커 종료
pkill -9 -f "celery.*worker"

# 새 워커 시작
cd backend
source kvenv/bin/activate
celery -A app.celery_app worker --loglevel=info --pool=gevent --concurrency=10
```

### Redis 연결 실패
```bash
# Redis 실행 확인
redis-cli ping
# 응답: PONG

# Redis 서버 시작
redis-server
```

---

## 📝 개발 히스토리

### 2025-11-07
- ✅ General Mode 프로토타입 완성
- ✅ 흰색 배경 + 검은색 자막 구현
- ✅ 자동 줄바꿈 적용
- ✅ QA 필드명 버그 수정 (`image_slots` → `images`)
- ✅ Gemini API 응답 로깅 개선
- ✅ 프로젝트명 변경: AutoShorts → Kurz AI Studio

### 이전 작업
- Story Mode 구현
- Celery + Redis 비동기 처리
- FSM 상태 관리
- Multi-Agent 아키텍처 설계

---

## 🎯 향후 계획

### Short-term
- [ ] General Mode 테스트 및 버그 수정
- [ ] Gemini API 할당량 관리
- [ ] 프롬프트 최적화

### Mid-term
- [ ] 프론트엔드 UI/UX 개선
- [ ] 영상 미리보기 기능
- [ ] 사용자 피드백 시스템

### Long-term
- [ ] 클라우드 배포 (AWS/GCP)
- [ ] 사용자 인증 시스템
- [ ] 다국어 지원 확대

---

## 📄 License

This project is licensed under the MIT License.

---

## 👥 Contact

프로젝트 관련 문의: [이메일 또는 이슈 트래커]

**Project Repository**: [GitHub URL]

---

**마지막 업데이트**: 2025-11-07
**버전**: 1.0.0-alpha (General Mode Prototype)
