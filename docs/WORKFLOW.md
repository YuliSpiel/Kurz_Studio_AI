# Kurz AI Studio - 워크플로우

**최종 업데이트**: 2025-11-21

## FSM 상태 전이

```
┌────────┐
│  INIT  │
└───┬────┘
    │
    ↓
┌─────────────────┐
│ PLOT_GENERATION │ ← 기획자: characters.json + plot.json + layout.json
└───┬─────────────┘
    │
    ↓ (review_mode=true 시 여기서 대기)
┌─────────────────────┐
│ ASSET_GENERATION    │ ← 디자이너/작곡가/성우 병렬 실행
└───┬─────────────────┘
    │
    ↓
┌─────────────────┐
│   RENDERING     │ ← 감독: FFmpeg 합성
└───┬─────────────┘
    │
    ↓
┌─────────────────┐
│       QA        │ ← QA: 품질 검수
└───┬─────────────┘
    │
    ├─ Pass → END
    │
    └─ Fail → FAILED (또는 재시도)
```

---

## 실행 모드

### 1. Review Mode (검수 모드)
- `review_mode=true`
- PLOT_GENERATION 완료 후 대기
- 사용자가 레이아웃 검수/수정 후 "확정" 버튼 클릭
- `/v1/runs/{run_id}/layout-confirm` 호출로 진행

### 2. Auto Mode (자동 모드)
- `review_mode=false`
- PLOT_GENERATION 완료 즉시 ASSET_GENERATION 진행
- 검수 단계 없이 자동 완료

---

## 상세 워크플로우

### 1. INIT → PLOT_GENERATION

**담당**: `tasks/plan.py`

**작업**:
1. 사용자 프롬프트 분석
2. Gemini 2.5 Flash로 시나리오 생성
3. 파일 생성:
   - `characters.json`: 캐릭터 정의 (appearance, personality, voice_profile)
   - `plot.json`: 장면별 시나리오 (expression, pose, text, emotion)
   - `layout.json`: 렌더링용 통합 데이터 (images, texts, timeline)

**프롬프트 템플릿 위치**: `utils/plot_generator.py`

---

### 2. PLOT_GENERATION → ASSET_GENERATION

**Celery Chord 패턴**으로 3개 Agent 병렬 실행:

```python
chord(
    group(
        designer_task.s(run_id, json_path, spec),
        composer_task.s(run_id, json_path, spec),
        voice_task.s(run_id, json_path, spec),
    )
)(director_task.s(asset_results, run_id, json_path))
```

#### 2.1 Designer Agent (`tasks/designer.py`)
- layout.json에서 각 씬의 `image_prompt` 읽기
- Gemini Flash 2.0으로 이미지 생성
- 이미지 경로를 layout.json에 업데이트

#### 2.2 Composer Agent (`tasks/composer.py`)
- layout.json에서 `bgm_prompt` 읽기
- ElevenLabs Sound Effects API로 BGM 생성 (30초)
- BGM 경로를 layout.json에 업데이트

#### 2.3 Voice Agent (`tasks/voice.py`)
- layout.json에서 각 씬의 대사(`texts`) 읽기
- ElevenLabs TTS로 음성 합성
- 음성 경로를 layout.json에 업데이트
- **TTS 길이 기반 duration 자동 조정**

---

### 3. ASSET_GENERATION → RENDERING

**담당**: `tasks/director.py`

**작업**:
1. 업데이트된 layout.json 로드
2. FFmpeg로 영상 합성
   - 이미지 레이어링
   - 한글 자막 오버레이 (Pretendard 폰트)
   - 음성 타이밍 동기화
   - BGM 믹싱 (볼륨 0.3)
3. 최종 영상 출력
   - 해상도: 1080x1920 (9:16)
   - FPS: 30
   - 코덱: H.264

**출력**: `app/data/outputs/{run_id}/final_video.mp4`

---

### 4. RENDERING → QA

**담당**: `tasks/qa.py`

**검수 항목**:
- 영상 파일 존재 확인
- 파일 크기 > 0
- JSON 레이아웃 유효성

**결과**:
- Pass → END (완료)
- Fail → FAILED

---

## 진행률 매핑

| 단계 | 상태 | 진행률 | 로그 메시지 |
|------|------|--------|------------|
| 플롯 시작 | PLOT_GENERATION | 0.10 | "플롯 생성 시작" |
| 플롯 완료 | PLOT_GENERATION | 0.20 | "JSON 레이아웃 생성 완료" |
| 에셋 시작 | ASSET_GENERATION | 0.25 | "에셋 생성 시작" |
| 이미지 생성 | ASSET_GENERATION | 0.30-0.50 | "이미지 생성 중" |
| BGM 생성 | ASSET_GENERATION | 0.50-0.60 | "배경음악 생성 중" |
| TTS 생성 | ASSET_GENERATION | 0.60-0.70 | "음성 합성 중" |
| 렌더링 시작 | RENDERING | 0.75 | "렌더링 시작" |
| 렌더링 완료 | RENDERING | 0.85 | "렌더링 완료" |
| QA | QA | 0.90 | "품질 검수 중" |
| 완료 | END | 1.00 | "영상 생성 완료" |

---

## Celery 설정

### 필수: 병렬 풀 사용

```bash
# gevent pool (권장)
celery -A app.celery_app worker --loglevel=info --pool=gevent --concurrency=10
```

**주의**: `--pool=solo` 사용 금지 (병렬 실행 불가)

### Worker 재시작

`backend/app/` 하위 Python 파일 수정 시 **반드시 Worker 재시작 필요**:

```bash
pkill -f "celery.*worker"
cd backend
./kvenv/bin/celery -A app.celery_app worker --loglevel=info --pool=gevent --concurrency=10
```
