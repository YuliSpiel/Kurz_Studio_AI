# AutoShorts 워크플로 설명

## ⚠️ IMPORTANT: Celery Worker Configuration

**Before running AutoShorts, ensure your Celery worker is configured for parallel execution!**

```bash
# Start worker with gevent pool (REQUIRED for parallel asset generation)
cd backend
./start_worker.sh
```

**DO NOT use `--pool=solo`** as it disables parallel execution and breaks the chord pattern.

See [CELERY_SETUP.md](./CELERY_SETUP.md) for detailed configuration guide.

---

## FSM (Finite State Machine) 오케스트레이션

AutoShorts는 FSM 기반 오케스트레이션을 사용하여 생성 파이프라인을 관리합니다.

### 상태 다이어그램

```
┌────────┐
│  INIT  │
└───┬────┘
    │
    ↓
┌─────────────────┐
│ PLOT_GENERATION │ ← 기획자: CSV → JSON 생성
└───┬─────────────┘
    │
    ↓
┌─────────────────────┐
│ ASSET_GENERATION    │ ← 디자이너/작곡가/성우 병렬 실행
└───┬─────────────────┘
    │
    ↓
┌─────────────────┐
│   RENDERING     │ ← 감독: MoviePy 합성
└───┬─────────────┘
    │
    ↓
┌─────────────────┐
│       QA        │ ← QA: 품질 검수
└───┬─────────────┘
    │
    ├─ Pass → END
    │
    └─ Fail → PLOT_GENERATION (재시도)

에러 발생 시:
    ↓
┌─────────┐
│ FAILED  │
└─────────┘
```

### 상태 전이 규칙

| 현재 상태 | 가능한 다음 상태 |
|---------|---------------|
| INIT | PLOT_GENERATION, FAILED |
| PLOT_GENERATION | ASSET_GENERATION, FAILED |
| ASSET_GENERATION | RENDERING, FAILED |
| RENDERING | QA, FAILED |
| QA | END, PLOT_GENERATION (재시도), FAILED |
| END | (종료 상태) |
| FAILED | (종료 상태) |

---

## 오케스트레이션 플로우

### 1. INIT → PLOT_GENERATION

**담당**: 기획자 Agent (`tasks/plan.py`)

**작업**:
1. 사용자 프롬프트 수신
2. CSV 생성 (LLM 또는 룰 기반)
   - 컬럼: scene_id, sequence, char_id, text, emotion, subtitle_text, duration_ms
3. CSV → JSON 변환
   - 캐릭터 정의 (char_id, name, persona, seed)
   - 씬 구조 (images, subtitles, dialogue, bgm, sfx)
4. JSON 파일 저장

**전이 조건**:
- CSV/JSON 생성 성공 → `ASSET_GENERATION`
- 실패 → `FAILED`

---

### 2. PLOT_GENERATION → ASSET_GENERATION

**팬아웃/배리어 패턴**: Celery `chord`를 사용하여 3개 에이전트를 병렬 실행

```python
chord(
    group(
        designer_task.s(run_id, json_path, spec),
        composer_task.s(run_id, json_path, spec),
        voice_task.s(run_id, json_path, spec),
    )
)(director_task.s(run_id, json_path))
```

#### 2.1. Designer Agent (`tasks/designer.py`)

**작업**:
- JSON에서 각 씬의 이미지 슬롯 읽기
- ComfyUI로 이미지 생성
  - 캐릭터: `char_seed` 고정
  - 배경: `bg_seed = BG_SEED_BASE + scene_id`
  - LoRA 적용 (art_style)
  - 참조 이미지 사용 (OmniRef)
- 생성된 이미지 경로를 JSON 업데이트

**결과**:
```json
{
  "images": [
    {
      "scene_id": "scene_1",
      "slot_id": "center",
      "image_url": "app/data/outputs/run_123_scene_1_center.png"
    }
  ]
}
```

#### 2.2. Composer Agent (`tasks/composer.py`)

**작업**:
- JSON timeline에서 총 duration 읽기
- BGM 생성 (Mubert/Udio/Suno)
  - 장르/무드 기반
  - 전체 길이 맞춤
