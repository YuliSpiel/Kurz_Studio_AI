"""
기획자 Agent: Plot planning task.
Generates CSV from prompt, converts to JSON, and triggers asset generation.
"""
import logging
import json
from pathlib import Path
from celery import chord, group
from celery.exceptions import Retry
from typing import List

from app.celery_app import celery
from app.orchestrator.fsm import RunState, get_fsm
from app.utils.plot_generator import generate_plot_with_characters
from app.utils.json_converter import convert_plot_to_json
from app.utils.progress import publish_progress

logger = logging.getLogger(__name__)


def _validate_plot_json(run_id: str, plot_json_path: Path, layout_json_path: Path, characters_path: Path, spec: dict) -> List[str]:
    """
    Validate plot.json, characters.json, and layout.json structure.

    Args:
        run_id: Run identifier
        plot_json_path: Path to plot.json
        layout_json_path: Path to layout.json
        characters_path: Path to characters.json
        spec: RunSpec dict

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    try:
        # Load plot.json
        with open(plot_json_path, "r", encoding="utf-8") as f:
            plot_data = json.load(f)

        # Load layout.json
        with open(layout_json_path, "r", encoding="utf-8") as f:
            layout_data = json.load(f)

        # Load characters.json
        characters_data = {}
        if characters_path.exists():
            with open(characters_path, "r", encoding="utf-8") as f:
                characters_data = json.load(f)

        mode = spec.get("mode", "general")
        num_cuts = spec.get("num_cuts", 3)

        # Validation 1: Check plot.json has scenes
        if "scenes" not in plot_data or not plot_data["scenes"]:
            errors.append("plot.json에 scenes가 없거나 비어있음")
            return errors  # Critical error, stop validation

        # Validation 2: Check scene count is reasonable (allow ±100% tolerance)
        # LLM often generates 2x scenes, so be very flexible
        num_scenes = len(plot_data["scenes"])
        min_scenes = max(1, int(num_cuts * 0.5))  # Allow 50% fewer
        max_scenes = num_cuts * 2 + 3             # Allow 2x + buffer

        if num_scenes < min_scenes or num_scenes > max_scenes:
            errors.append(f"scenes 개수({num_scenes})가 num_cuts({num_cuts}) 범위를 벗어남 (허용: {min_scenes}~{max_scenes})")

        # Validation 2.5: Count new images requested (should be at least 40% of num_cuts)
        total_new_images = 0
        for scene in plot_data["scenes"]:
            if mode in ["general", "ad"]:
                # Count non-empty image_prompt
                if "image_prompt" in scene and scene["image_prompt"] and scene["image_prompt"].strip():
                    total_new_images += 1
            elif mode == "story":
                # Background + characters
                if "background_img" in scene and scene["background_img"]:
                    total_new_images += 1
                for key in scene.keys():
                    if key.startswith("char") and key.endswith("_id") and scene[key]:
                        total_new_images += 1

        min_images = max(1, int(num_cuts * 0.4))  # At least 40% should be new images
        if total_new_images < min_images:
            errors.append(f"새 이미지 요청이 너무 적음 ({total_new_images}개, 최소 {min_images}개 필요)")

        # Validation 3: Check each scene has required fields
        for idx, scene in enumerate(plot_data["scenes"]):
            scene_id = scene.get("scene_id", f"scene_{idx}")

            # Check text field
            if "text" not in scene or not scene["text"].strip():
                errors.append(f"{scene_id}: text 필드가 비어있음")

            # Mode-specific validation
            if mode in ["general", "ad"]:
                # General/Ad Mode: image_prompt required
                if "image_prompt" not in scene:
                    errors.append(f"{scene_id}: image_prompt 필드 없음")
                elif scene.get("image_prompt") is None:
                    errors.append(f"{scene_id}: image_prompt가 None")
                # Note: empty string is allowed for image reuse

            elif mode == "story":
                # Story Mode: background_img required
                if "background_img" not in scene or not scene["background_img"]:
                    errors.append(f"{scene_id}: background_img 필드가 비어있음")

        # Validation 4: Check layout.json structure
        if "scenes" not in layout_data or not layout_data["scenes"]:
            errors.append("layout.json에 scenes가 없거나 비어있음")

        if "timeline" not in layout_data:
            errors.append("layout.json에 timeline 필드 없음")

        # Validation 5: Check layout has reasonable number of image slots (allow ±100% tolerance)
        layout_image_count = 0
        for scene in layout_data.get("scenes", []):
            layout_image_count += len(scene.get("images", []))

        min_layout_images = max(1, int(num_cuts * 0.5))
        max_layout_images = num_cuts * 2 + 3

        if layout_image_count < min_layout_images or layout_image_count > max_layout_images:
            errors.append(f"layout.json 이미지 슬롯 개수({layout_image_count})가 num_cuts({num_cuts}) 범위를 벗어남 (허용: {min_layout_images}~{max_layout_images})")

        # Validation 6: Check each layout scene has images
        for idx, scene in enumerate(layout_data.get("scenes", [])):
            scene_id = scene.get("scene_id", f"scene_{idx}")
            if "images" not in scene or not scene["images"]:
                errors.append(f"{scene_id}: layout.json에 images 슬롯이 없음")

        # Validation 7: Check text quality (detect fallback/dummy data)
        prompt = spec.get("prompt", "")
        all_texts = [scene.get("text", "") for scene in plot_data["scenes"]]

        # Check for fallback pattern: "{prompt}의 N번째 장면입니다"
        fallback_pattern_count = 0
        for text in all_texts:
            if "번째 장면입니다" in text or f"{prompt}의" in text or f'"{prompt}의' in text:
                fallback_pattern_count += 1

        if fallback_pattern_count > 0:
            errors.append(f"폴백 더미 텍스트 감지됨 ({fallback_pattern_count}개 씬) - LLM 생성 실패")

        # Check for identical texts (all scenes have same text = LLM failure)
        if len(all_texts) > 1:
            unique_texts = set(all_texts)
            if len(unique_texts) == 1:
                errors.append(f"모든 씬({len(all_texts)}개)이 동일한 텍스트 반복 - LLM 생성 실패")
            elif len(unique_texts) < len(all_texts) * 0.5:  # More than 50% duplicates
                errors.append(f"과도한 텍스트 중복 ({len(unique_texts)}/{len(all_texts)} 고유) - LLM 생성 실패")

        # Check text length (max 28 characters per spec)
        for idx, scene in enumerate(plot_data["scenes"]):
            scene_id = scene.get("scene_id", f"scene_{idx}")
            text = scene.get("text", "").strip()
            # Remove quotes if present
            text_clean = text.strip('"\'')
            if len(text_clean) > 50:  # Allow some flexibility, but 50 is too long
                errors.append(f"{scene_id}: text 길이 초과 ({len(text_clean)}자, 권장 28자 이내)")

        # Validation 8: Check for dummy character names in characters.json
        if characters_data and "characters" in characters_data:
            char_names = [c.get("name", "") for c in characters_data["characters"]]
            dummy_char_count = 0
            for name in char_names:
                if name.startswith("캐릭터 ") or name.startswith("Character "):
                    dummy_char_count += 1

            if dummy_char_count > 0:
                errors.append(f"의미 없는 캐릭터 이름 감지됨 ({dummy_char_count}개) - LLM 생성 실패")

            # Check for dummy appearance descriptions
            char_appearances = [c.get("appearance", "") for c in characters_data["characters"] if c.get("appearance")]
            dummy_appearance_count = 0
            for appearance in char_appearances:
                if appearance.startswith("캐릭터 ") and "의 외형" in appearance:
                    dummy_appearance_count += 1

            if dummy_appearance_count > 0:
                errors.append(f"의미 없는 캐릭터 외형 감지됨 ({dummy_appearance_count}개) - LLM 생성 실패")

        logger.info(f"[{run_id}] Validation completed: {len(errors)} errors found")
        return errors

    except json.JSONDecodeError as e:
        errors.append(f"JSON 파싱 실패: {e}")
        return errors
    except Exception as e:
        errors.append(f"검증 중 오류 발생: {e}")
        return errors


@celery.task(bind=True, name="tasks.plan")
def plan_task(self, run_id: str, spec: dict):
    """
    Generate plot and structure from prompt.

    Workflow:
    1. Generate CSV from prompt (LLM placeholder / rule-based)
    2. Convert CSV to JSON
    3. Transition to ASSET_GENERATION
    4. Trigger fan-out for designer, composer, voice actors

    Args:
        run_id: Run identifier
        spec: RunSpec as dict
    """
    logger.info(f"[{run_id}] Starting plot generation...")
    publish_progress(run_id, state="PLOT_GENERATION", progress=0.1, log="기획자: 시나리오 작성 중...")

    try:
        # TEST: 3초 대기
        import time
        time.sleep(3)

        # Get FSM (from Redis if needed)
        fsm = get_fsm(run_id)
        if not fsm:
            raise ValueError(f"FSM not found for run {run_id}")

        # Step 1: Generate characters and plot
        logger.info(f"[{run_id}] Generating characters and plot from prompt...")
        publish_progress(run_id, progress=0.12, log="기획자: 캐릭터 및 시나리오 생성 중 (Gemini 2.5 Flash)...")
        characters_path, plot_json_path = generate_plot_with_characters(
            run_id=run_id,
            prompt=spec["prompt"],
            num_characters=spec["num_characters"],
            num_cuts=spec["num_cuts"],
            mode=spec["mode"],
            characters=spec.get("characters")  # Pass user-provided characters (Story Mode)
        )
        logger.info(f"[{run_id}] Characters generated: {characters_path}")
        logger.info(f"[{run_id}] Plot JSON generated: {plot_json_path}")
        publish_progress(run_id, progress=0.15, log=f"기획자: 캐릭터 & 시나리오 생성 완료")

        # Step 2: Convert plot.json to layout.json
        logger.info(f"[{run_id}] Converting plot.json to layout.json...")
        publish_progress(run_id, progress=0.17, log="기획자: 레이아웃 JSON 변환 중...")
        json_path = convert_plot_to_json(
            plot_json_path=str(plot_json_path),
            run_id=run_id,
            art_style=spec.get("art_style", "파스텔 수채화"),
            music_genre=spec.get("music_genre", "ambient"),
            video_title=spec.get("video_title"),
            layout_config=spec.get("layout_config")
        )
        logger.info(f"[{run_id}] Layout JSON generated: {json_path}")
        publish_progress(run_id, progress=0.2, log=f"기획자: 레이아웃 JSON 생성 완료")

        # Step 2.5: Validate plot.json, characters.json, and layout.json
        logger.info(f"[{run_id}] Validating plot, characters, and layout JSON...")
        publish_progress(run_id, progress=0.21, log="기획자: JSON 검증 중...")
        validation_errors = _validate_plot_json(run_id, plot_json_path, json_path, characters_path, spec)

        if validation_errors:
            # Check retry count from FSM metadata (persistent across Celery retries)
            max_retries = 2
            retry_count = fsm.metadata.get("plot_retry_count", 0)

            if retry_count < max_retries:
                # Log retry attempt
                logger.warning(f"[{run_id}] Plot validation failed (attempt {retry_count + 1}/{max_retries}), retrying...")
                logger.warning(f"[{run_id}] Validation errors: {', '.join(validation_errors)}")
                publish_progress(run_id, progress=0.21, log=f"⚠️ JSON 검증 실패 - 재생성 시도 ({retry_count + 1}/{max_retries})")

                # Update retry counter in FSM metadata (persistent)
                fsm.metadata["plot_retry_count"] = retry_count + 1
                from app.orchestrator.fsm import register_fsm
                register_fsm(fsm)

                # Clean up old files
                plot_json_path.unlink(missing_ok=True)
                json_path.unlink(missing_ok=True)
                if characters_path:
                    characters_path.unlink(missing_ok=True)

                logger.info(f"[{run_id}] Cleaned up old files, retrying plot generation...")
                publish_progress(run_id, progress=0.1, log="기획자: 시나리오 재작성 중...")

                # Retry plot generation by raising Celery retry
                raise self.retry(countdown=3, max_retries=max_retries)
            else:
                # Max retries exceeded
                error_msg = f"Plot validation failed after {max_retries} attempts: {', '.join(validation_errors)}"
                logger.error(f"[{run_id}] {error_msg}")
                publish_progress(run_id, progress=0.21, log=f"❌ 최대 재시도 초과 - 생성 실패")
                raise ValueError(error_msg)

        logger.info(f"[{run_id}] ✓ JSON validation passed")
        publish_progress(run_id, progress=0.22, log="✓ JSON 검증 완료")

        # Update FSM artifacts
        from app.main import runs
        if run_id in runs:
            runs[run_id]["artifacts"]["characters_path"] = str(characters_path)
            runs[run_id]["artifacts"]["plot_json_path"] = str(plot_json_path)
            runs[run_id]["artifacts"]["json_path"] = str(json_path)
            runs[run_id]["progress"] = 0.22

        # Step 3: Branch based on review_mode
        if spec.get("review_mode", False):
            # Review mode: Transition to PLOT_REVIEW (user approval needed)
            publish_progress(run_id, progress=0.22, log="플롯 검수 대기 중...")
            if fsm.transition_to(RunState.PLOT_REVIEW):
                logger.info(f"[{run_id}] [REVIEW_MODE] Transitioned to PLOT_REVIEW - waiting for user approval")
                publish_progress(run_id, state="PLOT_REVIEW", progress=0.25, log="✓ 플롯 생성 완료 - 사용자 검수 필요")

                # Update state
                if run_id in runs:
                    runs[run_id]["state"] = fsm.current_state.value

                # Load plot.json data
                import json
                with open(plot_json_path, 'r', encoding='utf-8') as f:
                    plot_data = json.load(f)

                # Save CSV version of plot for user editing
                from app.utils.plot_csv_converter import save_plot_csv
                plot_csv_path = save_plot_csv(run_id, plot_data, mode=spec["mode"])
                logger.info(f"[{run_id}] Saved plot CSV for user review: {plot_csv_path}")

                # Update artifacts
                if run_id in runs:
                    runs[run_id]["artifacts"]["plot_csv_path"] = str(plot_csv_path)

                # Wait here - user needs to confirm/edit/regenerate
                # The workflow will continue via API endpoint (see main.py)
                return {
                    "status": "plot_review_pending",
                    "run_id": run_id,
                    "message": "Plot generation complete, waiting for user review"
                }
            else:
                error_msg = f"Failed to transition to PLOT_REVIEW"
                logger.error(f"[{run_id}] {error_msg}")
                publish_progress(run_id, progress=0.22, log=f"❌ 상태 전환 실패")
                raise ValueError(error_msg)
        else:
            # Auto mode: Transition directly to ASSET_GENERATION
            publish_progress(run_id, progress=0.22, log="에셋 생성 단계로 전환 중...")
            if fsm.transition_to(RunState.ASSET_GENERATION):
                logger.info(f"[{run_id}] [AUTO_MODE] Transitioned to ASSET_GENERATION")
                publish_progress(run_id, state="ASSET_GENERATION", progress=0.25, log="에셋 생성 시작 (디자이너, 작곡가, 성우)")

                # Update state
                if run_id in runs:
                    runs[run_id]["state"] = fsm.current_state.value

                # Step 4: Fan-out to asset generation tasks
                from app.tasks.designer import designer_task
                from app.tasks.composer import composer_task
                from app.tasks.voice import voice_task
                from app.tasks.director import director_task

                # Convert Path to string for JSON serialization
                json_path_str = str(json_path)

                # Create chord: parallel tasks → director callback
                asset_tasks = group(
                    designer_task.s(run_id, json_path_str, spec),
                    composer_task.s(run_id, json_path_str, spec),
                    voice_task.s(run_id, json_path_str, spec),
                )

                # Chord: when all complete, trigger director
                workflow = chord(asset_tasks)(director_task.s(run_id, json_path_str))

                logger.info(f"[{run_id}] Asset generation chord started")

            return {
                "run_id": run_id,
                "plot_json_path": str(plot_json_path),
                "json_path": str(json_path),
                "status": "success"
            }

    except Retry:
        # Let Celery handle retry - don't mark as failed
        logger.info(f"[{run_id}] Plot task retrying due to validation failure...")
        raise

    except Exception as e:
        logger.error(f"[{run_id}] Plan task failed: {e}", exc_info=True)

        # Mark FSM as failed
        if fsm := get_fsm(run_id):
            fsm.fail(str(e))

        # Update run state
        from app.main import runs
        if run_id in runs:
            runs[run_id]["state"] = "FAILED"
            runs[run_id]["logs"].append(f"Planning failed: {e}")

        raise
