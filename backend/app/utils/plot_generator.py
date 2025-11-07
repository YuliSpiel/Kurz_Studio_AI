"""
Plot generation utilities with character separation.
Generates characters.json and plot.json from user prompts.
"""
import logging
import json
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


def generate_plot_with_characters(
    run_id: str,
    prompt: str,
    num_characters: int,
    num_cuts: int,
    mode: str = "story",
    characters: list = None
) -> Tuple[Path, Path]:
    """
    Generate characters.json and plot.json from user prompt using GPT-4o-mini.

    Args:
        run_id: Run identifier
        prompt: User prompt
        num_characters: Number of characters
        num_cuts: Number of scenes/cuts
        mode: story or ad
        characters: Optional list of user-provided character data (Story Mode)

    Returns:
        Tuple of (characters_json_path, plot_json_path)
    """
    logger.info(f"Generating plot with characters for: {prompt[:50]}...")

    output_dir = Path(f"app/data/outputs/{run_id}")
    output_dir.mkdir(parents=True, exist_ok=True)

    characters_path = output_dir / "characters.json"
    plot_path = output_dir / "plot.json"

    try:
        from openai import OpenAI
        from app.config import settings

        if not settings.OPENAI_API_KEY:
            raise ValueError("No OpenAI API key")

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Step 1: Generate or use provided characters
        if characters:
            # Story Mode: Use user-provided characters
            logger.info("Step 1: Using provided characters (Story Mode)...")
            characters_data = {
                "characters": [
                    {
                        "char_id": f"char_{i+1}",
                        "name": char["name"],
                        "appearance": char["appearance"],
                        "personality": char["personality"],
                        "voice_profile": "default",  # Will be matched by voice.py
                        "seed": 1002 + i,
                        "gender": char.get("gender", "other"),
                        "role": char.get("role", "")
                    }
                    for i, char in enumerate(characters)
                ]
            }
            with open(characters_path, "w", encoding="utf-8") as f:
                json.dump(characters_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Characters saved: {characters_path}")
        else:
            # Auto-generate characters
            char_prompt = f"""당신은 숏폼 영상 콘텐츠의 캐릭터 디자이너입니다.
사용자의 요청에 맞는 {num_characters}명의 캐릭터를 만들어주세요.

각 캐릭터마다 다음 정보를 JSON 형식으로 제공하세요:
- char_id: char_1, char_2, ... 형식
- name: 캐릭터 이름 (창의적으로)
- appearance: 외형 묘사 (이미지 생성 프롬프트용, 상세하게)
- personality: 성격/특징
- voice_profile: "default"
- seed: char_1은 1002, char_2는 1003, ...

**중요**:
- 반드시 JSON 형식으로만 출력
- appearance는 이미지 생성 프롬프트로 사용되므로 시각적 특징 상세 작성
- 해설자는 appearance를 "음성만 있는 해설자 (이미지 없음)"으로 설정

JSON 형식:
{{
  "characters": [
    {{
      "char_id": "char_1",
      "name": "캐릭터 이름",
      "appearance": "상세한 외형 묘사",
      "personality": "성격 설명",
      "voice_profile": "default",
      "seed": 1002
    }}
  ]
}}"""

            logger.info("Step 1: Generating characters...")
            char_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": char_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            char_json_content = char_response.choices[0].message.content.strip()

            # Remove markdown code blocks if present
            if char_json_content.startswith("```"):
                lines = char_json_content.split("\n")
                char_json_content = "\n".join([line for line in lines if not line.startswith("```")])

            # Parse and save characters
            characters_data = json.loads(char_json_content)
            with open(characters_path, "w", encoding="utf-8") as f:
                json.dump(characters_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Characters generated: {characters_path}")

        # Step 2: Generate plot JSON
        char_names = ", ".join([c["name"] for c in characters_data["characters"]])
        char_list = "\n".join([f"- {c['char_id']}: {c['name']} ({c.get('role', c['personality'])})"
                               for c in characters_data["characters"]])

        # Add detailed character information when user provides characters
        char_details = ""
        if characters:
            char_details = "\n\n캐릭터 세부정보 (반드시 이 설정 그대로 사용할 것):\n"
            for c in characters_data["characters"]:
                char_details += f"- {c['name']} ({c['char_id']})\n"
                char_details += f"  외형: {c['appearance']}\n"
                char_details += f"  성격: {c['personality']}\n"
                if c.get('role'):
                    char_details += f"  역할: {c['role']}\n"
                char_details += "\n"

        # Use new schema for Story Mode
        logger.info(f"[DEBUG] Preparing plot generation: mode='{mode}', characters={'provided' if characters else 'None'}, num_cuts={num_cuts}")
        if mode == "story":
            logger.info("[DEBUG] ✅ Using STORY MODE prompt (char1_id/char2_id/speaker/background_img schema)")
            plot_prompt = f"""당신은 비주얼노벨 스타일 숏폼 영상 시나리오 작가입니다.
사용자의 스토리를 {num_cuts}개 장면으로 나누어 시나리오를 만들어주세요.

등장인물:
{char_list}{char_details}

각 장면마다 다음 정보를 JSON 형식으로 제공하세요:
- scene_id: scene_1, scene_2, ... 형식
- char1_id: 첫 번째 캐릭터 ID (char_1, char_2, char_3 중 하나, 또는 null)
- char1_pos: 위치 (left, center, right 중 하나, 또는 "" = 이전 위치 유지)
- char1_expression: 표정 (excited, happy, sad, angry, surprised, neutral, confident 등, 또는 "" = 이전 표정 유지)
- char1_pose: 포즈 (standing, sitting, walking, pointing 등, 또는 "" = 이전 포즈 유지)
- char2_id: 두 번째 캐릭터 ID (char_1, char_2, char_3 중 하나, 또는 null = 캐릭터 없음)
- char2_pos: 위치 (left, center, right 중 하나, 또는 "" = 이전 위치 유지)
- char2_expression: 표정 ("" = 이전 표정 유지)
- char2_pose: 포즈 ("" = 이전 포즈 유지)
- speaker: 발화자 (narration, char_1, char_2, char_3 중 하나)
- text: 대사 또는 해설 내용
- text_type: dialogue (대사) 또는 narration (해설)
- emotion: neutral, happy, sad, excited, angry, surprised 중 하나
- subtitle_position: 항상 "top" (자막은 항상 상단에 표시)
- duration_ms: 장면 지속시간 (4000-6000)
- background_img: 배경 이미지 생성 프롬프트 (예: "calm farm", "busy city street", 또는 "" = 이전 배경 유지)

**중요 규칙**:
1. **캐릭터 배치**:
   - 모든 장면에 모든 캐릭터를 넣지 마세요. 스토리 흐름에 따라 필요한 캐릭터만 배치
   - 혼자 독백하거나 클로즈업이 필요하면 char1_id만 사용하고 char2_id는 null
   - 두 캐릭터가 대화할 때만 char1_id와 char2_id 모두 사용
   - 해설(narration)일 때는 캐릭터 없이 배경만 보여줄 수 있음 (char1_id, char2_id 모두 null)

2. **위치 충돌 방지**:
   - 두 캐릭터가 동시에 등장하면 반드시 다른 위치에 배치 (예: char1_pos="left", char2_pos="right")
   - 한 명만 등장하면 "center" 사용 가능
   - 절대 같은 위치에 두 캐릭터를 배치하지 마세요 (겹침)

3. **배경 재사용**:
   - 배경은 분위기가 바뀔 때만 변경하세요
   - 같은 장소에서 계속 대화하면 background_img를 ""로 두어 이전 배경 유지
   - 장소 이동이나 시간 변화가 있을 때만 새로운 배경 프롬프트 작성

4. **표정/포즈 캐싱**:
   - 캐릭터의 표정이나 포즈가 이전 장면과 같으면 ""로 두어 재사용
   - 변화가 있을 때만 새로운 값 입력

5. **기타**:
   - 반드시 JSON 형식으로만 출력
   - background_img는 간결한 영어 프롬프트로 작성 (5-10 단어)
   - 위에 제공된 캐릭터 세부정보가 있다면 반드시 그 이름, 성격, 역할을 그대로 사용할 것

JSON 예시:
{{
  "scenes": [
    {{
      "scene_id": "scene_1",
      "char1_id": "char_1",
      "char1_pos": "center",
      "char1_expression": "excited",
      "char1_pose": "standing",
      "char2_id": null,
      "char2_pos": null,
      "char2_expression": null,
      "char2_pose": null,
      "speaker": "char_1",
      "text": "안녕! 나는 용감한 고양이야!",
      "text_type": "dialogue",
      "emotion": "happy",
      "subtitle_position": "top",
      "duration_ms": 5000,
      "background_img": "sunny playground with swings"
    }},
    {{
      "scene_id": "scene_2",
      "char1_id": "char_1",
      "char1_pos": "left",
      "char1_expression": "happy",
      "char1_pose": "",
      "char2_id": "char_2",
      "char2_pos": "right",
      "char2_expression": "surprised",
      "char2_pose": "standing",
      "speaker": "char_2",
      "text": "우주로 출발하자!",
      "text_type": "dialogue",
      "emotion": "excited",
      "subtitle_position": "top",
      "duration_ms": 4500,
      "background_img": ""
    }},
    {{
      "scene_id": "scene_3",
      "char1_id": null,
      "char1_pos": null,
      "char1_expression": null,
      "char1_pose": null,
      "char2_id": null,
      "char2_pos": null,
      "char2_expression": null,
      "char2_pose": null,
      "speaker": "narration",
      "text": "그들은 함께 우주선을 타고 떠났다.",
      "text_type": "narration",
      "emotion": "neutral",
      "subtitle_position": "top",
      "duration_ms": 5000,
      "background_img": "starry night sky with rocket launching"
    }}
  ]
}}"""
        else:
            # Legacy schema for normal/ad modes
            logger.info(f"[DEBUG] ⚠️ Using LEGACY MODE prompt (char_id/expression/pose schema) for mode='{mode}'")
            plot_prompt = f"""당신은 숏폼 영상 콘텐츠 시나리오 작가입니다.
사용자의 요청을 {num_cuts}개 장면으로 나누어 {'광고' if mode == 'ad' else '영상'}를 만들어주세요.

등장인물: {char_names}

각 장면마다 다음 정보를 JSON 형식으로 제공하세요:
- scene_id: scene_1, scene_2, ... 형식
- char_id: char_1, char_2 (등장인물 ID)
- expression: 표정 (excited, happy, sad, angry, surprised, neutral, amazed, confident, brave 등)
- pose: 포즈 (standing, sitting, walking, running, pointing, looking_up, fist_raised 등, 해설자는 none)
- text: 대사 또는 해설 내용
- text_type: dialogue (대사) 또는 narration (해설)
- emotion: neutral, happy, sad, excited, angry, surprised 중 하나
- subtitle_position: 항상 "top" (자막은 항상 상단에 표시)
- duration_ms: 장면 지속시간 (4000-6000)

**중요**:
- 반드시 JSON 형식으로만 출력
- 해설자의 expression/pose는 "none"으로 설정

JSON 형식:
{{
  "scenes": [
    {{
      "scene_id": "scene_1",
      "char_id": "char_1",
      "expression": "excited",
      "pose": "standing",
      "text": "안녕! 나는 용감한 고양이야!",
      "text_type": "dialogue",
      "emotion": "happy",
      "subtitle_position": "top",
      "duration_ms": 5000
    }},
    {{
      "scene_id": "scene_2",
      "char_id": "char_2",
      "expression": "happy",
      "pose": "walking",
      "text": "우주로 출발하자!",
      "text_type": "dialogue",
      "emotion": "excited",
      "subtitle_position": "top",
      "duration_ms": 4500
    }}
  ]
}}"""

        logger.info("Step 2: Generating plot...")
        plot_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": plot_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=2000
        )

        plot_json_content = plot_response.choices[0].message.content.strip()

        # Remove markdown code blocks if present
        if plot_json_content.startswith("```"):
            lines = plot_json_content.split("\n")
            plot_json_content = "\n".join([line for line in lines if not line.startswith("```")])

        # Parse and save plot JSON
        plot_data = json.loads(plot_json_content)
        with open(plot_path, "w", encoding="utf-8") as f:
            json.dump(plot_data, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Plot generated: {plot_path}")
        logger.info(f"Generated {len(plot_data.get('scenes', []))} scenes")

        return characters_path, plot_path

    except Exception as e:
        logger.warning(f"GPT generation failed: {e}, using fallback with mode='{mode}'")
        return _generate_fallback(output_dir, prompt, num_characters, num_cuts, mode, characters)


def _generate_fallback(
    output_dir: Path,
    prompt: str,
    num_characters: int,
    num_cuts: int,
    mode: str,
    characters: list = None
) -> Tuple[Path, Path]:
    """
    Fallback: rule-based generation when GPT fails.
    """
    logger.info(f"[DEBUG] Fallback generation: mode='{mode}', num_cuts={num_cuts}")
    characters_path = output_dir / "characters.json"
    plot_path = output_dir / "plot.json"

    # Generate simple characters
    if characters:
        # Use provided characters
        characters_data = {
            "characters": [
                {
                    "char_id": f"char_{i+1}",
                    "name": char["name"],
                    "appearance": char["appearance"],
                    "personality": char["personality"],
                    "voice_profile": "default",
                    "seed": 1002 + i,
                    "gender": char.get("gender", "other"),
                    "role": char.get("role", "")
                }
                for i, char in enumerate(characters)
            ]
        }
    else:
        # Auto-generate characters
        characters_data = {
            "characters": [
                {
                    "char_id": f"char_{i+1}",
                    "name": f"캐릭터 {i+1}",
                    "appearance": f"캐릭터 {i+1}의 외형",
                    "personality": f"캐릭터 {i+1}의 성격",
                    "voice_profile": "default",
                    "seed": 1002 + i
                }
                for i in range(num_characters)
            ]
        }

    with open(characters_path, "w", encoding="utf-8") as f:
        json.dump(characters_data, f, indent=2, ensure_ascii=False)

    # Generate simple plot
    scenes = []
    for i in range(num_cuts):
        scene_id = f"scene_{i+1}"
        char_id = f"char_{(i % num_characters) + 1}"

        if mode == "story":
            # Story Mode: Use new schema
            logger.debug(f"[DEBUG] Fallback: generating story mode scene {i+1}")
            scenes.append({
                "scene_id": scene_id,
                "char1_id": char_id,
                "char1_pos": "center",
                "char1_expression": "neutral",
                "char1_pose": "standing",
                "char2_id": None,
                "char2_pos": None,
                "char2_expression": None,
                "char2_pose": None,
                "speaker": char_id,
                "text": f"{prompt}의 {i+1}번째 장면입니다.",
                "text_type": "dialogue",
                "emotion": "neutral" if i % 2 == 0 else "happy",
                "subtitle_position": "top",
                "duration_ms": 5000,
                "background_img": "simple background"
            })
        else:
            # Legacy schema for normal/ad modes
            scenes.append({
                "scene_id": scene_id,
                "char_id": char_id,
                "expression": "neutral",
                "pose": "standing",
                "text": f"{prompt}의 {i+1}번째 장면입니다.",
                "text_type": "dialogue",
                "emotion": "neutral" if i % 2 == 0 else "happy",
                "subtitle_position": "top",
                "duration_ms": 5000
            })

    plot_data = {"scenes": scenes}
    with open(plot_path, "w", encoding="utf-8") as f:
        json.dump(plot_data, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Fallback generation complete")
    return characters_path, plot_path
