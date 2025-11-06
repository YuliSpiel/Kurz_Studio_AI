# Plot Data Schema

Kurz AI Studio에서 사용하는 플롯 데이터 스키마 문서입니다.

## 데이터 플로우

```
User Prompt
    ↓
[plot_generator.py] GPT-4o-mini로 생성
    ↓
1. characters.json (캐릭터 정의)
2. plot.json (장면별 시나리오)
    ↓
[json_converter.py] 변환
    ↓
3. layout.json (최종 합성용 데이터)
    ↓
[Assets Generation] 병렬 생성
    ↓
4. Images (Gemini)
5. Voice (ElevenLabs)
6. BGM (ElevenLabs)
    ↓
[director.py] 영상 합성
    ↓
final_video.mp4
```

---

## 1. characters.json

캐릭터 정의 파일. GPT-4o-mini가 생성합니다.

### 구조

```json
{
  "characters": [
    {
      "char_id": "char_1",
      "name": "캐릭터 이름",
      "appearance": "상세한 외형 묘사 (이미지 생성 프롬프트용)",
      "personality": "성격 설명",
      "voice_profile": "default",
      "seed": 1002
    }
  ]
}
```

### 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `char_id` | string | ✅ | 캐릭터 고유 ID (char_1, char_2, ...) |
| `name` | string | ✅ | 캐릭터 이름 |
| `appearance` | string | ✅ | 외형 상세 묘사 (Gemini 이미지 생성용) |
| `personality` | string | ✅ | 성격/특징 설명 |
| `voice_profile` | string | ✅ | 음성 프로필 (현재 "default"만 지원) |
| `seed` | int | ✅ | 이미지 생성 시드 (1002부터 시작) |

### 실제 예시

```json
{
  "characters": [
    {
      "char_id": "char_1",
      "name": "댕댕이 루피",
      "appearance": "작고 귀여운 골든 리트리버 강아지로, 부드러운 금발 털과 큰 갈색 눈을 가지고 있다. 귀는 길고 늘어져 있으며, 항상 짖는 듯한 밝은 표정을 짓고 있다. 목에는 파란색 리본이 달린 흰색 목줄을 하고 있다.",
      "personality": "활발하고 호기심이 많은 성격으로, 친구를 사귀는 것을 좋아한다. 항상 긍정적이고 에너지가 넘치며, 다른 동물들과 금방 친해진다.",
      "voice_profile": "default",
      "seed": 1002
    },
    {
      "char_id": "char_2",
      "name": "고양이 미야",
      "appearance": "매끈한 검은색 털을 가진 작은 고양이로, 뾰족한 귀와 초록색 눈이 매력적이다. 몸은 날렵하고, 항상 우아하게 걷는 모습이 인상적이다. 목에는 빨간색 스카프를 두르고 있다.",
      "personality": "조용하고 지혜로운 성격으로, 조금 수줍음이 많지만 친구에게는 깊은 애정을 보인다. 호기심이 많아 주변을 탐색하는 것을 좋아하며, 루피와의 우정에서 따뜻한 면을 보여준다.",
      "voice_profile": "default",
      "seed": 1003
    }
  ]
}
```

---

## 2. plot.json

장면별 시나리오 파일. GPT-4o-mini가 생성합니다.

### 구조

```json
{
  "scenes": [
    {
      "scene_id": "scene_1",
      "char_id": "char_1",
      "expression": "excited",
      "pose": "standing",
      "text": "대사 또는 해설 내용",
      "text_type": "dialogue",
      "emotion": "happy",
      "subtitle_position": "top",
      "duration_ms": 5000
    }
  ]
}
```

