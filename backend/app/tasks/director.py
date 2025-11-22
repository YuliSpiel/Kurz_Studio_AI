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


@celery.task(bind=True, name="tasks.layout_ready")
def layout_ready_task(self, asset_results: list, run_id: str, json_path: str):
    """
    Chord callback after asset generation completes.
    Updates layout.json with asset URLs and transitions to LAYOUT_REVIEW.

    Args:
        asset_results: List of results from parallel tasks (designer, composer, voice)
        run_id: Run identifier
        json_path: Path to layout.json

    Returns:
        Dict with status
    """
    logger.info(f"[{run_id}] Layout ready: All assets generated")
    logger.info(f"[{run_id}] Asset results: {asset_results}")
    publish_progress(run_id, progress=0.6, log="에셋 생성 완료 - 레이아웃 검수 대기 중...")

    try:
        # Load layout.json
        with open(json_path, "r", encoding="utf-8") as f:
            layout = json.load(f)

        # Update layout.json with asset URLs from chord results
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
                                    logger.info(f"[{run_id}] Updated {scene_id}/{slot_id} -> {image_url}")

            # Update audio URLs from voice agent
            elif agent == "voice" and "voice" in result:
                for audio_result in result["voice"]:
                    scene_id = audio_result["scene_id"]
                    line_id = audio_result["line_id"]
                    audio_url = audio_result["audio_url"]

                    # Find scene and update audio_url
                    for scene in layout.get("scenes", []):
                        if scene["scene_id"] == scene_id:
                            for text_line in scene.get("texts", []):
                                if text_line.get("line_id") == line_id:
                                    text_line["audio_url"] = audio_url
                                    logger.info(f"[{run_id}] Updated {scene_id}/{line_id} -> {audio_url}")

            # Update global BGM from composer
            elif agent == "composer" and "audio" in result:
                # Composer returns audio results in "audio" key
                audio_results = result["audio"]
                for audio_item in audio_results:
                    if audio_item.get("type") == "bgm" and audio_item.get("id") == "global_bgm":
                        bgm_url = audio_item.get("path")
                        if bgm_url:
                            if "global_bgm" not in layout or layout["global_bgm"] is None:
                                layout["global_bgm"] = {}
                            layout["global_bgm"]["audio_url"] = bgm_url
                            logger.info(f"[{run_id}] Updated global BGM -> {bgm_url}")

        # Save updated layout.json
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(layout, f, indent=2, ensure_ascii=False)

        logger.info(f"[{run_id}] layout.json updated with all asset URLs")

        # Check mode from layout.json
        mode = layout.get("metadata", {}).get("mode", "general")

        # Get review_mode from run spec or layout metadata (fallback)
        from app.main import runs
        review_mode = False
        if run_id in runs:
            spec = runs[run_id].get("spec", {})
            review_mode = spec.get("review_mode", False)

        # Fallback to metadata if not found in spec
        if not review_mode:
            review_mode = layout.get("metadata", {}).get("review_mode", False)

        logger.info(f"[{run_id}] Mode={mode}, review_mode={review_mode}")

        from app.orchestrator.fsm import get_fsm
        fsm = get_fsm(run_id)

        # State transition logic:
        # - review_mode=False (자동 모드): Skip all reviews, go directly to RENDERING
        # - review_mode=True (검수 모드): Go to ASSET_REVIEW first for image/BGM review

        if not review_mode:
            # Auto mode: skip all reviews, go directly to RENDERING
            logger.info(f"[{run_id}] Auto mode (review_mode=False), skipping reviews, going directly to RENDERING")
            if fsm and fsm.transition_to(RunState.RENDERING):
                logger.info(f"[{run_id}] Transitioned to RENDERING")
                publish_progress(
                    run_id,
                    state="RENDERING",
                    progress=0.7,
                    log="영상 합성 시작..."
                )

                if run_id in runs:
                    runs[run_id]["state"] = fsm.current_state.value
                    runs[run_id]["progress"] = 0.7

                # Trigger director task immediately
                logger.info(f"[{run_id}] Triggering director_task for immediate rendering")
                director_task.delay([], run_id, json_path)

            return {
                "status": "success",
                "message": "Assets generated, starting video composition",
                "run_id": run_id
            }

        # Review mode: go to ASSET_REVIEW for image/BGM review first
        else:
            if fsm and fsm.transition_to(RunState.ASSET_REVIEW):
                logger.info(f"[{run_id}] Transitioned to ASSET_REVIEW")
                publish_progress(
                    run_id,
                    state="ASSET_REVIEW",
                    progress=0.6,
                    log="에셋 검수 단계 - 이미지/BGM 확인 대기 중"
                )

                if run_id in runs:
                    runs[run_id]["state"] = fsm.current_state.value
                    runs[run_id]["progress"] = 0.6

            return {
                "status": "success",
                "message": "Assets generated, waiting for asset review",
                "run_id": run_id
            }

    except Exception as e:
        logger.error(f"[{run_id}] Failed in layout_ready_task: {e}", exc_info=True)
        from app.orchestrator.fsm import get_fsm
        fsm = get_fsm(run_id)
        if fsm:
            fsm.fail(f"Layout ready task failed: {str(e)}")
        raise


