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
                        if layout.get("global_bgm"):
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

        scenes_clips = []

        # Process each scene
        for scene in layout.get("scenes", []):
            scene_id = scene["scene_id"]
            duration_sec = scene["duration_ms"] / 1000.0

            logger.info(f"[{run_id}] Composing {scene_id}, duration={duration_sec}s")

            # Create base background
            bg_color = (20, 20, 40)  # Dark background
            base_clip = VideoClip(
                lambda t: np.full((height, width, 3), bg_color, dtype=np.uint8),
                duration=duration_sec
            )

            # Layer images
            image_clips = [base_clip]
            for img_slot in scene.get("images", []):
                img_url = img_slot.get("image_url")
                if img_url and Path(img_url).exists():
                    # Load and position image (MoviePy 2.x uses duration parameter)
                    img_clip = ImageClip(img_url, duration=duration_sec)

                    # Resize to fit
                    img_clip = img_clip.resized(height=height * 0.6)

                    # Position based on slot
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

            # Add text overlays (subtitles)
            text_clips = []
            for text_line in scene.get("texts", []):
                text_content = text_line.get("text", "").strip('"')  # Remove quotes if present
                if not text_content:
                    continue

                try:
                    # Create text clip
                    txt_clip = TextClip(
                        text=text_content,
                        font=KOREAN_FONT,
                        font_size=60,
                        color='white',
                        stroke_color='black',
                        stroke_width=2,
                        duration=duration_sec
                    )

                    # Position text based on layout
                    position = text_line.get("position", "bottom")
                    if position == "top":
                        txt_position = ('center', height * 0.1)
                    elif position == "center":
                        txt_position = ('center', 'center')
                    else:  # bottom
                        txt_position = ('center', height * 0.85)

                    txt_clip = txt_clip.with_position(txt_position)
                    text_clips.append(txt_clip)

                    logger.info(f"[{run_id}] Added subtitle: {text_content[:30]}...")
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

        # Global BGM
        global_bgm = layout.get("global_bgm")
        if global_bgm and global_bgm.get("audio_url"):
            bgm_path = global_bgm["audio_url"]
            if Path(bgm_path).exists() and Path(bgm_path).stat().st_size > 100:
                try:
                    bgm_clip = AudioFileClip(bgm_path).with_volume_scaled(global_bgm.get("volume", 0.3))
                    audio_clips.append(bgm_clip)
                    logger.info(f"[{run_id}] Added BGM: {bgm_path}")
                except Exception as e:
                    logger.warning(f"[{run_id}] Failed to load BGM {bgm_path}: {e}")
            else:
                logger.warning(f"[{run_id}] Skipping BGM (file too small or missing): {bgm_path}")

        # Text audio (voice/narration) with proper timing
        scene_start_time = 0.0  # Cumulative start time for each scene
        for scene in layout.get("scenes", []):
            scene_duration = scene["duration_ms"] / 1000.0

            for text_line in scene.get("texts", []):
                audio_url = text_line.get("audio_url")
                if audio_url and Path(audio_url).exists():
                    # Check file size (skip stub files < 100 bytes)
                    if Path(audio_url).stat().st_size < 100:
                        logger.warning(f"[{run_id}] Skipping voice audio (stub file): {audio_url}")
                        continue

                    try:
                        voice_clip = AudioFileClip(audio_url)

                        # Calculate start time: scene start + text line start within scene
                        text_start_in_scene = text_line.get("start_ms", 0) / 1000.0
                        absolute_start_time = scene_start_time + text_start_in_scene

                        # Set start time for this voice clip
                        voice_clip = voice_clip.with_start(absolute_start_time)
                        audio_clips.append(voice_clip)

                        logger.info(f"[{run_id}] Added voice at {absolute_start_time:.2f}s: {audio_url}")
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
