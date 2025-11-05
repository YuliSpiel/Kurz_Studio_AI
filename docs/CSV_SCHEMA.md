# CSV 데이터 스키마 설계 문서

## 개요
AutoShorts 영상 생성을 위한 CSV 스키마 정의.
GPT가 시나리오를 생성하고, 각 에이전트가 이를 기반으로 이미지/음성/음악을 생성함.

---

## 📋 CSV 필드 정의

### 1. 기본 정보
| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `scene_id` | string | 씬 고유 ID | `scene_1`, `scene_2`, ... |
| `image_id` | string | 이미지 고유 ID (캐싱용) | `img_001`, `""` (재사용), `null` (비우기) |
| `title` | string | 씬 제목 | `오프닝`, `마을 도착` |

### 2. 배경 정보
| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `bg_prompt` | string | 배경 묘사 | `숲속 풍경, 햇살이 비치는`, `중세 마을` |

### 3. 캐릭터 정보
| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `char_id` | string | 캐릭터 고유 ID | `char_hero`, `char_elder` |
| `char_name` | string | 캐릭터 이름 | `주인공`, `현명한 노인` |
| `char_persona` | string | 외모 상세 설명 | `젊은 남성, 갈색 머리, 파란 눈, 갑옷` |
| `char_pose` | string | 포즈 | `standing`, `sitting`, `walking`, `running` |
| `char_expression` | string | 표정 | `neutral`, `happy`, `sad`, `surprised`, `angry` |
| `char_position` | string | 화면 위치 | `left`, `center`, `right` |
| `char_size` | float | 크기 비율 | `0.5` ~ `1.5` (1.0 = 기본) |

### 4. 이미지 생성 메타데이터
| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `omni_ref_id` | string | OmniGen 레퍼런스 ID (캐릭터 일관성) | `ref_hero`, `ref_elder` |
| `lora_tag` | string | LoRA 스타일 태그 | `anime_style`, `realistic` |

### 5. 대사 및 음성
| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `text` | string | 대사/해설 내용 | `안녕하세요!`, `반갑습니다.` |
| `text_type` | string | 텍스트 타입 | `dialogue` (대사), `narration` (해설) |
| `voice_id` | string | ElevenLabs 음성 ID | `voice_hero`, `voice_elder`, `voice_narrator` |
| `emotion` | string | 음성 감정 | `neutral`, `happy`, `sad` |
| `subtitle_position` | string | 자막 위치 | `top`, `bottom`, `center` |
| `duration_ms` | int | 지속 시간 (밀리초) | `3000`, `5000` |

### 6. 오디오
| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `bgm_prompt` | string | 배경음악 프롬프트 | `cinematic_orchestral`, `peaceful_village` |
| `sfx_prompt` | string | 효과음 | `birds_chirping`, `footsteps`, `door_opening` |

---

## 🔄 캐싱 규칙

### image_id 동작 방식
1. **빈칸 (`""`)**
   - 이전 이미지 재사용
   - 대사만 바뀌고 배경/포즈/표정이 동일할 때

2. **"null"**
   - 명시적으로 이미지 비우기
   - 장면 전환, 텍스트 전용 씬

3. **새 값 (`img_001`, `img_002`, ...)**
   - 새 이미지 생성
   - 배경/포즈/표정이 바뀔 때

### bg_prompt 동작 방식
- **빈칸**: 이전 배경 재사용
- **새 값**: 새 배경 적용

### 기타 필드
- 모든 필드는 **빈칸 = 이전 값 재사용** 원칙
- `char_pose`, `char_expression` 변경 시 → 새 `image_id` 필요

---

## 📝 CSV 예시

```csv
scene_id,image_id,title,bg_prompt,char_id,char_name,char_persona,char_pose,char_expression,char_position,char_size,omni_ref_id,lora_tag,text,text_type,voice_id,emotion,subtitle_position,duration_ms,bgm_prompt,sfx_prompt
scene_1,img_001,오프닝,숲속 풍경 햇살,char_hero,주인공,젊은 남성 갈색머리 파란눈,standing,happy,center,1.0,ref_hero,anime_style,안녕하세요!,dialogue,voice_hero,happy,bottom,3000,cinematic_orchestral,birds_chirping
scene_1,,,,,,,standing,happy,,,,,반갑습니다!,dialogue,voice_hero,neutral,bottom,2000,,
scene_1,img_002,,,,,,,sitting,neutral,,,,,앉아서 얘기할게요.,dialogue,voice_hero,neutral,bottom,3000,,
scene_2,img_003,마을도착,중세 마을 거리,char_hero,주인공,,walking,neutral,left,0.8,ref_hero,anime_style,마을에 도착했어요.,dialogue,voice_hero,neutral,bottom,4000,peaceful_village,footsteps
scene_2,,,,,char_elder,현명한 노인 흰수염,standing,happy,right,1.2,ref_elder,,어서오게.,dialogue,voice_elder,happy,bottom,3000,,
scene_2,,,,,,,,,,,,,,주인공이 마을에 들어서자 노인이 반갑게 맞이한다.,narration,voice_narrator,neutral,top,3000,,
scene_3,null,전환,null,,,,,,,,,,,,,,2000,transition_sound,
```

---

## 🎨 이미지 생성 프롬프트 빌드 로직