### 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `scene_id` | string | ✅ | 장면 ID (scene_1, scene_2, ...) |
| `char_id` | string | ✅ | 등장하는 캐릭터 ID |
| `expression` | string | ✅ | 표정 (excited, happy, sad, angry, surprised, neutral, amazed, confident, brave, none) |
| `pose` | string | ✅ | 포즈 (standing, sitting, walking, running, pointing, looking_up, fist_raised, none) |
| `text` | string | ✅ | 대사 또는 해설 내용 |
| `text_type` | string | ✅ | `dialogue` (대사) 또는 `narration` (해설) |
| `emotion` | string | ✅ | 감정 (neutral, happy, sad, excited, angry, surprised) |
| `subtitle_position` | string | ✅ | 자막 위치 (`top` 또는 `bottom`) |
| `duration_ms` | int | ✅ | 장면 지속 시간 (밀리초, 4000-6000 권장) |

### 특수 케이스

- **해설자**: `expression`과 `pose`를 `"none"`으로 설정 (이미지 생성 안 함)
- **대사**: `text_type`이 `dialogue`일 경우 자동으로 큰따옴표 추가됨

### 실제 예시

```json
{
  "scenes": [
    {
      "scene_id": "scene_1",
      "char_id": "char_1",
      "expression": "excited",
      "pose": "standing",
      "text": "안녕! 나는 댕댕이 루피야! 오늘은 특별한 날이야!",
      "text_type": "dialogue",
      "emotion": "happy",
      "subtitle_position": "top",
      "duration_ms": 5000
    },
    {
      "scene_id": "scene_2",
      "char_id": "char_2",
      "expression": "happy",
      "pose": "sitting",
      "text": "안녕 루피! 나는 고양이 미야야! 오늘 뭐할까?",
      "text_type": "dialogue",
      "emotion": "excited",
      "subtitle_position": "bottom",
      "duration_ms": 4500
    }
  ]
}
```

---

## 3. layout.json

최종 합성용 데이터. `json_converter.py`가 characters.json과 plot.json을 통합하여 생성합니다.

### 구조

```json
{
  "project_id": "20251106_1931_강아지와고양이의",
  "title": "AutoShorts 20251106_1931_강아지와고양이의",
  "mode": "story",
  "timeline": {
    "total_duration_ms": 15500,
    "aspect_ratio": "9:16",
    "fps": 30,
    "resolution": "1080x1920"
  },
  "characters": [...],
  "scenes": [...],
  "global_bgm": null,
  "metadata": {...}
}
```

### Characters 필드

```json
{
  "char_id": "char_1",
  "name": "캐릭터 이름",
  "persona": "성격 설명",
  "voice_profile": "default",
  "seed": 1002
}
```

### Scene 필드

