"""
감독 Agent: Final video composition using MoviePy.
This is the chord callback that runs after all asset generation tasks complete.
"""
import logging
import json
from pathlib import Path

from app.celery_app import celery
from app.orchestrator.fsm import RunState
from app.utils.progress import publish_progress
from app.utils.fonts import get_font_path

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="tasks.director")
def director_task(self, asset_results: list, run_id: str, json_path: str):
    """
    Compose final 9:16 video from all generated assets.

    This task is called as a chord callback after designer, composer, and voice tasks complete.

    Args:
        asset_results: List of results from parallel tasks
        run_id: Run identifier
        json_path: Path to JSON layout with all asset URLs

    Returns:
        Dict with final video URL
    """
    logger.info(f"[{run_id}] Director: Starting video composition...")
    logger.info(f"[{run_id}] Asset results: {asset_results}")
    publish_progress(run_id, progress=0.7, log="감독: 최종 영상 합성 시작...")

    # TEST: 3초 대기
    import time
    time.sleep(3)

    try:
        # Get FSM and transition to RENDERING
        from app.orchestrator.fsm import get_fsm
        fsm = get_fsm(run_id)
        if fsm and fsm.transition_to(RunState.RENDERING):
            logger.info(f"[{run_id}] Transitioned to RENDERING")
            publish_progress(run_id, state="RENDERING", progress=0.75, log="렌더링 단계 시작")

            from app.main import runs
            if run_id in runs:
                runs[run_id]["state"] = fsm.current_state.value
                runs[run_id]["progress"] = 0.7

        # Load JSON
        with open(json_path, "r", encoding="utf-8") as f:
            layout = json.load(f)

        # Get layout customization config
        layout_config = layout.get("metadata", {}).get("layout_config", {})
        use_title_block = layout_config.get("use_title_block", True)  # Default to True for backward compatibility
        title_bg_color = layout_config.get("title_bg_color", "#323296")  # Default dark blue
        title_font_size = layout_config.get("title_font_size", 100)  # Updated default
        subtitle_font_size = layout_config.get("subtitle_font_size", 80)  # Updated default

        # Get font paths from font IDs
        title_font_id = layout_config.get("title_font", "AppleGothic")
        subtitle_font_id = layout_config.get("subtitle_font", "AppleGothic")
        title_font_path = get_font_path(title_font_id)
        subtitle_font_path = get_font_path(subtitle_font_id)

        # DEBUG: Log title configuration
        project_title = layout.get("title", "")
        logger.info(f"[{run_id}] Project title: '{project_title}'")
        logger.info(f"[{run_id}] use_title_block: {use_title_block}")
        logger.info(f"[{run_id}] Layout config: {layout_config}")
        logger.info(f"[{run_id}] Title font: {title_font_id} -> {title_font_path}")
        logger.info(f"[{run_id}] Subtitle font: {subtitle_font_id} -> {subtitle_font_path}")

        # IMPORTANT: Update layout.json with asset URLs from chord results
        # This fixes race condition where parallel tasks overwrite each other's changes
        logger.info(f"[{run_id}] Updating layout.json with asset URLs from chord results...")

        for result in asset_results:
            if not result or "agent" not in result:
                continue

            agent = result["agent"]

            # Update image URLs from designer
            if agent == "designer" and "images" in result:
                for img_result in result["images"]:
                    scene_id = img_result["scene_id"]
                    slot_id = img_result["slot_id"]
                    image_url = img_result["image_url"]

                    # Find scene and update image_url
                    for scene in layout.get("scenes", []):
                        if scene["scene_id"] == scene_id:
                            for img_slot in scene.get("images", []):
                                if img_slot["slot_id"] == slot_id:
                                    img_slot["image_url"] = image_url
                                    logger.info(f"[{run_id}] Updated {scene_id}/{slot_id}: {image_url}")

            # Update audio URLs from voice
            elif agent == "voice" and "voice" in result:
                for voice_result in result["voice"]:
                    scene_id = voice_result["scene_id"]
                    line_id = voice_result["line_id"]
                    audio_url = voice_result["audio_url"]

                    # Find scene and text line, update audio_url
                    for scene in layout.get("scenes", []):
                        if scene["scene_id"] == scene_id:
                            for text_line in scene.get("texts", []):
                                if text_line["line_id"] == line_id:
                                    text_line["audio_url"] = audio_url
                                    logger.info(f"[{run_id}] Updated {scene_id}/{line_id}: {audio_url}")

            # Update BGM from composer
            elif agent == "composer" and "audio" in result:
                for audio_result in result["audio"]:
                    if audio_result["type"] == "bgm":
                        bgm_path = audio_result["path"]
                        # Create global_bgm if it doesn't exist
                        if not layout.get("global_bgm"):
                            layout["global_bgm"] = {
                                "bgm_id": audio_result.get("id", "global_bgm"),
                                "genre": "ambient",
                                "mood": "cinematic",
                                "audio_url": bgm_path,
                                "start_ms": 0,
                                "duration_ms": layout.get("timeline", {}).get("total_duration_ms", 30000),
                                "volume": 0.5
                            }
                            logger.info(f"[{run_id}] Created global BGM entry: {bgm_path}")
                        else:
                            layout["global_bgm"]["audio_url"] = bgm_path
                            logger.info(f"[{run_id}] Updated global BGM: {bgm_path}")

        # Save updated layout.json
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(layout, f, indent=2, ensure_ascii=False)

        logger.info(f"[{run_id}] Layout JSON updated with all asset URLs")

        # Check if we're in stub mode (no real assets)
        from app.config import settings
        # Always use full rendering mode since MoviePy is installed
        stub_mode = False

        if stub_mode:
            logger.info(f"[{run_id}] ===== STUB RENDERING MODE =====")
            logger.info(f"[{run_id}] Video composition summary:")
            logger.info(f"[{run_id}]   Format: 1080x1920 (9:16)")
            logger.info(f"[{run_id}]   FPS: {layout.get('timeline', {}).get('fps', 30)}")
            logger.info(f"[{run_id}]   Scenes: {len(layout.get('scenes', []))}")

            for scene in layout.get("scenes", []):
                scene_id = scene["scene_id"]
                duration_sec = scene["duration_ms"] / 1000.0
                logger.info(f"[{run_id}]   - {scene_id}: {duration_sec}s")
                logger.info(f"[{run_id}]     Images: {len(scene.get('images', []))}")
                logger.info(f"[{run_id}]     Texts: {len(scene.get('texts', []))}")

            global_bgm = layout.get("global_bgm")
            if global_bgm:
                logger.info(f"[{run_id}]   BGM: {global_bgm.get('audio_url', 'N/A')}")

            # Create stub output file
            output_dir = Path(f"app/data/outputs/{run_id}")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "final_video.txt"

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("=== AutoShorts Video Composition Summary ===\n\n")
                f.write(f"Run ID: {run_id}\n")
                f.write(f"Format: 1080x1920 (9:16)\n")
                f.write(f"FPS: {layout.get('timeline', {}).get('fps', 30)}\n\n")

                for scene in layout.get("scenes", []):
                    scene_id = scene["scene_id"]
                    duration_sec = scene["duration_ms"] / 1000.0
                    f.write(f"\n[{scene_id}] ({duration_sec}s)\n")
                    f.write("-" * 40 + "\n")

                    for img_slot in scene.get("images", []):
                        f.write(f"  Image ({img_slot.get('slot_id', 'N/A')}): {img_slot.get('image_url', 'N/A')}\n")

                    for text_line in scene.get("texts", []):
                        f.write(f"  Audio: {text_line.get('audio_url', 'N/A')}\n")
                        f.write(f"    Text: {text_line.get('text', 'N/A')}\n")
                        f.write(f"    Type: {text_line.get('text_type', 'N/A')}\n")

                if global_bgm:
                    f.write(f"\nGlobal BGM: {global_bgm.get('audio_url', 'N/A')}\n")
                    f.write(f"  Volume: {global_bgm.get('volume', 0.3)}\n")

            logger.info(f"[{run_id}] Stub rendering complete: {output_path}")
            logger.info(f"[{run_id}] ===== END STUB RENDERING =====")
            publish_progress(run_id, progress=0.8, log=f"렌더링 완료: {output_path}")

            # Transition to QA
            if fsm and fsm.transition_to(RunState.QA):
                logger.info(f"[{run_id}] Transitioned to QA")
                publish_progress(run_id, state="QA", progress=0.82, log="QA 검수 단계로 전환...")

                from app.main import runs
                if run_id in runs:
                    runs[run_id]["state"] = fsm.current_state.value
                    runs[run_id]["progress"] = 0.82
                    # Set HTTP URL path for frontend to access video
                    runs[run_id]["artifacts"]["video_url"] = f"/outputs/{run_id}/final_video.mp4"

                # Trigger QA task
                from app.tasks.qa import qa_task
                qa_task.apply_async(args=[run_id, str(json_path), str(output_path)])
                logger.info(f"[{run_id}] QA task triggered")

            return {
                "run_id": run_id,
                "agent": "director",
                "video_url": str(output_path),
                "status": "success",
                "mode": "stub"
            }

        # Import MoviePy for composition
        try:
            # Try MoviePy 2.x import
            from moviepy import (
                VideoClip, ImageClip, AudioFileClip, CompositeVideoClip,
                CompositeAudioClip, TextClip, concatenate_videoclips
            )
        except ImportError:
            # Fallback to MoviePy 1.x import
            from moviepy.editor import (
                VideoClip, ImageClip, AudioFileClip, CompositeVideoClip,
                CompositeAudioClip, TextClip, concatenate_videoclips
            )
        import numpy as np

        # Korean font path for subtitles
        KOREAN_FONT = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

        # Video settings (9:16 format)
        width = 1080
        height = 1920
        fps = layout.get("timeline", {}).get("fps", 30)

        # Pre-generate title block clips if needed (to be reused across all scenes)
        title_clips_cache = {}  # {duration_sec: (title_bg_clip, title_clip, title_height)}
        title_text = layout.get("title", "")

        # Log title block configuration at start
        logger.info(f"[{run_id}] === TITLE BLOCK CONFIGURATION ===")
        logger.info(f"[{run_id}] title_text: '{title_text}'")
        logger.info(f"[{run_id}] use_title_block: {use_title_block}")
        logger.info(f"[{run_id}] title_bg_color: {title_bg_color}")
        logger.info(f"[{run_id}] title_font: {title_font_id} -> {title_font_path}")
        logger.info(f"[{run_id}] title_font_size: {title_font_size}")
        logger.info(f"[{run_id}] =====================================")

        # Function to create title block clips for a given duration
        def create_title_block_clips(duration_sec):
            if duration_sec in title_clips_cache:
                return title_clips_cache[duration_sec]

            try:
                # Convert hex color to RGB
                def hex_to_rgb(hex_color):
                    hex_color = hex_color.lstrip('#')
                    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]

                title_rgb = hex_to_rgb(title_bg_color)

                # Create title text (bold and large) with max width to prevent overflow
                max_title_width = int(width * 0.95)  # 95% of width for more space

                # CRITICAL FIX: Give TextClip MUCH MORE HEIGHT than it thinks it needs
                # MoviePy's auto-calculated height is ALWAYS too small for Korean text with strokes
                # We need to manually specify a generous height to prevent clipping
                estimated_text_height = int(title_font_size * 3.5)  # 3.5x font size for generous space

                # NOTE: TextClip with method='caption' supports \n for line breaks
                # This is the correct way to handle multi-line titles
                # MoviePy 2.x doesn't support 'align' parameter - text alignment is handled by positioning
                title_clip = TextClip(
                    text=title_text,
                    font=title_font_path,  # Use selected font
                    font_size=title_font_size,
                    color='white',
                    stroke_color='black',
                    stroke_width=3,
                    size=(max_title_width, estimated_text_height),  # EXPLICIT HEIGHT to prevent clipping
                    method='caption',  # Enable text wrapping and multi-line support
                    duration=duration_sec
                )

                # Calculate title block height - use the explicit height we set
                # Add minimal padding since we already gave generous height to TextClip
                padding_top = 20  # Small top padding
                padding_bottom = 20  # Small bottom padding
                padding_left = 30  # Left padding for title

                title_height = estimated_text_height + padding_top + padding_bottom

                logger.info(f"[{run_id}] Created title block: text_height={estimated_text_height}px, total_height={title_height}px, duration={duration_sec}s")

                # Create background rectangle for title (auto-sized)
                def make_title_bg(t):
                    bg = np.full((title_height, width, 3), title_rgb, dtype=np.uint8)
                    return bg

                title_bg_clip = VideoClip(make_title_bg, duration=duration_sec)
                title_bg_clip = title_bg_clip.with_position((0, 0))

                # Position title text LEFT-ALIGNED with padding
                title_clip = title_clip.with_position((padding_left, padding_top))

                # Cache the result
                title_clips_cache[duration_sec] = (title_bg_clip, title_clip, title_height)

                return (title_bg_clip, title_clip, title_height)
            except Exception as e:
                logger.error(f"[{run_id}] Failed to create title block: {e}", exc_info=True)
                return (None, None, 0)

        scenes_clips = []

        # Process each scene
        for scene in layout.get("scenes", []):
            scene_id = scene["scene_id"]
            duration_sec = scene["duration_ms"] / 1000.0

            logger.info(f"[{run_id}] Composing {scene_id}, duration={duration_sec}s")

            # Create base background - white for general mode, dark for story mode
            mode = layout.get("mode", "story")
            if mode == "general":
                bg_color = (255, 255, 255)  # White background for general mode
            else:
                bg_color = (20, 20, 40)  # Dark background for story mode

            base_clip = VideoClip(
                lambda t: np.full((height, width, 3), bg_color, dtype=np.uint8),
                duration=duration_sec
            )
            logger.info(f"[{run_id}] Using {'white' if mode == 'general' else 'dark'} base background for {mode} mode")

            # Layer images
            image_clips = [base_clip]

            # Initialize scene_image_top_y for subtitle positioning
            # Default to None, will be set for general mode 1:1 images
            scene_image_top_y = None

            # Sort slots by z_index (background first, then characters)
            sorted_slots = sorted(scene.get("images", []), key=lambda s: s.get("z_index", 1))

            for img_slot in sorted_slots:
                img_url = img_slot.get("image_url")
                if img_url and Path(img_url).exists():
                    img_type = img_slot.get("type", "character")

                    # Load image with proper transparency handling for PNG
                    from PIL import Image as PILImage

                    pil_img = PILImage.open(img_url)

                    # Check if image has alpha channel (transparency)
                    has_alpha = pil_img.mode in ('RGBA', 'LA') or (pil_img.mode == 'P' and 'transparency' in pil_img.info)

                    if has_alpha and img_type == "character":
                        # Character with transparency - use mask for proper compositing
                        logger.info(f"[{run_id}] Loading transparent PNG: {img_url}")

                        # Convert to RGBA if needed
                        if pil_img.mode != 'RGBA':
                            pil_img = pil_img.convert('RGBA')

                        # Split RGB and alpha
                        img_array = np.array(pil_img)
                        rgb = img_array[:, :, :3]
                        alpha = img_array[:, :, 3]

                        # Create ImageClip from RGB array
                        img_clip = ImageClip(rgb, duration=duration_sec, is_mask=False)

                        # Create mask from alpha channel
                        # Normalize alpha to 0-1 range for MoviePy
                        alpha_normalized = alpha.astype(float) / 255.0
                        mask_clip = ImageClip(alpha_normalized, duration=duration_sec, is_mask=True)

                        # Apply mask to image
                        img_clip = img_clip.with_mask(mask_clip)
                        logger.info(f"[{run_id}] Applied transparency mask to character image")
                    else:
                        # Background or image without alpha - load normally
                        img_clip = ImageClip(img_url, duration=duration_sec)

                    # Handle different image types
                    if img_type == "background":
                        # Background: always fill entire screen (9:16)
                        img_clip = img_clip.resized((width, height))
                        img_clip = img_clip.with_position(("center", "center"))
                        logger.info(f"[{run_id}] Added background image (full screen)")
                    elif img_type == "scene":
                        # Scene image: check aspect ratio
                        aspect_ratio = img_slot.get("aspect_ratio", "9:16")

                        if aspect_ratio == "1:1":
                            # General Mode: 1:1 square image, positioned near bottom
                            # Resize to fit width while maintaining aspect ratio
                            img_clip = img_clip.resized(width=width)
                            # Position image center at 80% of screen height (near bottom to avoid subtitle overlap)
                            img_height = img_clip.h
                            # Calculate y so image center is at 80% of screen height
                            y_position = int(height * 0.80 - img_height * 0.80)
                            img_clip = img_clip.with_position(("center", y_position))
                            # Store image position for subtitle placement
                            scene_image_top_y = y_position
                            logger.info(f"[{run_id}] Added 1:1 scene image (positioned at y={y_position}px, image center at 80% of screen, avoiding subtitle overlap)")
                        else:
                            # Story Mode or default: 9:16 image, fill screen
                            img_clip = img_clip.resized((width, height))
                            img_clip = img_clip.with_position(("center", "center"))
                            logger.info(f"[{run_id}] Added 9:16 scene image (full screen)")
                    else:
                        # Character: resize and position based on x_pos
                        # Use 0.7 (70% of screen height) to show full character even if text overlaps
                        img_clip = img_clip.resized(height=height * 0.7)

                        # Check for x_pos (Story Mode positioning)
                        if "x_pos" in img_slot:
                            x_pos = img_slot["x_pos"]  # 0.25 (left), 0.5 (center), 0.75 (right)

                            # Position image horizontally at x_pos, bottom-aligned vertically
                            img_width, img_height = img_clip.size
                            x_center = int(x_pos * width)
                            y_bottom = height  # Bottom of screen

                            # Calculate top-left corner position so horizontal center is at x_center and bottom is at screen bottom
                            x_pixel = x_center - (img_width // 2)
                            y_pixel = y_bottom - img_height

                            img_clip = img_clip.with_position((x_pixel, y_pixel), relative=False)
                            logger.info(f"[{run_id}] Positioned character at x={x_pos:.2f} ({x_center}px), bottom-aligned (image at {x_pixel}, {y_pixel}px)")
                        else:
                            # Legacy positioning by slot_id
                            slot_id = img_slot.get("slot_id", "center")
                            if slot_id == "left":
                                img_clip = img_clip.with_position(("left", "center"))
                            elif slot_id == "right":
                                img_clip = img_clip.with_position(("right", "center"))
                            else:
                                img_clip = img_clip.with_position(("center", "center"))

                    image_clips.append(img_clip)

            # Composite video (without text yet)
            video_clip = CompositeVideoClip(image_clips, size=(width, height))

            # Add title block at the top if enabled
            title_height = 0  # Track title block height for subtitle positioning

            if title_text and use_title_block:
                # Create or retrieve cached title block clips
                title_bg_clip, title_clip_positioned, title_height = create_title_block_clips(duration_sec)

                if title_bg_clip and title_clip_positioned:
                    # Add title block and text to the scene
                    video_clip = CompositeVideoClip([video_clip, title_bg_clip, title_clip_positioned], size=(width, height))
                    logger.info(f"[{run_id}] Scene {scene_id}: Added title block (height: {title_height}px)")
                else:
                    logger.error(f"[{run_id}] Scene {scene_id}: Failed to add title block (clips are None)")
            elif title_text and not use_title_block:
                logger.info(f"[{run_id}] Scene {scene_id}: Title block disabled by user (use_title_block=False)")
            elif not title_text:
                logger.warning(f"[{run_id}] Scene {scene_id}: No title text found, skipping title block")

            # Add text overlays (subtitles) - positioned between title and content
            text_clips = []
            for text_line in scene.get("texts", []):
                text_content = text_line.get("text", "").strip('"')  # Remove quotes if present
                if not text_content:
                    continue

                try:
                    # Create text clip with size constraint for auto line wrapping
                    # Set max width to 90% of screen width for padding
                    max_text_width = int(width * 0.9)

                    # CRITICAL FIX: Give subtitle TextClip explicit generous height
                    # Same issue as title - MoviePy underestimates height for Korean text
                    estimated_subtitle_height = int(subtitle_font_size * 2.5)  # 2.5x font size for generous space

                    # Use black text for general mode (white background), white text for story mode
                    if mode == "general":
                        text_color = 'black'
                        stroke_color = 'white'
                    else:
                        text_color = 'white'
                        stroke_color = 'black'

                    txt_clip = TextClip(
                        text=text_content,
                        font=subtitle_font_path,  # Use selected font
                        font_size=subtitle_font_size,
                        color=text_color,
                        stroke_color=stroke_color,
                        stroke_width=2,
                        size=(max_text_width, estimated_subtitle_height),  # EXPLICIT HEIGHT to prevent clipping
                        method='caption',  # Enable text wrapping
                        duration=duration_sec
                    )

                    # Center subtitle between title block and image
                    # Calculate available space and center the subtitle in it
                    if scene_image_top_y is not None:
                        # General mode: center between title and image
                        available_space = scene_image_top_y - title_height
                        subtitle_y = title_height + (available_space - estimated_subtitle_height) / 2
                    else:
                        # Story mode: position subtitle below title block (or at top if no title)
                        subtitle_y = title_height + 20  # 20px padding from title (or from top if no title)

                    txt_position = ('center', subtitle_y)
                    txt_clip = txt_clip.with_position(txt_position)
                    text_clips.append(txt_clip)

                    logger.info(f"[{run_id}] Added subtitle at y={subtitle_y} (estimated h={estimated_subtitle_height}px): {text_content[:30]}...")
                except Exception as e:
                    logger.warning(f"[{run_id}] Failed to create text overlay: {e}")

            # Combine video with text overlays
            if text_clips:
                video_clip = CompositeVideoClip([video_clip] + text_clips, size=(width, height))

            scenes_clips.append(video_clip)

        # Concatenate all scenes
        logger.info(f"[{run_id}] Concatenating {len(scenes_clips)} scenes...")
        final_video = concatenate_videoclips(scenes_clips, method="compose")

        # Add audio tracks
        audio_clips = []

        # Global BGM with looping support
        global_bgm = layout.get("global_bgm")
        if global_bgm and global_bgm.get("audio_url"):
            bgm_path = global_bgm["audio_url"]
            if Path(bgm_path).exists() and Path(bgm_path).stat().st_size > 100:
                try:
                    bgm_clip = AudioFileClip(bgm_path)
                    video_duration = final_video.duration

                    # Loop BGM if it's shorter than video
                    if bgm_clip.duration < video_duration:
                        from moviepy import concatenate_audioclips
                        num_loops = int(video_duration / bgm_clip.duration) + 1
                        logger.info(f"[{run_id}] BGM ({bgm_clip.duration:.1f}s) shorter than video ({video_duration:.1f}s), looping {num_loops} times")
                        bgm_clip = concatenate_audioclips([bgm_clip] * num_loops)
                        bgm_clip = bgm_clip.with_duration(video_duration)

                    bgm_clip = bgm_clip.with_volume_scaled(global_bgm.get("volume", 0.5))
                    audio_clips.append(bgm_clip)
                    logger.info(f"[{run_id}] Added BGM: {bgm_path} (duration: {bgm_clip.duration:.1f}s)")
                except Exception as e:
                    logger.warning(f"[{run_id}] Failed to load BGM {bgm_path}: {e}")
            else:
                logger.warning(f"[{run_id}] Skipping BGM (file too small or missing): {bgm_path}")

        # Text audio (voice/narration) with proper timing
        scene_start_time = 0.0  # Cumulative start time for each scene
        for scene in layout.get("scenes", []):
            scene_duration = scene["duration_ms"] / 1000.0

            # Track current position within scene for sequential audio playback
            current_time_in_scene = 0.0

            for text_line in scene.get("texts", []):
                audio_url = text_line.get("audio_url")
                if audio_url and Path(audio_url).exists():
                    # Check file size (skip stub files < 100 bytes)
                    if Path(audio_url).stat().st_size < 100:
                        logger.warning(f"[{run_id}] Skipping voice audio (stub file): {audio_url}")
                        continue

                    try:
                        voice_clip = AudioFileClip(audio_url)

                        # Use start_ms from layout if provided and non-zero, otherwise sequential
                        text_start_in_scene = text_line.get("start_ms", 0) / 1000.0

                        # If start_ms is 0 or not properly set, use sequential timing
                        if text_start_in_scene == 0 and current_time_in_scene > 0:
                            text_start_in_scene = current_time_in_scene

                        absolute_start_time = scene_start_time + text_start_in_scene

                        # Set start time for this voice clip
                        voice_clip = voice_clip.with_start(absolute_start_time)
                        audio_clips.append(voice_clip)

                        # Update current time for next audio (add duration of this audio)
                        current_time_in_scene = text_start_in_scene + voice_clip.duration

                        logger.info(f"[{run_id}] Added voice at {absolute_start_time:.2f}s (duration: {voice_clip.duration:.2f}s): {audio_url}")
                    except Exception as e:
                        logger.warning(f"[{run_id}] Failed to load voice {audio_url}: {e}")

            # Move to next scene
            scene_start_time += scene_duration

        # Composite audio
        if audio_clips:
            final_audio = CompositeAudioClip(audio_clips)
            final_video = final_video.with_audio(final_audio)

        # Export video
        output_dir = Path(f"app/data/outputs/{run_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "final_video.mp4"

        logger.info(f"[{run_id}] Exporting video to {output_path}...")
        publish_progress(run_id, progress=0.78, log="영상 파일 내보내기 중...")

        final_video.write_videofile(
            str(output_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(output_dir / "temp_audio.m4a"),
            remove_temp=True,
            logger="bar"  # Show progress bar
        )

        logger.info(f"[{run_id}] Video exported: {output_path}")
        publish_progress(run_id, progress=0.8, log=f"영상 내보내기 완료: {output_path}")

        # Transition to QA
        if fsm and fsm.transition_to(RunState.QA):
            logger.info(f"[{run_id}] Transitioned to QA")

            # Publish with video_url artifact
            video_url = f"/outputs/{run_id}/final_video.mp4"
            publish_progress(
                run_id,
                state="QA",
                progress=0.82,
                log="QA 검수 단계로 전환...",
                artifacts={"video_url": video_url}
            )

            # Trigger QA task
            from app.tasks.qa import qa_task
            qa_task.apply_async(args=[run_id, str(json_path), str(output_path)])
            logger.info(f"[{run_id}] QA task triggered with video_url: {video_url}")

        return {
            "run_id": run_id,
            "agent": "director",
            "video_url": str(output_path),
            "status": "success"
        }

    except Exception as e:
        logger.error(f"[{run_id}] Director task failed: {e}", exc_info=True)

        # Mark FSM as failed
        from app.orchestrator.fsm import get_fsm
        if fsm := get_fsm(run_id):
            fsm.fail(str(e))

        from app.main import runs
        if run_id in runs:
            runs[run_id]["state"] = "FAILED"
            runs[run_id]["logs"].append(f"Rendering failed: {e}")

        raise
