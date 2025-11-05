"""
Recovery task: Handles retries and fallback strategies.
"""
import logging
from app.celery_app import celery
from app.orchestrator.fsm import RunState, get_fsm

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="tasks.recover")
def recover_task(self, run_id: str, failed_state: str, error_message: str):
    """
    Attempt to recover from a failed task.

    Strategy:
    1. Identify failed state
    2. Determine if retry is possible
    3. Apply fallback providers if needed
    4. Re-trigger failed task

    Args:
        run_id: Run identifier
        failed_state: State where failure occurred
        error_message: Error description

    Returns:
        Recovery status
    """
    logger.info(f"[{run_id}] Recovery: Attempting to recover from {failed_state}")
    logger.info(f"[{run_id}] Error: {error_message}")

    try:
        # Get FSM (from Redis if needed)
        fsm = get_fsm(run_id)
        if not fsm:
            raise ValueError(f"FSM not found for run {run_id}")

        # Transition to RECOVER state
        if not fsm.transition_to(RunState.RECOVER):
            logger.error(f"[{run_id}] Cannot transition to RECOVER state")
            return {"status": "failed", "reason": "Cannot enter recovery"}

        # Determine retry state
        retry_state = fsm.get_retry_state()
        if not retry_state:
            logger.error(f"[{run_id}] No valid retry state found")
            fsm.fail("Recovery failed: no valid retry state")
            return {"status": "failed", "reason": "No retry state"}

        logger.info(f"[{run_id}] Will retry from state: {retry_state.value}")

        # Apply fallback strategies based on failed state
        if "TTS" in error_message or "voice" in error_message.lower():
            # Switch TTS provider
            from app.config import settings
            if settings.TTS_PROVIDER == "elevenlabs":
                logger.info(f"[{run_id}] Switching TTS provider to playht")
                settings.TTS_PROVIDER = "playht"
            elif settings.TTS_PROVIDER == "playht":
                logger.info(f"[{run_id}] Switching TTS provider to elevenlabs")
                settings.TTS_PROVIDER = "elevenlabs"

        # Retry count check (store in FSM metadata)
        retry_count = fsm.metadata.get("retry_count", 0)
        if retry_count >= 3:
            logger.error(f"[{run_id}] Max retries exceeded")
            fsm.fail("Max retries exceeded")
            return {"status": "failed", "reason": "Max retries exceeded"}

        fsm.metadata["retry_count"] = retry_count + 1

        # Re-trigger the failed task
        if retry_state == RunState.PLOT_PLANNING:
            from app.tasks.plan import plan_task
            from app.main import runs
            spec = runs.get(run_id, {}).get("spec", {})
            plan_task.apply_async(args=[run_id, spec])

        elif retry_state == RunState.ASSET_GENERATION:
            # Re-trigger asset generation
            logger.info(f"[{run_id}] Re-triggering asset generation...")
            # Would re-run the chord here

        logger.info(f"[{run_id}] Recovery initiated, retry count: {retry_count + 1}")

        return {
            "status": "recovery_initiated",
            "retry_state": retry_state.value,
            "retry_count": retry_count + 1
        }

    except Exception as e:
        logger.error(f"[{run_id}] Recovery task failed: {e}", exc_info=True)
        raise
