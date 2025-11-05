"""
기획자 Agent: Plot planning task.
Generates CSV from prompt, converts to JSON, and triggers asset generation.
"""
import logging
from pathlib import Path
from celery import chord, group

from app.celery_app import celery
from app.orchestrator.fsm import RunState, get_fsm
from app.utils.csv_to_json import generate_csv_from_prompt, csv_to_json
from app.utils.progress import publish_progress

logger = logging.getLogger(__name__)


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
    logger.info(f"[{run_id}] Starting plot planning...")
    publish_progress(run_id, state="PLOT_PLANNING", progress=0.1, log="기획 시작: 프롬프트 분석 중...")

    try:
        # TEST: 3초 대기
        import time
        time.sleep(3)

        # Get FSM (from Redis if needed)
        fsm = get_fsm(run_id)
        if not fsm:
            raise ValueError(f"FSM not found for run {run_id}")

        # Step 1: Generate CSV
        logger.info(f"[{run_id}] Generating CSV from prompt...")
        publish_progress(run_id, progress=0.12, log="시나리오 생성 중 (GPT-4o-mini)...")
        csv_path = generate_csv_from_prompt(
            run_id=run_id,
            prompt=spec["prompt"],
            num_characters=spec["num_characters"],
            num_cuts=spec["num_cuts"],
            mode=spec["mode"]
        )
        logger.info(f"[{run_id}] CSV generated: {csv_path}")
        publish_progress(run_id, progress=0.15, log=f"시나리오 CSV 생성 완료: {csv_path}")

        # Step 2: Convert CSV to JSON
        logger.info(f"[{run_id}] Converting CSV to JSON...")
        publish_progress(run_id, progress=0.17, log="JSON 레이아웃 변환 중...")
        json_path = csv_to_json(
            csv_path=csv_path,
            run_id=run_id,
            art_style=spec.get("art_style", "파스텔 수채화"),
            music_genre=spec.get("music_genre", "ambient")
        )
        logger.info(f"[{run_id}] JSON generated: {json_path}")
        publish_progress(run_id, progress=0.2, log=f"JSON 레이아웃 생성 완료: {json_path}")

        # Update FSM artifacts
        from app.main import runs
        if run_id in runs:
            runs[run_id]["artifacts"]["csv_path"] = str(csv_path)
            runs[run_id]["artifacts"]["json_path"] = str(json_path)
            runs[run_id]["progress"] = 0.2

        # Step 3: Transition to ASSET_GENERATION
        publish_progress(run_id, progress=0.22, log="에셋 생성 단계로 전환 중...")
        if fsm.transition_to(RunState.ASSET_GENERATION):
            logger.info(f"[{run_id}] Transitioned to ASSET_GENERATION")
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
            "csv_path": str(csv_path),
            "json_path": str(json_path),
            "status": "success"
        }

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