- SFX 생성 (선택적)
  - 대사/감정에서 무드 태그 추출
  - 적절한 효과음 선택
- 생성된 오디오 경로를 JSON 업데이트

**결과**:
```json
{
  "global_bgm": {
    "bgm_id": "global_bgm",
    "genre": "ambient",
    "audio_url": "app/data/outputs/run_123_global_bgm.mp3",
    "volume": 0.3
  }
}
```

#### 2.3. Voice Agent (`tasks/voice.py`)

**작업**:
- JSON에서 각 씬의 dialogue 읽기
- TTS 생성 (ElevenLabs/PlayHT)
  - 캐릭터별 voice_profile 매핑
  - 감정(emotion) 반영
- 생성된 음성 파일 경로를 JSON 업데이트

**결과**:
```json
{
  "dialogue": [
    {
      "line_id": "scene_1_line_1",
      "char_id": "char_1",
      "text": "안녕하세요!",
      "emotion": "happy",
      "audio_url": "app/data/outputs/run_123_scene_1_line_1.mp3",
      "start_ms": 0,
      "duration_ms": 2000
    }
  ]
}
```

**배리어**: 3개 태스크 모두 완료 시 chord 콜백 실행

---

### 3. ASSET_GENERATION → RENDERING

**담당**: 감독 Agent (`tasks/director.py`)

**작업**:
1. 업데이트된 JSON 로드 (모든 에셋 경로 포함)
2. MoviePy로 씬별 클립 생성
   - 배경 + 이미지 레이어 합성
   - 자막 오버레이 (TextClip)
   - 위치: top/center/bottom
3. 씬 클립 연결 (concatenate_videoclips)
4. 오디오 트랙 합성
   - 전역 BGM (볼륨 낮춤)
   - 대사 음성 (타이밍 맞춤)
   - SFX (start_ms 기준 배치)
5. 최종 영상 렌더링
   - 해상도: 1080x1920 (9:16)
   - FPS: 30
   - 코덱: H.264 (libx264)
   - 오디오: AAC
6. 파일 저장: `app/data/outputs/{run_id}_final.mp4`

**전이 조건**:
- 렌더링 성공 → `END`
- 실패 → `FAILED` 또는 `RECOVER`

---

### 4. RENDERING → END

**작업**:
- FSM을 `END` 상태로 전이
- Run progress를 1.0으로 설정
- 프론트엔드에 완료 알림 (WebSocket)
- 결과 artifacts 반환:
  ```json
  {
    "video_url": "app/data/outputs/run_123_final.mp4",
    "json_path": "app/data/outputs/run_123_layout.json"
  }
  ```

---

## Recovery 메커니즘

### RECOVER 상태

**진입 조건**:
- 임의의 상태에서 에러 발생
- `fsm.can_recover() == True`

**동작**:
1. 실패한 상태 식별
2. 재시도 횟수 확인 (최대 3회)
3. 폴백 전략 적용:
   - TTS 실패 → Provider 교체 (ElevenLabs ↔ PlayHT)
   - 이미지 생성 실패 → seed 변경 재시도
   - 타임아웃 → 재실행
4. 실패한 태스크 재실행

**전이**:
- 복구 성공 → 실패했던 상태로 재진입
- 복구 실패 또는 최대 재시도 초과 → `FAILED`

### 자동 재시도 (Celery)

Celery 태스크는 자동 재시도 설정:

```python
@celery.task(
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
```

- 지수 백오프 (exponential backoff)
- 최대 10분 대기
- 지터 추가 (부하 분산)

---

## 시퀀스 다이어그램

