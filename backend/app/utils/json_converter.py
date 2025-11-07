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

    # Extract bgm_prompt if present (General/Ad Mode)
    bgm_prompt = plot_data.get("bgm_prompt")

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

    # Cache for previous scene values (for Story Mode)
    cache = {
        "char1_id": None,
        "char1_expression": "neutral",
        "char1_pose": "standing",
        "char1_pos": "center",
        "char2_id": None,
        "char2_expression": "neutral",
        "char2_pose": "standing",
        "char2_pos": "right",
        "background_img": "simple background"
    }

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
                # Keep speaker as-is (char_1, char_2, narration)
                voice_char_id = speaker
            else:
                # General/Ad Mode: use "speaker" field
                speaker = row.get("speaker", "narration")
                voice_char_id = speaker

            texts.append(
                TextLine(
                    line_id=line_id,
                    char_id=voice_char_id,
                    text=display_text,
                    text_type=text_type,
                    emotion=row.get("emotion", "neutral"),
                    position="top",  # Always top position
                    audio_url="",  # Will be filled by voice task
                    start_ms=idx * 2000,
                    duration_ms=duration_ms
                ).model_dump()
            )

        # Create image slots
        images = []

        if is_story_mode:
            # Story Mode: Multiple characters with positioning
            # Get values from plot, use cache if empty string ""
            char1_id_raw = first_row.get("char1_id")
            char1_id = char1_id_raw if char1_id_raw else cache["char1_id"]

            char1_expr_raw = first_row.get("char1_expression", "neutral")
            char1_expr = char1_expr_raw if char1_expr_raw else cache["char1_expression"]

            char1_pose_raw = first_row.get("char1_pose", "standing")
            char1_pose = char1_pose_raw if char1_pose_raw else cache["char1_pose"]

            char1_pos_raw = first_row.get("char1_pos", "center")
            char1_pos = char1_pos_raw if char1_pos_raw else cache["char1_pos"]

            char2_id_raw = first_row.get("char2_id")
            char2_id = char2_id_raw if char2_id_raw else cache["char2_id"]

            char2_expr_raw = first_row.get("char2_expression", "neutral")
            char2_expr = char2_expr_raw if char2_expr_raw else cache["char2_expression"]

            char2_pose_raw = first_row.get("char2_pose", "standing")
            char2_pose = char2_pose_raw if char2_pose_raw else cache["char2_pose"]

            char2_pos_raw = first_row.get("char2_pos", "right")
            char2_pos = char2_pos_raw if char2_pos_raw else cache["char2_pos"]

            background_img_raw = first_row.get("background_img")  # Can be None, "", or actual value
            # Use cache if null or empty string
            if background_img_raw is None or background_img_raw == "":
                background_img = cache["background_img"]
            else:
                background_img = background_img_raw

            # Update cache with new values (only if not null and not empty)
            if char1_id_raw is not None:
                cache["char1_id"] = char1_id
            if char1_expr_raw:
                cache["char1_expression"] = char1_expr
            if char1_pose_raw:
                cache["char1_pose"] = char1_pose
            if char1_pos_raw:
                cache["char1_pos"] = char1_pos
            if char2_id_raw is not None:
                cache["char2_id"] = char2_id
            if char2_expr_raw:
                cache["char2_expression"] = char2_expr
            if char2_pose_raw:
                cache["char2_pose"] = char2_pose
            if char2_pos_raw:
                cache["char2_pos"] = char2_pos
            if background_img_raw:  # Update cache only if not null and not empty
                cache["background_img"] = background_img_raw

            # Position mapping for x-coordinate (for multi-character scenes)
            # Adjusted for better separation with 2:3 aspect ratio character images
            position_map = {
                "left": 0.2,      # 화면 왼쪽 20%
                "center": 0.5,    # 정중앙 50%
                "right": 0.8      # 화면 오른쪽 80%
            }

            # Add char1 if present (and not null)
            if char1_id:
                char1_appearance = ""
                for char in characters_data:
                    if char["char_id"] == char1_id:
                        char1_appearance = char.get("appearance", "")
                        break

                # Character image (background will be removed by rembg)
                # Fixed framing with strict composition rules
                char1_prompt = f"{char1_appearance}, {char1_expr} expression, {char1_pose} pose, head to mid-thigh portrait, face at upper third of frame, body centered and fully visible, consistent scale, pure white background" if char1_appearance else ""

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

            # Add char2 if present (and not null)
            if char2_id:
                char2_appearance = ""
                for char in characters_data:
                    if char["char_id"] == char2_id:
                        char2_appearance = char.get("appearance", "")
                        break

                # Character image (background will be removed by rembg)
                # Fixed framing with strict composition rules
                char2_prompt = f"{char2_appearance}, {char2_expr} expression, {char2_pose} pose, head to mid-thigh portrait, face at upper third of frame, body centered and fully visible, consistent scale, pure white background" if char2_appearance else ""

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

            # Add background image slot (always present)
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
            # General Mode: Use image_prompt directly from plot.json
            # The image_prompt is already provided in the scene data
            image_prompt_raw = first_row.get("image_prompt", "")

            # If image_prompt is empty string "", reuse previous scene's image
            # (handled by designer - we still create the slot but mark it for reuse)
            if image_prompt_raw == "" and sequence > 1:
                # Empty prompt means reuse previous image
                logger.debug(f"Scene {scene_id}: Empty image_prompt, will reuse previous image")
                image_prompt = ""  # Designer will handle reuse
            else:
                # Use provided prompt or fallback
                image_prompt = image_prompt_raw if image_prompt_raw else "simple background"

            # Create single image slot for the scene (1:1 ratio, white background)
            images = [
                ImageSlot(
                    slot_id="scene",
                    type="scene",  # Unified scene image type
                    ref_id=scene_id,
                    image_url="",  # Will be filled by designer
                    z_index=0
                ).model_dump()
            ]

            # Store image_prompt for designer task
            images[0]["image_prompt"] = image_prompt
            # Add metadata for general mode image generation
            images[0]["aspect_ratio"] = "1:1"  # General mode uses 1:1 images
            images[0]["background"] = "white"  # White background for transparency removal

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
    metadata_dict = {
        "art_style": art_style,
        "music_genre": music_genre,
        "generated_from": str(plot_json_path),
        "characters_file": str(characters_json_path) if characters_json_path.exists() else None
    }

    # Add bgm_prompt if present (General/Ad Mode)
    if bgm_prompt:
        metadata_dict["bgm_prompt"] = bgm_prompt
        logger.info(f"Added bgm_prompt to metadata: {bgm_prompt}")

    # Determine mode from schema detection
    mode_value = "story" if is_story_mode else "general"
    logger.info(f"Layout mode: {mode_value}")

    shorts_json = ShortsJSON(
        project_id=run_id,
        title=f"AutoShorts {run_id}",
        mode=mode_value,
        timeline=timeline.model_dump(),
        characters=characters,
        scenes=scenes,
        global_bgm=None,
        metadata=metadata_dict
    )

    # Write layout JSON
    json_path = plot_json_path.parent / "layout.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(shorts_json.model_dump(), f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Layout JSON generated: {json_path}")
    return json_path
