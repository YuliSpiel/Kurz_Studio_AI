# Kurz AI Studio - API 명세

**최종 업데이트**: 2025-11-21

## Base URL

```
http://localhost:8000
```

---

## REST API

### 1. Health Check

**GET** `/`

```json
{
  "service": "Kurz AI Studio API",
  "version": "0.2.0",
  "status": "running"
}
```

---

### 2. Create Run (영상 생성 시작)

**POST** `/v1/runs`

#### Request Body

```json
{
  "mode": "general",
  "prompt": "강아지와 고양이의 우정 이야기",
  "num_characters": 2,
  "num_cuts": 5,
  "art_style": "파스텔 수채화",
  "music_genre": "ambient",
  "title": "영상 제목",
  "review_mode": true
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `mode` | string | ✅ | "general", "story", "ad" |
| `prompt` | string | ✅ | 영상 설명 프롬프트 |
| `num_characters` | int | ✅ | 캐릭터 수 (1-3) |
| `num_cuts` | int | ✅ | 씬 수 (1-10) |
| `art_style` | string | | 화풍 (기본: "파스텔 수채화") |
| `music_genre` | string | | 음악 장르 (기본: "ambient") |
| `title` | string | | 영상 제목 |
| `review_mode` | bool | | 검수 모드 (기본: true) |

#### Response

```json
{
  "run_id": "20251121_1430_강아지와고양이",
  "state": "PLOT_GENERATION",
  "progress": 0.0,
  "artifacts": {},
  "logs": ["Run created"]
}
```

---

### 3. Get Run Status

**GET** `/v1/runs/{run_id}`

#### Response

```json
{
  "run_id": "20251121_1430_강아지와고양이",
  "state": "RENDERING",
  "progress": 0.75,
  "artifacts": {
    "json_path": "app/data/outputs/.../layout.json",
    "images": [...],
    "audio": [...],
    "video_url": "app/data/outputs/.../final_video.mp4"
  },
  "logs": [...]
}
```

#### State Values

| 상태 | 설명 |
|------|------|
| `INIT` | 초기화 |
| `PLOT_GENERATION` | 시나리오 생성 중 |
| `ASSET_GENERATION` | 에셋 생성 중 (이미지/음성/BGM) |
| `RENDERING` | 영상 합성 중 |
| `QA` | 품질 검수 중 |
| `END` | 완료 |
| `FAILED` | 실패 |

---

### 4. Confirm Layout (레이아웃 확정)

**POST** `/v1/runs/{run_id}/layout-confirm`

검수 모드에서 사용자가 레이아웃을 확인 후 영상 렌더링을 시작합니다.

#### Request Body (Optional)

```json
{
  "layout_config": {
    "bg_color": [255, 255, 255],
    "text_color": "#000000",
    "font_size": 40,
    "stroke_color": "#FFFFFF",
    "stroke_width": 2
  },
  "title": "수정된 제목"
}
```

#### Response

```json
{
  "status": "confirmed",
  "run_id": "20251121_1430_강아지와고양이",
  "message": "Layout confirmed, starting asset generation"
}
```

---

### 5. Enhance Prompt (AI 풍부화)

**POST** `/v1/enhance`

사용자 프롬프트를 AI로 풍부화합니다.

#### Request Body

```json
{
  "prompt": "강아지 이야기",
  "mode": "general"
}
```

#### Response

```json
{
  "enhanced_prompt": "골든 리트리버 강아지가 공원에서 친구들과 놀며...",
  "suggested_title": "행복한 강아지",
  "suggested_plot_outline": "강아지가 공원에서...",
  "suggested_num_cuts": 5,
  "suggested_art_style": "파스텔 수채화",
  "suggested_music_genre": "upbeat acoustic",
  "suggested_num_characters": 2,
  "suggested_narrative_tone": "친근한반말",
  "suggested_plot_structure": "기승전결",
  "reasoning": "밝고 긍정적인 분위기로..."
}
```

---

## WebSocket API

### Connect

**WS** `/ws/{run_id}`

Run의 실시간 진행 상황을 수신합니다.

### Message Types

#### 1. Initial State (연결 시)

```json
{
  "type": "initial_state",
  "state": "ASSET_GENERATION",
  "progress": 0.5,
  "artifacts": {...},
  "logs": [...]
}
```

#### 2. Progress Update

```json
{
  "type": "progress",
  "run_id": "...",
  "state": "RENDERING",
  "progress": 0.75,
  "message": "렌더링 중..."
}
```

#### 3. Ping/Pong

**Client → Server:**
```json
{ "type": "ping" }
```

**Server → Client:**
```json
{ "type": "pong" }
```

---

## Error Responses

```json
{
  "detail": "Error message"
}
```

| 상태 코드 | 설명 |
|----------|------|
| `400` | 잘못된 요청 |
| `404` | Run 없음 |
| `422` | 입력 검증 실패 |
| `500` | 서버 오류 |
