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

        # Load JSON with all asset URLs
        with open(json_path, "r", encoding="utf-8") as f:
            layout = json.load(f)

        # Check if we're in stub mode (no real assets)
        from app.config import settings
        stub_mode = not settings.ELEVENLABS_API_KEY and not settings.PLAYHT_API_KEY

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
                logger.info(f"[{run_id}]     Dialogue: {len(scene.get('dialogue', []))}")

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

                    for dialogue in scene.get("dialogue", []):
                        f.write(f"  Audio: {dialogue.get('audio_url', 'N/A')}\n")
                        f.write(f"    Text: {dialogue.get('text', 'N/A')}\n")

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
                    runs[run_id]["artifacts"]["video_url"] = str(output_path)

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

            # Composite video
            video_clip = CompositeVideoClip(image_clips, size=(width, height))

            # Add subtitles (simplified - use TextClip)
            for subtitle in scene.get("subtitles", []):
                # MoviePy TextClip requires ImageMagick (complex setup)
                # For now, skip or use simple overlay
                pass

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
            if Path(bgm_path).exists():
                bgm_clip = AudioFileClip(bgm_path).with_volume_scaled(global_bgm.get("volume", 0.3))
                audio_clips.append(bgm_clip)

        # Dialogue audio (simplified - just add sequentially)
        for scene in layout.get("scenes", []):
            for dialogue in scene.get("dialogue", []):
                audio_url = dialogue.get("audio_url")
                if audio_url and Path(audio_url).exists():
                    voice_clip = AudioFileClip(audio_url)
                    # Set start time based on dialogue["start_ms"]
                    # For simplicity, add to composite
                    audio_clips.append(voice_clip)

        # Composite audio
        if audio_clips:
            final_audio = CompositeAudioClip(audio_clips)
            final_video = final_video.with_audio(final_audio)

        # Export video
        output_dir = Path(f"app/data/outputs/{run_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "final_video.mp4"

        logger.info(f"[{run_id}] Exporting video to {output_path}...")

        final_video.write_videofile(
            str(output_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(output_dir / "temp_audio.m4a"),
            remove_temp=True,
            logger=None  # Suppress MoviePy logs
        )

        logger.info(f"[{run_id}] Video exported: {output_path}")
        publish_progress(run_id, progress=0.8, log=f"영상 내보내기 완료: {output_path}")

        # Transition to QA
        if fsm and fsm.transition_to(RunState.QA):
            logger.info(f"[{run_id}] Transitioned to QA")
            publish_progress(run_id, state="QA", progress=0.82, log="QA 검수 단계로 전환...")

            from app.main import runs
            if run_id in runs:
                runs[run_id]["state"] = fsm.current_state.value
                runs[run_id]["progress"] = 0.82
                runs[run_id]["artifacts"]["video_url"] = str(output_path)

            # Trigger QA task
            from app.tasks.qa import qa_task
            qa_task.apply_async(args=[run_id, str(json_path), str(output_path)])
            logger.info(f"[{run_id}] QA task triggered")

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