```
사용자      프론트엔드      FastAPI      Celery Workers      ComfyUI/TTS/Music
  │             │              │              │                     │
  │─ 입력 ────→│              │              │                     │
  │             │─ POST /runs ─→│              │                     │
  │             │              │─ FSM Init ──→│                     │
  │             │              │              │                     │
  │             │←─ run_id ────│              │                     │
  │             │              │              │                     │
  │             │─ WS connect ─→│              │                     │
  │             │              │              │                     │
  │             │              │    [Plan Task]                     │
  │             │              │─────────────→│                     │
  │             │              │              │─ CSV → JSON         │
  │             │              │←─────────────│                     │
  │             │              │              │                     │
  │             │              │    [Fan-out: chord]                │
  │             │              │─────────────→│                     │
  │             │              │              ├─ Designer ─────────→│
  │             │              │              │                     │─ Generate
  │             │              │              │←────────────────────│
  │             │              │              ├─ Composer ─────────→│
  │             │              │              │                     │─ Generate
  │             │              │              │←────────────────────│
  │             │              │              ├─ Voice ────────────→│
  │             │              │              │                     │─ TTS
  │             │              │              │←────────────────────│
  │             │              │              │                     │
  │             │              │    [Barrier: all done]             │
  │             │              │              │                     │
  │             │              │    [Director Task]                 │
  │             │              │─────────────→│                     │
  │             │              │              │─ MoviePy Render     │
  │             │              │←─────────────│                     │
  │             │              │              │                     │
  │             │← WS: END ────│              │                     │
  │             │              │              │                     │
  │← 영상 재생 ─│              │              │                     │
```

---

## 성능 최적화

### 병렬 처리

- **Designer, Composer, Voice**: 동시 실행
- Celery worker pool 크기: `--concurrency=4` (기본)
- Redis 큐 분리 가능 (우선순위 처리)

### 타임아웃

- ComfyUI 이미지 생성: 5분
- TTS 생성: 1분
- 전체 Run: 1시간 (hard limit)

### 캐싱

- 동일 prompt/seed: 이미지 재사용 가능 (추후 구현)
- LLM 응답 캐싱 (CSV 생성 시)

---

## 모니터링

### 로그

- FastAPI: `uvicorn` 로그
- Celery: worker 로그
- Provider 호출: `httpx` 로그

### 메트릭 (추후 추가)

- Run 성공률
- 평균 생성 시간 (단계별)
- Provider 호출 횟수/실패율

---

## 확장 가능성

### 새로운 Agent 추가

예: **Editor Agent** (편집 효과)

1. `tasks/editor.py` 생성
2. Chord에 추가:
   ```python
   chord(
       group(designer, composer, voice, editor)
   )(director)
   ```
3. JSON 스키마 확장 (transitions, effects)

### 분산 실행

- Celery broker를 RabbitMQ로 교체
- Worker를 여러 머신에 배포
- Redis → PostgreSQL (result backend)

### 우선순위 큐

```python
# 높은 우선순위 Run
task.apply_async(args=[...], priority=9)
```

---

## 참고 자료

- [Celery Documentation](https://docs.celeryproject.org/)
- [MoviePy Documentation](https://zulko.github.io/moviepy/)
- [ComfyUI API](https://github.com/comfyanonymous/ComfyUI)

### 4. RENDERING → QA

**담당**: QA Agent (`tasks/qa.py`)

**작업**:
1. 영상 파일 존재 확인
2. JSON 레이아웃 유효성 검증
   - 필수 필드 존재 (scenes, timeline)
   - 모든 씬에 이미지 존재
3. 에셋 파일 확인
   - 이미지: `scenes[].images[].image_url` 경로 존재
   - BGM: `global_bgm.audio_url` 경로 존재
   - 음성: `scenes[].dialogue[].audio_url` 경로 존재
4. 품질 판정
   - Pass: 모든 검사 통과
   - Fail: 하나 이상 실패

**전이 조건**:
- Pass → `END`
- Fail → `PLOT_GENERATION` (재시도)
- 에러 → `FAILED`

**검수 항목**:
```python
qa_results = {
    "checks": [
        {"name": "Video file exists", "passed": True},
        {"name": "JSON has 'scenes' field", "passed": True},
        {"name": "JSON has 'timeline' field", "passed": True},
        {"name": "Image for scene_1", "passed": True},
        {"name": "Background music exists", "passed": True}
    ],
    "passed": True,
    "issues": []
}
```

**재시도 로직**:
- QA 실패 시 `retry_from_qa()` 메서드 호출
- FSM이 PLOT_GENERATION으로 전이
- 플롯부터 재생성 시작
- 재시도 횟수는 metadata에 기록

---

### 5. QA → END