### 1. 완전한 프롬프트 생성
```python
def build_image_prompt(scene):
    """씬 정보 → ComfyUI 프롬프트"""

    bg = scene.get("bg_prompt", "")
    char_persona = scene.get("char_persona", "")
    char_pose = scene.get("char_pose", "standing")
    char_expression = scene.get("char_expression", "neutral")
    lora_tag = scene.get("lora_tag", "")

    # 최종 프롬프트
    prompt = f"{bg}, {char_persona}, {char_pose}, {char_expression} expression, {lora_tag}"

    return prompt.strip(", ")
```

### 2. OmniGen 레퍼런스 적용
```python
omni_ref_id = scene.get("omni_ref_id")
if omni_ref_id:
    # 캐릭터 일관성을 위한 레퍼런스 이미지
    ref_image_path = f"app/data/references/{omni_ref_id}.png"
    workflow["ip_adapter"]["image"] = ref_image_path
    workflow["ip_adapter"]["weight"] = 0.8
```

---

## 🔍 이미지 재사용 판별 알고리즘

```python
def should_generate_new_image(current_scene, previous_scene):
    """새 이미지 생성 여부 판단"""

    # 1. image_id가 명시적으로 지정됨
    if current_scene.get("image_id"):
        return True

    # 2. image_id가 빈칸 = 재사용
    if current_scene.get("image_id") == "":
        return False

    # 3. 이미지 관련 필드가 바뀌었는지 확인
    image_fields = [
        "bg_prompt",
        "char_persona",
        "char_pose",
        "char_expression",
        "char_position",
        "char_size",
        "lora_tag"
    ]

    for field in image_fields:
        if current_scene.get(field) != previous_scene.get(field):
            return True

    return False
```

---

## 📹 자막 렌더링 로직

### text_type에 따른 자막 처리

```python
def format_subtitle(text: str, text_type: str) -> str:
    """
    text_type에 따라 자막 포맷 적용.

    Args:
        text: 원본 텍스트
        text_type: 'dialogue' 또는 'narration'

    Returns:
        포맷된 자막 텍스트
    """
    if text_type == "dialogue":
        # 대사인 경우 큰따옴표 추가
        return f'"{text}"'
    else:
        # 해설인 경우 그대로 반환
        return text

# 사용 예시
subtitle_text = format_subtitle("안녕하세요!", "dialogue")
# 결과: "안녕하세요!"

subtitle_text = format_subtitle("주인공이 마을에 도착했다.", "narration")
# 결과: 주인공이 마을에 도착했다.
```

### 자막 위치 규칙

- **dialogue**: 기본적으로 `bottom` (하단)
- **narration**: 기본적으로 `top` 또는 `center` (상단/중앙)

---

## 🎯 GPT 프롬프트 가이드

### CSV 생성 시 GPT에게 주는 지침

```
당신은 숏폼 영상 시나리오 작가입니다. 다음 규칙을 따라 CSV를 생성하세요:

**필수 규칙:**
1. scene_id는 scene_1, scene_2, ... 순차적으로 생성
2. image_id는 다음 규칙을 따름:
   - 새 장면/배경/포즈/표정 → img_001, img_002, ...
   - 대사만 바뀜 → 빈칸 (이전 이미지 재사용)
   - 이미지 없음 → "null"
3. char_pose는 standing, sitting, walking, running, lying 등 자연스러운 동작
4. char_expression은 neutral, happy, sad, surprised, angry, fearful 등
5. 같은 image_id 내에서는 bg_prompt, char_pose, char_expression 동일 유지

**배경음악 규칙:**
- 씬 시작 또는 분위기 전환 시에만 bgm_prompt 작성
- 그 외에는 빈칸 (이전 음악 지속)

**효과음 규칙:**
- 행동에 맞는 자연스러운 효과음 추가
- 예: 걷기=footsteps, 문 열기=door_opening, 새소리=birds_chirping

**대사 규칙:**
- 자연스럽고 간결하게 (15자 이내 권장)
- 같은 씬에서 여러 대사는 행 복제 후 대사만 변경
- text_type 필드로 대사/해설 구분:
  - dialogue: 캐릭터가 말하는 대사 (큰따옴표 없이 텍스트만 입력)
  - narration: 나레이션/해설 (큰따옴표 없이 텍스트만 입력)
- 렌더링 시 text_type이 dialogue인 경우 자막에 큰따옴표 자동 추가
```

---

## 📚 참고사항

### 왜 이 구조인가?

1. **image_id 기반 캐싱**
   - GPT가 명시적으로 제어 가능
   - 디버깅 용이 (어떤 이미지가 재사용되는지 명확)

2. **포즈/표정 분리**
   - 캐릭터 외모(persona)는 고정
   - 포즈/표정만 변경 → 프롬프트 변화 최소화

3. **빈칸 = 재사용 원칙**
   - CSV 간결
   - GPT 생성 부담 감소

### 향후 확장

- **multi_char**: 여러 캐릭터 동시 등장
  - `char1_*`, `char2_*` 필드 추가

- **camera_angle**: 카메라 앵글
  - `close_up`, `wide_shot`, `over_shoulder`

- **lighting**: 조명
  - `day`, `night`, `sunset`, `dramatic`

---

**작성일**: 2025-11-05
**버전**: 1.0
**작성자**: AutoShorts Team
