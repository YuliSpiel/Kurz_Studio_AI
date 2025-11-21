# Kurz AI Studio - 데이터 스키마

**최종 업데이트**: 2025-11-21

## 데이터 흐름

```
User Prompt
    ↓
[plot_generator.py] Gemini 2.5 Flash
    ↓
1. characters.json (캐릭터 정의)
2. plot.json (장면별 시나리오)
    ↓
[json_converter.py] 변환
    ↓
3. layout.json (렌더링용 통합 데이터)
    ↓
[Asset Generation] 병렬 생성
    ↓
4. Images (Gemini Flash 2.0)
5. Voice (ElevenLabs TTS)
6. BGM (ElevenLabs SFX)
    ↓
[director.py] FFmpeg 합성
    ↓
final_video.mp4
```

---

## 1. characters.json

캐릭터 정의 파일. Gemini가 생성.

### 구조

```json
{
  "characters": [
    {
      "char_id": "char_1",
      "name": "캐릭터 이름",
      "appearance": "상세한 외형 묘사 (이미지 생성용)",
      "personality": "성격 설명",
      "voice_profile": "default",
      "seed": 1002
    }
  ]
}
```

### 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `char_id` | string | 고유 ID (char_1, char_2, ...) |
| `name` | string | 캐릭터 이름 |
| `appearance` | string | 외형 상세 묘사 (Gemini 이미지 프롬프트용) |
| `personality` | string | 성격/특징 설명 |
| `voice_profile` | string | 음성 프로필 (현재 "default") |
| `seed` | int | 이미지 생성 시드 (1002부터) |

---

## 2. plot.json

장면별 시나리오 파일. Gemini가 생성.

### 구조

```json
{
  "bgm_prompt": "upbeat, cheerful, acoustic guitar",
  "scenes": [
    {
      "scene_id": "scene_1",
      "image_prompt": "이미지 생성 프롬프트 (빈 문자열이면 이전 이미지 재사용)",
      "text": "대사 또는 해설",
      "speaker": "char_1",
      "duration_ms": 5000
    }
  ]
}
```

### 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `bgm_prompt` | string | BGM 생성 프롬프트 |
| `scene_id` | string | 장면 ID (scene_1, scene_2, ...) |
| `image_prompt` | string | 이미지 프롬프트 (빈 문자열 = 이전 이미지 재사용) |
| `text` | string | 대사 또는 해설 |
| `speaker` | string | 발화자 ID (char_1, narrator 등) |
| `duration_ms` | int | 장면 지속 시간 (밀리초) |

### 이미지 재사용 규칙

- `image_prompt = ""` (빈 문자열): 이전 씬의 이미지 재사용
- `image_prompt = "..."` (값 있음): 새 이미지 생성

---

## 3. layout.json

렌더링용 최종 데이터. `json_converter.py`가 생성.

### 구조

```json
{
  "project_id": "20251121_1430_프롬프트8글자",
  "title": "영상 제목",
  "mode": "general",
  "timeline": {
    "total_duration_ms": 30000,
    "aspect_ratio": "9:16",
    "fps": 30,
    "resolution": "1080x1920"
  },
  "characters": [...],
  "scenes": [...],
  "global_bgm": {
    "bgm_id": "global_bgm",
    "bgm_prompt": "BGM 프롬프트",
    "audio_url": "app/data/outputs/.../audio/global_bgm.mp3",
    "volume": 0.3
  },
  "layout_config": {
    "bg_color": [255, 255, 255],
    "text_color": "#000000",
    "font_size": 40,
    "stroke_color": "#FFFFFF",
    "stroke_width": 2
  },
  "metadata": {
    "created_at": "2025-11-21T14:30:00",
    "prompt": "원본 프롬프트"
  }
}
```

### Scene 구조

```json
{
  "scene_id": "scene_1",
  "sequence": 1,
  "duration_ms": 5000,
  "images": [
    {
      "slot_id": "center",
      "type": "character",
      "ref_id": "char_1",
      "image_url": "app/data/outputs/.../scene_1_center.png",
      "image_prompt": "이미지 프롬프트",
      "z_index": 1
    }
  ],
  "texts": [
    {
      "line_id": "scene_1_line_1",
      "char_id": "char_1",
      "text": "대사 내용",
      "text_type": "dialogue",
      "emotion": "happy",
      "position": "top",
      "audio_url": "app/data/outputs/.../audio/scene_1_scene_1_line_1.mp3",
      "start_ms": 0,
      "duration_ms": 5000
    }
  ],
  "transition": "fade"
}
```

### 주요 필드

#### Timeline
| 필드 | 설명 |
|------|------|
| `total_duration_ms` | 전체 영상 길이 |
| `aspect_ratio` | 9:16 (세로형) |
| `fps` | 30fps |
| `resolution` | 1080x1920 |

#### ImageSlot
| 필드 | 설명 |
|------|------|
| `slot_id` | 위치 (center) |
| `image_url` | 생성된 이미지 경로 |
| `image_prompt` | 이미지 생성 프롬프트 |

#### TextLine
| 필드 | 설명 |
|------|------|
| `line_id` | 텍스트 라인 ID |
| `text` | 자막 텍스트 |
| `text_type` | dialogue / narration |
| `position` | 자막 위치 (top/bottom) |
| `audio_url` | TTS 음성 경로 |

#### LayoutConfig
| 필드 | 설명 |
|------|------|
| `bg_color` | 배경색 RGB |
| `text_color` | 자막 색상 |
| `font_size` | 폰트 크기 |
| `stroke_color` | 외곽선 색상 |
| `stroke_width` | 외곽선 두께 |

---

## 파일 위치

```
backend/app/data/outputs/{run_id}/
├── characters.json      # 캐릭터 정의
├── plot.json            # 장면 시나리오
├── layout.json          # 렌더링 데이터
├── scene_1_center.png   # 생성된 이미지
├── scene_2_center.png
├── audio/
│   ├── scene_1_scene_1_line_1.mp3  # TTS 음성
│   ├── scene_2_scene_2_line_1.mp3
│   └── global_bgm.mp3   # 배경음악
└── final_video.mp4      # 최종 영상
```

---

## 캐릭터 변수 치환

`{char_X}` 형식의 변수는 실제 캐릭터 이름으로 자동 치환됨:

```python
# json_converter.py에서 처리
# 예: "{char_1}이 말했다" → "루피가 말했다"
```

적용 필드:
- `image_prompt`
- `text`
