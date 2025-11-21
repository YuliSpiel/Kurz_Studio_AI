# Kurz AI Studio - 시스템 아키텍처

**최종 업데이트**: 2025-11-21

## 전체 구조

```
┌──────────────────┐
│   Frontend       │ (React + TypeScript + Vite)
│   (Port 5173)    │
└──────┬───────────┘
       │ HTTP/WebSocket
       ↓
┌──────────────────────┐
│   FastAPI Server     │ (Port 8000)
│   (app/main.py)      │
└──────┬───────────────┘
       │
       ├── Redis Pub/Sub ←──┐ 진행도 업데이트
       │                    │
       ├── Celery Broker    │
       │   (Redis)          │
       │                    │
       ↓                    │
┌────────────────────────┐  │
│   Celery Workers       │──┘
│   (Background Tasks)   │
└────────────────────────┘
       │
       ├── Gemini 2.5 Flash (LLM - 시나리오)
       ├── Gemini Flash 2.0 (이미지 생성)
       ├── ElevenLabs (TTS + BGM)
       └── MoviePy + FFmpeg (영상 합성)
```

---

## 핵심 컴포넌트

### 1. Frontend (React + TypeScript)

**위치**: `frontend/src/`

**주요 컴포넌트**:
- `App.tsx`: 메인 앱, 상태 관리
- `HeroChat.tsx`: 히어로 섹션 채팅 UI (프롬프트 풍부화)
- `RunForm.tsx`: 에디터 모드 입력 폼
- `RunStatus.tsx`: 실시간 진행도 표시 (모달)
- `LayoutReviewModal.tsx`: 레이아웃 검수 모달

**통신**:
- REST API: `/v1/runs` (POST), `/v1/runs/{run_id}` (GET)
- WebSocket: `/ws/{run_id}` (실시간 업데이트)

---

### 2. FastAPI Server

**위치**: `backend/app/main.py`

**주요 엔드포인트**:
- `POST /v1/runs`: 새 Run 생성
- `GET /v1/runs/{run_id}`: Run 상태 조회
- `POST /v1/runs/{run_id}/layout-confirm`: 레이아웃 확정 (영상 렌더링 시작)
- `POST /v1/enhance`: 프롬프트 풍부화 (Gemini Flash)
- `WS /ws/{run_id}`: 실시간 업데이트

---

### 3. Celery Workers

**위치**: `backend/app/tasks/`

**태스크 목록**:
1. `plan_task` - 기획자: 시나리오 생성 (characters.json, plot.json, layout.json)
2. `designer_task` - 디자이너: Gemini 이미지 생성
3. `composer_task` - 작곡가: ElevenLabs BGM 생성
4. `voice_task` - 성우: ElevenLabs TTS 생성
5. `director_task` - 감독: FFmpeg 영상 합성
6. `qa_task` - QA: 품질 검수

**병렬 실행 (Chord 패턴)**:
```python
chord(
    group(
        designer_task.s(...),
        composer_task.s(...),
        voice_task.s(...)
    )
)(director_task.s(...))
```

---

### 4. FSM (Finite State Machine)

**위치**: `backend/app/orchestrator/fsm.py`

**상태 전이**:
```
INIT → PLOT_GENERATION → ASSET_GENERATION → RENDERING → QA → END
                                                          ↓
                                                       FAILED
```

---

### 5. 외부 서비스

| 서비스 | 용도 | Provider 위치 |
|--------|------|--------------|
| Gemini 2.5 Flash | LLM (시나리오 생성) | `providers/llm/gemini_llm_client.py` |
| Gemini Flash 2.0 Exp | 이미지 생성 | `providers/image/gemini_image_client.py` |
| ElevenLabs TTS | 음성 합성 | `providers/tts/elevenlabs_client.py` |
| ElevenLabs SFX | 배경음악 생성 | `providers/music/elevenlabs_music_client.py` |

---

## 데이터 흐름

```
1. User Prompt
      ↓
2. [enhance_prompt()] AI 풍부화 (Gemini)
      ↓
3. [plan_task] 시나리오 생성
      ├── characters.json (캐릭터 정의)
      ├── plot.json (장면별 시나리오)
      └── layout.json (렌더링용 통합 데이터)
      ↓
4. [레이아웃 검수] 사용자 확인/수정 (review_mode=true 시)
      ↓
5. [Chord] 에셋 병렬 생성
      ├── designer_task → images/
      ├── composer_task → audio/global_bgm.mp3
      └── voice_task → audio/scene_*_line_*.mp3
      ↓
6. [director_task] FFmpeg 영상 합성
      ↓
7. [qa_task] 품질 검수
      ↓
8. final_video.mp4
```

---

## 폴더 구조

```
Kurz_Studio_AI/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 앱
│   │   ├── celery_app.py           # Celery 설정
│   │   ├── config.py               # 환경 변수
│   │   ├── orchestrator/
│   │   │   └── fsm.py              # FSM 상태 머신
│   │   ├── tasks/
│   │   │   ├── plan.py             # 기획자 Agent
│   │   │   ├── designer.py         # 디자이너 Agent
│   │   │   ├── composer.py         # 작곡가 Agent
│   │   │   ├── voice.py            # 성우 Agent
│   │   │   ├── director.py         # 감독 Agent
│   │   │   └── qa.py               # QA Agent
│   │   ├── providers/
│   │   │   ├── llm/                # Gemini LLM
│   │   │   ├── image/              # Gemini Image
│   │   │   ├── tts/                # ElevenLabs TTS
│   │   │   └── music/              # ElevenLabs Music
│   │   ├── utils/
│   │   │   ├── plot_generator.py   # 시나리오 생성
│   │   │   ├── json_converter.py   # plot → layout 변환
│   │   │   ├── ffmpeg_renderer.py  # FFmpeg 영상 합성
│   │   │   └── progress.py         # 진행률 Pub/Sub
│   │   └── data/
│   │       └── outputs/{run_id}/   # 생성 파일 저장
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── HeroChat.tsx
│   │   │   ├── RunForm.tsx
│   │   │   ├── RunStatus.tsx
│   │   │   ├── LayoutReviewModal.tsx
│   │   │   └── Player.tsx
│   │   └── api/
│   │       └── client.ts
│   └── package.json
│
├── DOCS/                           # 문서
└── CLAUDE.md                       # AI Agent 참조 문서
```
