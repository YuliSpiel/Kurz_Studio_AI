# AutoShorts - AI 스토리텔링 숏폼 영상 자동 제작 시스템

## 프로젝트 개요
사용자가 제공한 프롬프트로 스토리를 생성하고, 캐릭터 이미지/음성/배경음악을 자동 생성하여 비주얼노벨 스타일의 숏폼 영상을 제작하는 시스템입니다.

## 기술 스택

### Backend (Python)
- **FastAPI**: REST API 서버 및 WebSocket (진행도 실시간 업데이트)
- **Celery**: 비동기 작업 큐 (gevent pool, concurrency=10)
- **Redis**: Celery 브로커, FSM 상태 저장, Pub/Sub
- **MoviePy**: 영상 합성 및 렌더링
- **Pydantic**: 데이터 검증 및 JSON 스키마

### Frontend (React + TypeScript)
- **React**: UI 컴포넌트
- **TypeScript**: 타입 안정성
- **Vite**: 빌드 도구

### 외부 API
- **OpenAI GPT-4o-mini**: 시나리오 및 캐릭터 생성
- **Gemini 2.5 Flash (Nano Banana)**: 이미지 생성
- **ElevenLabs**: TTS 음성 합성 및 BGM 생성
- **rembg**: 캐릭터 배경 투명화

## 디렉토리 구조

```
backend/
├── app/
│   ├── celery_app.py          # Celery 초기화
│   ├── config.py               # 환경 설정 (.env)
│   ├── main.py                 # FastAPI 앱 및 WebSocket
│   ├── orchestrator/
│   │   └── fsm.py              # 상태 기계 (FSM)
│   ├── tasks/
│   │   ├── plan.py             # 플롯 생성 (GPT)
│   │   ├── designer.py         # 이미지 생성 (Gemini)
│   │   ├── voice.py            # TTS 음성 (ElevenLabs)
│   │   ├── composer.py         # BGM 생성 (ElevenLabs)
│   │   ├── director.py         # 영상 합성 (MoviePy) ⚠️ 캐릭터 위치 렌더링
│   │   └── qa.py               # 품질 검수
│   ├── utils/
│   │   ├── plot_generator.py   # GPT-4o-mini 프롬프트 엔지니어링
│   │   ├── json_converter.py   # plot.json → layout.json 변환, 캐싱
│   │   └── progress.py         # Redis pub/sub 진행도 업데이트
│   ├── providers/              # API 클라이언트
│   │   ├── images/gemini_client.py
│   │   └── tts/elevenlabs_client.py
│   └── schemas/
│       ├── run_spec.py         # API 요청/응답 스키마
│       └── json_layout.py      # 영상 구성 JSON 스키마 ⚠️ ImageSlot에 position/x_pos 필드
├── kvenv/                      # Python 가상환경
└── data/
    └── outputs/                # 생성된 영상 및 에셋

frontend/
└── src/
    ├── components/
    │   ├── StoryModeForm.tsx   # Story Mode 입력 폼 (Alt+Shift+T 테스트 모드)
    │   └── RunStatus.tsx       # 진행도 표시 (WebSocket)
    └── api/client.ts           # API 호출
```

## 워크플로우 (FSM States)

```
IDLE → PLOT_GENERATION → ASSET_GENERATION → VIDEO_COMPOSITION → QA → END
                ↓               ↓                    ↓
            plan_task     designer, voice,      director
                          composer (병렬)
```

## Story Mode 특징 (최근 구현)

### 1. 선택적 캐릭터 배치
- 모든 씬에 모든 캐릭터가 나오지 않음
- GPT가 스토리 흐름에 따라 필요한 캐릭터만 배치
- 두 캐릭터 등장 시 자동으로 left/right 위치 지정

### 2. 씬 간 캐싱
- `""` (빈 문자열): 이전 씬 값 재사용
- `null`: 해당 요소 없음
- 캐싱 대상: `char_expression`, `char_pose`, `background_img`

### 3. 캐릭터 이미지 표준화
- **프레이밍**: "from thighs up, upper body portrait"
- **배경**: "pure white background" (투명화 용이)
- **비율**: 2:3 (512x768), 배경은 9:16 (1080x1920)

### 4. 위치 렌더링 (director.py)
⚠️ **중요**: x_pos는 이미지 **중심** 좌표입니다.
- `left` (x_pos=0.25): 화면 왼쪽 1/4 지점에 중심
- `center` (x_pos=0.5): 화면 정중앙에 중심
- `right` (x_pos=0.75): 화면 오른쪽 3/4 지점에 중심

## 개발 시 주의사항

### Celery Worker 실행
```bash
cd backend
./kvenv/bin/celery -A app.celery_app worker --loglevel=info --pool=gevent --concurrency=10
```
⚠️ `source kvenv/bin/activate && celery` 대신 **직접 경로** 사용 (gevent import 오류 방지)

### FastAPI 서버 실행
```bash
cd backend
source kvenv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Frontend 실행
```bash
cd frontend
npm run dev
```

### Redis 확인
```bash
redis-cli ping                           # Redis 연결 확인
redis-cli PUBSUB NUMSUB autoshorts:progress  # 구독자 수 확인 (1이면 정상)
```

## 파일 경로 규칙
- Run ID 형식: `YYYYMMDD_HHMM_프롬프트앞8글자`
- 출력 폴더: `backend/app/data/outputs/{run_id}/`
  - `plot.json`: GPT 생성 시나리오
  - `layout.json`: 영상 구성 JSON (Pydantic 검증 후)
  - `characters.json`: 캐릭터 정보
  - `final_video.mp4`: 최종 영상
  - `audio/`: TTS 음성 및 BGM
  - `*.png`: 생성된 이미지 (캐릭터는 투명 배경)

## 테스트 방법

### 1. Alt+Shift+T (Option+Shift+T on Mac)
프론트엔드 Story Mode 폼에서 샘플 데이터 자동 입력

### 2. 수동 테스트
- 스토리 텍스트 입력 (대화/해설 혼합)
- 캐릭터 2명 정의 (이름, 성별, 역할, 성격, 외모)
- Submit → RunStatus 페이지에서 진행도 확인

## 알려진 이슈

### 1. Gemini API NO_IMAGE 응답
- 일부 캐릭터 프롬프트에서 이미지 생성 실패
- 현재: stub 이미지 (1x1 픽셀)로 대체
- 해결 방안: 프롬프트 단순화 또는 재시도 로직 추가

### 2. 진행도 표시 0% 고정 (진행중)
- 원인: FastAPI 서버 재시작 시 in-memory `runs` dict 초기화
- 해결 방안: Redis에 run 상태 저장 (진행중)
- 임시 해결: Celery 로그로 진행 상황 확인

## 진행중인 작업

1. **Redis 기반 run 상태 저장**: FastAPI 서버 재시작 시에도 진행도 유지
2. **진행도 애니메이션**: 작가 글쓰기, 화가 그림 그리기 등 GIF 애니메이션 추가 예정

## 커밋 가이드라인
- 커밋 메시지는 영어로 작성
- 마지막에 다음 추가:
  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  Co-Authored-By: Claude <noreply@anthropic.com>
  ```

## 최근 변경사항
- ✅ Story Mode 선택적 캐릭터 배치 (plot_generator.py)
- ✅ 씬 간 캐싱 메커니즘 (json_converter.py)
- ✅ 캐릭터 이미지 표준화 (designer.py, json_converter.py)
- ✅ ImageSlot 스키마에 position/x_pos 필드 추가 (json_layout.py)
- ✅ 캐릭터 위치 렌더링 수정: 이미지 중심 기준 배치 (director.py)