@celery.task(bind=True, name="tasks.director")
def director_task(self, asset_results: list, run_id: str, json_path: str):
    """
    Compose final 9:16 video from all generated assets.

    This task is called as chord callback after all asset generation tasks complete.

    Args:
        asset_results: List of results from parallel asset generation tasks (designer, composer, voice)
        run_id: Run identifier
        json_path: Path to JSON layout with all asset URLs

    Returns:
        Dict with final video URL
    """
    logger.info(f"[{run_id}] Director: Received asset results from chord: {asset_results}")
    logger.info(f"[{run_id}] Director: Starting video composition...")
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

        # Load layout.json
        with open(json_path, "r", encoding="utf-8") as f:
            layout = json.load(f)

        logger.info(f"[{run_id}] Layout loaded with {len(layout.get('scenes', []))} scenes")
        logger.info(f"[{run_id}] Mode: {layout.get('metadata', {}).get('mode', 'general')}")

        # Update layout with asset URLs from chord results (if not already updated)
        # This is needed when director_task is called directly from chord callback (auto mode)
        if asset_results:
            logger.info(f"[{run_id}] Updating layout with asset URLs from chord results...")
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

                        for scene in layout.get("scenes", []):
                            if scene["scene_id"] == scene_id:
                                for img_slot in scene.get("images", []):
                                    if img_slot["slot_id"] == slot_id:
                                        img_slot["image_url"] = image_url

                # Update audio URLs from voice agent
                elif agent == "voice" and "voice" in result:
                    for audio_result in result["voice"]:
                        scene_id = audio_result["scene_id"]
                        line_id = audio_result["line_id"]
                        audio_url = audio_result["audio_url"]

                        for scene in layout.get("scenes", []):
                            if scene["scene_id"] == scene_id:
                                for text_line in scene.get("texts", []):
                                    if text_line.get("line_id") == line_id:
                                        text_line["audio_url"] = audio_url
                                        logger.info(f"[{run_id}] Updated {scene_id}/{line_id} audio -> {audio_url}")

                # Update global BGM from composer
                elif agent == "composer" and "audio" in result:
                    for audio_item in result["audio"]:
                        if audio_item.get("type") == "bgm" and audio_item.get("id") == "global_bgm":
                            bgm_url = audio_item.get("path")
                            if bgm_url:
                                if "global_bgm" not in layout or layout["global_bgm"] is None:
                                    layout["global_bgm"] = {}
                                layout["global_bgm"]["audio_url"] = bgm_url
                                logger.info(f"[{run_id}] Updated global BGM -> {bgm_url}")

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

        # Use FFmpeg-based renderer (faster and more memory-efficient than MoviePy)
        from app.utils.ffmpeg_renderer import FFmpegRenderer

        logger.info(f"[{run_id}] Using FFmpeg-based rendering pipeline")

        output_dir = Path(f"app/data/outputs/{run_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "final_video.mp4"

        # Create FFmpeg renderer
        renderer = FFmpegRenderer(run_id, layout, output_dir)

        # Render video using FFmpeg pipeline
        try:
            publish_progress(run_id, progress=0.72, log="프레임 생성 중...")
            final_video_path = renderer.render(output_path)
            publish_progress(run_id, progress=0.78, log="영상 파일 내보내기 완료")
        except Exception as e:
            logger.error(f"[{run_id}] FFmpeg rendering failed: {e}", exc_info=True)
            raise

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
