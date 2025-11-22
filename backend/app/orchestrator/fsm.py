"""
Finite State Machine (FSM) for AutoShorts orchestration.
Manages state transitions: INIT → PLOT_GENERATION → PLOT_REVIEW → ASSET_GENERATION → LAYOUT_REVIEW → RENDERING → QA → END
                                        ↑                ↓ (재생성)           ↑            ↓ (재생성)                    ↓ Fail
                                        └────────────────┘                    └────────────┘               PLOT_GENERATION (재시도)
"""
import logging
from enum import Enum
from typing import Optional, Dict, Callable

logger = logging.getLogger(__name__)


class RunState(Enum):
    """State definitions for shorts generation workflow."""
    INIT = "INIT"
    PLOT_GENERATION = "PLOT_GENERATION"  # Director: 플롯 생성
    PLOT_REVIEW = "PLOT_REVIEW"  # User: 플롯 검수 및 수정
    ASSET_GENERATION = "ASSET_GENERATION"  # Voice/Painter/Composer
    ASSET_REVIEW = "ASSET_REVIEW"  # User: 에셋(이미지/BGM) 검수 및 재생성
    LAYOUT_REVIEW = "LAYOUT_REVIEW"  # User: 레이아웃 검수 및 확인
    RENDERING = "RENDERING"  # Director: 영상 합성
    QA = "QA"  # QA Agent: 품질 검수
    END = "END"
    FAILED = "FAILED"


