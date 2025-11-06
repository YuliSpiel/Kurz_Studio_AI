"""
Progress update utility for Celery tasks.
Publishes updates to Redis pub/sub which are then broadcast to WebSocket clients.
"""
import logging
import redis
import orjson

from app.config import settings

logger = logging.getLogger(__name__)

# Sync Redis client for Celery tasks
_redis_client = None


def get_redis_client():
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=False  # We'll handle encoding ourselves
        )
    return _redis_client


def publish_progress(
    run_id: str,
    state: str = None,
    progress: float = None,
    log: str = None,
    artifacts: dict = None
):
    """
    Publish progress update to Redis pub/sub.

    This function is called by Celery tasks to send progress updates
    to the FastAPI server, which then broadcasts them to WebSocket clients.

    Args:
        run_id: Run identifier
        state: FSM state (optional)
        progress: Progress value 0.0-1.0 (optional)
        log: Log message (optional)
        artifacts: Artifacts dict to update (optional)
    """
    try:
        client = get_redis_client()

        message = {"run_id": run_id}
        if state:
            message["state"] = state
        if progress is not None:
            message["progress"] = progress
        if log:
            message["log"] = log
        if artifacts:
            message["artifacts"] = artifacts

        # Publish to Redis channel
        client.publish(
            "autoshorts:progress",
            orjson.dumps(message)
        )

        logger.debug(f"[{run_id}] Published progress: state={state}, progress={progress}, artifacts={bool(artifacts)}")

    except Exception as e:
        logger.error(f"Failed to publish progress for {run_id}: {e}")
        # Don't raise - progress updates are non-critical