각 장면은 다음 구조를 가집니다:

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
      "z_index": 1,
      "image_prompt": "상세 이미지 프롬프트"
    }
  ],
  "texts": [
    {
      "line_id": "scene_1_line_1",
      "char_id": "char_1",
      "text": "\"안녕! 나는 용감한 고양이야!\"",
      "text_type": "dialogue",
      "emotion": "happy",
      "position": "top",
      "audio_url": "app/data/outputs/.../audio/scene_1_scene_1_line_1.mp3",
      "start_ms": 0,
      "duration_ms": 5000
    }
  ],
  "bgm": null,
  "sfx": [...],
  "bg_seed": 2001,
  "transition": "fade"
}
```

### 주요 필드 설명

#### Timeline
| 필드 | 설명 |
|------|------|
| `total_duration_ms` | 전체 영상 길이 (밀리초) |
| `aspect_ratio` | 화면 비율 (9:16 고정) |
| `fps` | 프레임 레이트 (30fps 고정) |
| `resolution` | 해상도 (1080x1920) |

#### ImageSlot
| 필드 | 설명 |
|------|------|
| `slot_id` | 위치 (left, center, right) |
| `type` | 타입 (character, background, prop) |
| `ref_id` | 참조 ID (char_id) |
| `image_url` | 생성된 이미지 경로 (designer가 채움) |
| `image_prompt` | 이미지 생성 프롬프트 |
| `z_index` | 레이어 순서 |

#### TextLine
| 필드 | 설명 |
|------|------|
| `line_id` | 텍스트 라인 고유 ID |
| `char_id` | 발화자 캐릭터 ID |
| `text` | 텍스트 내용 (dialogue인 경우 따옴표 포함) |
| `text_type` | `dialogue` 또는 `narration` |
| `emotion` | 감정 |
| `position` | 자막 위치 (top, center, bottom) |
| `audio_url` | TTS 음성 파일 경로 (voice가 채움) |
| `start_ms` | 장면 내 시작 시간 |
| `duration_ms` | 지속 시간 |

#### SFX (Sound Effects)
| 필드 | 설명 |
|------|------|
| `sfx_id` | SFX 고유 ID |
| `tags` | 무드 태그 (예: ['upbeat_chime', 'sparkle']) |
| `audio_url` | SFX 파일 경로 |
| `start_ms` | 시작 시간 |
| `volume` | 볼륨 (0.0-1.0) |

---

## 데이터 변환 과정

### 1단계: GPT 생성 (plot_generator.py)

```python
generate_plot_with_characters(
    run_id="20251106_1931_강아지와고양이의",
    prompt="강아지와 고양이의 우정 이야기",
    num_characters=2,
    num_cuts=3,
    mode="story"
)
```

**출력:**
- `characters.json`: 캐릭터 정의
- `plot.json`: 장면별 시나리오

### 2단계: JSON 변환 (json_converter.py)

```python
convert_plot_to_json(
    plot_json_path="app/data/outputs/.../plot.json",
    run_id="20251106_1931_강아지와고양이의",
    art_style="파스텔 수채화",
    music_genre="ambient"
)
```

**처리:**
1. `characters.json` 로드
2. `plot.json` 로드
3. 장면별 이미지 프롬프트 생성 (`appearance + expression + pose`)
4. 자막 포맷팅 (대사는 따옴표 추가)
5. SFX 태그 자동 추출
6. Timeline 계산

**출력:**
- `layout.json`: 최종 합성용 데이터

### 3단계: 에셋 생성 (병렬)

- **Designer** (designer.py): `image_prompt` 기반 Gemini 이미지 생성
- **Voice** (voice.py): `text` 기반 ElevenLabs TTS 생성
- **Composer** (composer.py): ElevenLabs BGM 생성

### 4단계: 영상 합성 (director.py)

`layout.json`의 모든 정보를 사용하여 MoviePy로 최종 영상 합성:
- 이미지 레이어링
- 한글 자막 오버레이
- 음성 타이밍 동기화
- BGM 믹싱

---

## 프롬프트 가이드라인

### 캐릭터 생성 프롬프트

- **appearance**: 이미지 생성에 직접 사용되므로 **상세하게** 작성
- **personality**: 캐릭터 일관성 유지용

### 플롯 생성 프롬프트

- **expression/pose**: 이미지 생성 프롬프트에 추가됨
- **해설자**: `expression="none"`, `pose="none"`으로 설정
- **text**: 자연스러운 대사/해설 작성
- **duration_ms**: 텍스트 길이에 맞게 4000-6000ms 권장

---

## 파일 위치

```
backend/app/data/outputs/{run_id}/
├── characters.json      # 캐릭터 정의
├── plot.json            # 장면 시나리오
├── layout.json          # 최종 합성 데이터
├── scene_1_center.png   # 생성된 이미지
├── scene_2_center.png
├── scene_3_center.png
├── audio/
│   ├── scene_1_scene_1_line_1.mp3  # TTS 음성
│   ├── scene_2_scene_2_line_1.mp3
│   ├── scene_3_scene_3_line_1.mp3
│   └── global_bgm.mp3   # 배경음악
└── final_video.mp4      # 최종 영상
```

---

## 스키마 버전

- **Version**: 1.0
- **Last Updated**: 2025-11-06
- **Compatible With**: Kurz AI Studio v0.1.0

---

## 참고 문서

- [ARCHITECTURE.md](./ARCHITECTURE.md) - 전체 시스템 구조
- [WORKFLOW.md](./WORKFLOW.md) - 워크플로우 상세 설명
- [API.md](./API.md) - API 엔드포인트
