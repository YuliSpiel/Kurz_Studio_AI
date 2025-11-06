"""
JSON conversion utilities with characters.json support.
"""
import logging
import json
from pathlib import Path
from typing import List, Dict

from app.utils.seeds import generate_char_seed, generate_bg_seed
from app.utils.sfx_tags import extract_sfx_tags

logger = logging.getLogger(__name__)


def convert_plot_to_json(
    plot_json_path: str,
    run_id: str,
    art_style: str = "파스텔 수채화",
    music_genre: str = "ambient"
) -> Path:
    """
    Convert plot.json and characters.json to final layout.json.

    Args:
        plot_json_path: Path to plot.json file
        run_id: Run identifier
        art_style: Art style for image generation
        music_genre: Music genre for BGM

    Returns:
        Path to generated layout.json file
    """
    logger.info(f"Converting plot.json to layout.json: {plot_json_path}")

    plot_json_path = Path(plot_json_path)
    characters_json_path = plot_json_path.parent / "characters.json"

    # Read characters.json
    characters_data = []
    if characters_json_path.exists():
        logger.info(f"Loading characters from: {characters_json_path}")
        with open(characters_json_path, "r", encoding="utf-8") as f:
            char_json = json.load(f)
            characters_data = char_json.get("characters", [])
    else:
        logger.warning(f"characters.json not found")

    # Read plot JSON
    with open(plot_json_path, "r", encoding="utf-8") as f:
        plot_data = json.load(f)

    rows = plot_data.get("scenes", [])
    if not rows:
        raise ValueError("Plot JSON has no scenes")

    # Build JSON structure
    from app.schemas.json_layout import (
        ShortsJSON, Timeline, Character, Scene, ImageSlot,
        TextLine, BGM
    )

    # Build characters list
    characters = []
    if characters_data:
        # Use characters from characters.json
        for char in characters_data:
            characters.append(
                Character(
                    char_id=char["char_id"],
                    name=char["name"],
                    persona=char.get("personality", f"{char['name']} 설정"),
                    voice_profile=char.get("voice_profile", "default"),
                    seed=char.get("seed", generate_char_seed(char["char_id"]))
                ).model_dump()
            )
    else:
        # Fallback: extract from plot JSON
        characters_set = set()
        for row in rows:
            char_id = row["char_id"]
            char_name = row.get("char_name", "Character")
            characters_set.add((char_id, char_name))

        for char_id, char_name in sorted(characters_set):
            characters.append(
                Character(
                    char_id=char_id,
                    name=char_name,
                    persona=f"{char_name} 설정",
                    voice_profile="default",
                    seed=generate_char_seed(char_id)
                ).model_dump()
            )

    # Build scenes
    scenes_data: Dict[str, List[dict]] = {}
    for row in rows:
        scene_id = row["scene_id"]
        if scene_id not in scenes_data:
            scenes_data[scene_id] = []
        scenes_data[scene_id].append(row)

    scenes = []
    total_duration = 0

    # Detect schema type from first row
    first_scene_row = rows[0] if rows else {}
    is_story_mode = "char1_id" in first_scene_row and "speaker" in first_scene_row

    for scene_id, scene_rows in sorted(scenes_data.items(), key=lambda x: int(x[0].split("_")[1])):
        first_row = scene_rows[0]
        sequence = int(scene_id.split("_")[1])
        # duration_ms with fallback to default 5000ms
        duration_ms = int(first_row.get("duration_ms") or 5000)
        total_duration += duration_ms

        # Create text lines (통합: 대사 + 해설)
        texts = []
        for idx, row in enumerate(scene_rows):
            line_id = f"{scene_id}_line_{idx+1}"
            text = row["text"]
            text_type = row.get("text_type", "dialogue")

            # text_type이 dialogue일 경우에만 큰따옴표 추가
            display_text = f'"{text}"' if text_type == "dialogue" else text

            # Determine char_id for voice selection
            if is_story_mode:
                speaker = row.get("speaker", "narration")
                # Convert speaker format to char_id (char_1 -> char_1)
                voice_char_id = speaker if speaker != "narration" else "narrator"
            else:
                voice_char_id = row["char_id"]

            texts.append(
                TextLine(
                    line_id=line_id,
                    char_id=voice_char_id,
                    text=display_text,
                    text_type=text_type,
                    emotion=row.get("emotion", "neutral"),
                    position=row.get("subtitle_position", "bottom"),
                    audio_url="",  # Will be filled by voice task
                    start_ms=idx * 2000,
                    duration_ms=duration_ms
                ).model_dump()
            )

        # Create image slots
        images = []

        if is_story_mode:
            # Story Mode: Multiple characters with positioning
            char1_id = first_row.get("char1_id")
            char2_id = first_row.get("char2_id")

            # Position mapping for x-coordinate (for multi-character scenes)
            position_map = {
                "left": 0.25,
                "center": 0.5,
                "right": 0.75
            }

            # Add char1 if present
            if char1_id:
                char1_appearance = ""
                for char in characters_data:
                    if char["char_id"] == char1_id:
                        char1_appearance = char.get("appearance", "")
                        break

                char1_expr = first_row.get("char1_expression", "neutral")
                char1_pose = first_row.get("char1_pose", "standing")
                char1_pos = first_row.get("char1_pos", "center")

                # Character image: no background, character only
                char1_prompt = f"{char1_appearance}, {char1_expr} expression, {char1_pose} pose, transparent background, character cutout, full body" if char1_appearance else ""

                char1_slot = ImageSlot(
                    slot_id=f"{char1_id}_slot",
                    type="character",
                    ref_id=char1_id,
                    image_url="",
                    z_index=2
                ).model_dump()
                char1_slot["image_prompt"] = char1_prompt
                char1_slot["position"] = char1_pos
                char1_slot["x_pos"] = position_map.get(char1_pos, 0.5)
                images.append(char1_slot)

            # Add char2 if present
            if char2_id:
                char2_appearance = ""
                for char in characters_data:
                    if char["char_id"] == char2_id:
                        char2_appearance = char.get("appearance", "")
                        break

                char2_expr = first_row.get("char2_expression", "neutral")
                char2_pose = first_row.get("char2_pose", "standing")
                char2_pos = first_row.get("char2_pos", "right")

                # Character image: no background, character only
                char2_prompt = f"{char2_appearance}, {char2_expr} expression, {char2_pose} pose, transparent background, character cutout, full body" if char2_appearance else ""

                char2_slot = ImageSlot(
                    slot_id=f"{char2_id}_slot",
                    type="character",
                    ref_id=char2_id,
                    image_url="",
                    z_index=2
                ).model_dump()
                char2_slot["image_prompt"] = char2_prompt
                char2_slot["position"] = char2_pos
                char2_slot["x_pos"] = position_map.get(char2_pos, 0.75)
                images.append(char2_slot)

            # Add background image slot
            background_img = first_row.get("background_img", "simple background")
            bg_slot = ImageSlot(
                slot_id="background",
                type="background",
                ref_id=scene_id,
                image_url="",
                z_index=0
            ).model_dump()
            bg_slot["image_prompt"] = background_img
            images.insert(0, bg_slot)  # Background goes first (z_index 0)

        else:
            # Legacy Mode: Single character centered
            char_id = first_row["char_id"]
            char_appearance = ""
            if characters_data:
                for char in characters_data:
                    if char["char_id"] == char_id:
                        char_appearance = char.get("appearance", "")
                        break

            expression = first_row.get("expression", "neutral")
            pose = first_row.get("pose", "standing")

            # Build image prompt (character only, no background for cutout composition)
            if char_appearance and expression != "none" and pose != "none":
                image_prompt = f"{char_appearance}, {expression} expression, {pose} pose, transparent background, character cutout, full body"
            elif char_appearance:
                image_prompt = f"{char_appearance}, transparent background, character cutout, full body"
            else:
                image_prompt = ""

            images = [
                ImageSlot(
                    slot_id="center",
                    type="character",
                    ref_id=char_id,
                    image_url="",  # Will be filled by designer
                    z_index=1
                ).model_dump()
            ]

            # Store image_prompt in metadata (for designer task)
            images[0]["image_prompt"] = image_prompt

        # SFX
        sfx_list = []
        sfx_tags = extract_sfx_tags(first_row["text"], first_row.get("emotion", "neutral"))
        if sfx_tags:
            from app.schemas.json_layout import SFX
            sfx_list.append(
                SFX(
                    sfx_id=f"{scene_id}_sfx",
                    tags=sfx_tags,
                    audio_url="",
                    start_ms=0,
                    volume=0.5
                ).model_dump()
            )

        # Create scene
        scene = Scene(
            scene_id=scene_id,
            sequence=sequence,
            duration_ms=duration_ms,
            images=images,
            texts=texts,
            bgm=None,
            sfx=sfx_list,
            bg_seed=generate_bg_seed(sequence),
            transition="fade"
        )

        scenes.append(scene.model_dump())

    # Create timeline
    timeline = Timeline(
        total_duration_ms=total_duration,
        aspect_ratio="9:16",
        fps=30,
        resolution="1080x1920"
    )

    # Create final JSON
    shorts_json = ShortsJSON(
        project_id=run_id,
        title=f"AutoShorts {run_id}",
        mode="story",
        timeline=timeline.model_dump(),
        characters=characters,
        scenes=scenes,
        global_bgm=None,
        metadata={
            "art_style": art_style,
            "music_genre": music_genre,
            "generated_from": str(plot_json_path),
            "characters_file": str(characters_json_path) if characters_json_path.exists() else None
        }
    )

    # Write layout JSON
    json_path = plot_json_path.parent / "layout.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(shorts_json.model_dump(), f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Layout JSON generated: {json_path}")
    return json_path