class FSM:
    """
    Finite State Machine for orchestrating shorts generation workflow.

    State transitions:
    INIT → PLOT_GENERATION → PLOT_REVIEW → ASSET_GENERATION → LAYOUT_REVIEW → RENDERING → QA → END
              ↑                   ↓ (재생성)           ↑            ↓ (재생성)                    ↓
              └───────────────────┘                    └────────────┘               PLOT_GENERATION (재시도)
    """

    # Valid state transitions
    TRANSITIONS: Dict[RunState, list[RunState]] = {
        RunState.INIT: [RunState.PLOT_GENERATION, RunState.FAILED],
        RunState.PLOT_GENERATION: [RunState.PLOT_REVIEW, RunState.ASSET_GENERATION, RunState.FAILED],  # Review mode → PLOT_REVIEW, Auto mode → ASSET
        RunState.PLOT_REVIEW: [RunState.ASSET_GENERATION, RunState.PLOT_GENERATION, RunState.FAILED],  # Confirm → ASSET, Regenerate → PLOT
        RunState.ASSET_GENERATION: [RunState.ASSET_REVIEW, RunState.LAYOUT_REVIEW, RunState.RENDERING, RunState.FAILED],  # Review mode → ASSET_REVIEW, General/Ad → RENDERING, Story → LAYOUT_REVIEW
        RunState.ASSET_REVIEW: [RunState.LAYOUT_REVIEW, RunState.RENDERING, RunState.ASSET_GENERATION, RunState.FAILED],  # Confirm → LAYOUT_REVIEW/RENDERING, Regenerate → ASSET
        RunState.LAYOUT_REVIEW: [RunState.RENDERING, RunState.ASSET_GENERATION, RunState.FAILED],  # Confirm → RENDERING, Regenerate → ASSET
        RunState.RENDERING: [RunState.QA, RunState.FAILED],
        RunState.QA: [RunState.END, RunState.PLOT_GENERATION, RunState.FAILED],  # Pass → END, Fail → 재시도
        RunState.END: [],
        RunState.FAILED: [RunState.PLOT_GENERATION, RunState.PLOT_REVIEW],  # Allow retry from FAILED state
    }

    def __init__(self, run_id: str, initial_state: RunState = RunState.INIT):
        """
        Initialize FSM for a run.

        Args:
            run_id: Unique run identifier
            initial_state: Starting state (default: INIT)
        """
        self.run_id = run_id
        self.current_state = initial_state
        self.history: list[RunState] = [initial_state]
        self.metadata: Dict = {}

        logger.info(f"FSM initialized for run {run_id} in state {initial_state.value}")

    def can_transition_to(self, target_state: RunState) -> bool:
        """
        Check if transition to target state is valid.

        Args:
            target_state: Target state

        Returns:
            True if transition is allowed, False otherwise
        """
        allowed_states = self.TRANSITIONS.get(self.current_state, [])
        return target_state in allowed_states

    def transition_to(
        self,
        target_state: RunState,
        guard: Optional[Callable[[], bool]] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Attempt to transition to target state.

        Args:
            target_state: Target state
            guard: Optional guard function that must return True for transition
            metadata: Optional metadata to attach to transition

        Returns:
            True if transition succeeded, False otherwise
        """
        # Check if transition is allowed
        if not self.can_transition_to(target_state):
            logger.warning(
                f"Invalid transition for run {self.run_id}: "
                f"{self.current_state.value} → {target_state.value}"
            )
            return False

        # Check guard condition
        if guard and not guard():
            logger.info(
                f"Guard failed for transition {self.run_id}: "
                f"{self.current_state.value} → {target_state.value}"
            )
            return False

        # Perform transition
        old_state = self.current_state
        self.current_state = target_state
        self.history.append(target_state)

        if metadata:
            self.metadata.update(metadata)

        logger.info(
            f"State transition for run {self.run_id}: "
            f"{old_state.value} → {target_state.value}"
        )

        # Update in Redis after state change
        update_fsm(self)

        return True

    def fail(self, error_message: str):
        """
        Mark run as failed.

        Args:
            error_message: Error description
        """
        self.transition_to(RunState.FAILED, metadata={"error": error_message})
        logger.error(f"Run {self.run_id} failed: {error_message}")

    def retry_from_qa(self) -> bool:
        """
        QA 실패 시 PLOT_GENERATION으로 재시도.

        Returns:
            True if transition succeeded, False otherwise
        """
        if self.current_state != RunState.QA:
            logger.warning(f"Cannot retry: current state is {self.current_state.value}, not QA")
            return False

        return self.transition_to(
            RunState.PLOT_GENERATION,
            metadata={"retry_reason": "QA failed, regenerating plot"}
        )

    def is_terminal(self) -> bool:
        """Check if current state is terminal (END or FAILED)."""
        return self.current_state in [RunState.END, RunState.FAILED]

    def __repr__(self) -> str:
        return f"FSM(run_id={self.run_id}, state={self.current_state.value})"


# Global FSM registry (production: use Redis/DB)
_fsm_registry: Dict[str, FSM] = {}


def get_fsm(run_id: str) -> Optional[FSM]:
    """
    Get FSM instance for run_id.
    Uses Redis for cross-process sharing between FastAPI and Celery.

    IMPORTANT: Always loads from Redis first to ensure fresh state across processes.
    This prevents stale in-memory cache issues when Celery workers share FSM state.
    """
    # Always try Redis first for freshest state (critical for cross-process consistency)
    try:
        from app.config import settings
        import redis
        import pickle

        r = redis.from_url(settings.REDIS_URL)
        fsm_data = r.get(f"fsm:{run_id}")
        if fsm_data:
            fsm = pickle.loads(fsm_data)
            _fsm_registry[run_id] = fsm  # Update in-memory cache
            logger.info(f"Loaded FSM for run {run_id} from Redis")
            return fsm
    except Exception as e:
        logger.error(f"Failed to load FSM from Redis for run {run_id}: {e}")

    # Fallback to in-memory cache only if Redis fails
    if run_id in _fsm_registry:
        logger.warning(f"Using stale in-memory FSM for run {run_id} (Redis unavailable)")
        return _fsm_registry[run_id]

    return None


def register_fsm(fsm: FSM):
    """
    Register FSM instance.
    Saves to both memory and Redis for cross-process sharing.
    """
    _fsm_registry[fsm.run_id] = fsm

    # Save to Redis for Celery workers
    try:
        from app.config import settings
        import redis
        import pickle

        r = redis.from_url(settings.REDIS_URL)
        fsm_data = pickle.dumps(fsm)
        r.setex(f"fsm:{fsm.run_id}", 86400, fsm_data)  # 24 hour TTL
        logger.info(f"Registered FSM for run {fsm.run_id} to Redis")
    except Exception as e:
        logger.error(f"Failed to save FSM to Redis for run {fsm.run_id}: {e}")


def update_fsm(fsm: FSM):
    """
    Update FSM instance in Redis after state changes.
    Called after each transition to keep Redis in sync.
    """
    try:
        from app.config import settings
        import redis
        import pickle

        r = redis.from_url(settings.REDIS_URL)
        fsm_data = pickle.dumps(fsm)
        r.setex(f"fsm:{fsm.run_id}", 86400, fsm_data)  # 24 hour TTL
    except Exception as e:
        logger.error(f"Failed to update FSM in Redis for run {fsm.run_id}: {e}")


def unregister_fsm(run_id: str):
    """Unregister FSM instance from memory and Redis."""
    _fsm_registry.pop(run_id, None)

    try:
        from app.config import settings
        import redis

        r = redis.from_url(settings.REDIS_URL)
        r.delete(f"fsm:{run_id}")
        logger.info(f"Unregistered FSM for run {run_id} from Redis")
    except Exception as e:
        logger.error(f"Failed to delete FSM from Redis for run {run_id}: {e}")


def invalidate_fsm_cache(run_id: str):
    """
    Invalidate in-memory FSM cache for a run_id.
    This forces the next get_fsm() call to reload from Redis.
    Used when cancelling a run to ensure fresh state.
    """
    if run_id in _fsm_registry:
        _fsm_registry.pop(run_id, None)
        logger.info(f"Invalidated FSM cache for run {run_id}")
