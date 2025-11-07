"""
QA Agent: 품질 검수 및 검증.
렌더링된 영상의 품질을 확인하고 Pass/Fail 판정.
"""
import logging
import json
from pathlib import Path

from app.celery_app import celery
from app.orchestrator.fsm import RunState, get_fsm
from app.utils.progress import publish_progress

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="tasks.qa")
def qa_task(self, run_id: str, json_path: str, video_path: str):
    """
    품질 검수 태스크.

    검수 항목:
    1. 영상 파일이 존재하는가?
    2. JSON 레이아웃이 유효한가?
    3. 모든 에셋이 생성되었는가?
    4. (TODO) 영상 길이가 적절한가?
    5. (TODO) LLM으로 콘텐츠 품질 평가

    Args:
        run_id: Run identifier
        json_path: Path to JSON layout
        video_path: Path to rendered video

    Returns:
        Dict with QA result (pass/fail)
    """
    logger.info(f"[{run_id}] QA: Starting quality check...")
    publish_progress(run_id, state="QA", progress=0.85, log="QA: 품질 검수 시작...")

    # TEST: 3초 대기
    import time
    time.sleep(3)

    try:
        # Get FSM
        from app.orchestrator.fsm import get_fsm
        fsm = get_fsm(run_id)
        if not fsm:
            raise ValueError(f"FSM not found for run {run_id}")

        # Load JSON layout
        with open(json_path, "r", encoding="utf-8") as f:
            layout = json.load(f)

        qa_results = {
            "checks": [],
            "passed": True,
            "issues": []
        }

        # Check 1: 영상 파일 존재 확인
        video_file = Path(video_path)
        if not video_file.exists():
            qa_results["checks"].append({
                "name": "Video file exists",
                "passed": False,
                "message": f"Video file not found: {video_path}"
            })
            qa_results["passed"] = False
            qa_results["issues"].append(f"영상 파일 없음: {video_path}")
        else:
            qa_results["checks"].append({
                "name": "Video file exists",
                "passed": True,
                "message": f"Video file found: {video_path}"
            })
            logger.info(f"[{run_id}] QA: ✓ Video file exists")

        publish_progress(run_id, progress=0.87, log="QA: 영상 파일 확인 완료")

        # Check 2: JSON 레이아웃 유효성
        required_keys = ["scenes", "timeline"]
        for key in required_keys:
            if key not in layout:
                qa_results["checks"].append({
                    "name": f"JSON has '{key}' field",
                    "passed": False,
                    "message": f"Missing required field: {key}"
                })
                qa_results["passed"] = False
                qa_results["issues"].append(f"JSON 필드 누락: {key}")
            else:
                qa_results["checks"].append({
                    "name": f"JSON has '{key}' field",
                    "passed": True,
                    "message": f"Field '{key}' present"
                })

        logger.info(f"[{run_id}] QA: ✓ JSON layout valid")
        publish_progress(run_id, progress=0.90, log="QA: JSON 레이아웃 검증 완료")

        # Check 3: 모든 씬에 이미지가 있는지 확인
        scenes = layout.get("scenes", [])
        for scene in scenes:
            scene_id = scene.get("scene_id", "unknown")
            images = scene.get("images", [])  # Changed from image_slots to images

            for slot in images:
                image_url = slot.get("image_url")
                if not image_url or not Path(image_url).exists():
                    qa_results["checks"].append({
                        "name": f"Image for scene {scene_id}",
                        "passed": False,
                        "message": f"Image missing or invalid: {image_url}"
                    })
                    qa_results["passed"] = False
                    qa_results["issues"].append(f"이미지 누락: {scene_id}")
                else:
                    qa_results["checks"].append({
                        "name": f"Image for scene {scene_id}",
                        "passed": True,
                        "message": f"Image found: {image_url}"
                    })

        logger.info(f"[{run_id}] QA: ✓ All scene images present")
        publish_progress(run_id, progress=0.93, log="QA: 씬 이미지 확인 완료")

        # Check 4: BGM 존재 확인
        global_bgm = layout.get("global_bgm")
        if global_bgm and global_bgm.get("audio_url"):
            bgm_path = Path(global_bgm["audio_url"])
            if not bgm_path.exists():
                qa_results["checks"].append({
                    "name": "Background music exists",
                    "passed": False,
                    "message": f"BGM file not found: {bgm_path}"
                })
                qa_results["passed"] = False
                qa_results["issues"].append(f"BGM 파일 없음")
            else:
                qa_results["checks"].append({
                    "name": "Background music exists",
                    "passed": True,
                    "message": f"BGM found: {bgm_path}"
                })

        logger.info(f"[{run_id}] QA: ✓ Background music check complete")
        publish_progress(run_id, progress=0.95, log="QA: 배경음악 확인 완료")

        # Final decision
        if qa_results["passed"]:
            logger.info(f"[{run_id}] QA: ✅ All checks PASSED")
            publish_progress(run_id, progress=0.98, log="QA: 모든 검사 통과 ✅")

            # Transition to END
            if fsm.transition_to(RunState.END):
                logger.info(f"[{run_id}] Transitioned to END")

                # Publish final state with video_url and qa_result
                video_url = f"/outputs/{run_id}/final_video.mp4"
                publish_progress(
                    run_id,
                    state="END",
                    progress=1.0,
                    log="영상 생성 완료! 🎉",
                    artifacts={
                        "video_url": video_url,
                        "qa_result": qa_results
                    }
                )
                logger.info(f"[{run_id}] Published END state with video_url: {video_url}")
        else:
            logger.warning(f"[{run_id}] QA: ❌ Checks FAILED - Issues: {qa_results['issues']}")
            publish_progress(
                run_id,
                progress=0.95,
                log=f"QA: 검사 실패 ❌ - {', '.join(qa_results['issues'])}"
            )

            # Retry from PLOT_GENERATION
            if fsm.retry_from_qa():
                logger.info(f"[{run_id}] Retrying from PLOT_GENERATION due to QA failure")
                publish_progress(
                    run_id,
                    state="PLOT_GENERATION",
                    progress=0.0,
                    log="QA 실패 - 플롯부터 재생성 시작..."
                )

                from app.main import runs
                if run_id in runs:
                    runs[run_id]["state"] = fsm.current_state.value
                    runs[run_id]["progress"] = 0.0
                    runs[run_id]["artifacts"]["qa_retry_count"] = runs[run_id]["artifacts"].get("qa_retry_count", 0) + 1

                # TODO: Trigger plan task again
                # from app.tasks.plan import plan_task
                # plan_task.apply_async(args=[run_id, spec])

        return {
            "run_id": run_id,
            "agent": "qa",
            "qa_result": qa_results,
            "passed": qa_results["passed"]
        }

    except Exception as e:
        logger.error(f"[{run_id}] QA task failed: {e}", exc_info=True)

        if fsm := get_fsm(run_id):
            fsm.fail(f"QA task error: {str(e)}")

        raise
