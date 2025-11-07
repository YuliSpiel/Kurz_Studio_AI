"""
FastAPI main application entry point.
Provides REST API endpoints and WebSocket for AutoShorts orchestration.
"""

import logging  # Python 표준 로깅 라이브러리
import asyncio  # 비동기 작업을 위한 라이브러리
from contextlib import asynccontextmanager
from typing import Dict, List
from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import orjson
import redis.asyncio as aioredis  # Redis를 비동기적으로 사용하기 위한 라이브러리

from app.config import settings, get_settings
from app.schemas.run_spec import RunSpec, RunStatus
from app.orchestrator.fsm import FSM, RunState
from app.utils.logger import setup_logger
from app.utils.fonts import get_available_fonts

# Setup logging
setup_logger()
logger = logging.getLogger(__name__)

# In-memory run tracking
runs: Dict[str, dict] = {}
websocket_clients: Dict[str, List[WebSocket]] = {}

# Redis clients for pub/sub
redis_client = None  # Async Redis client for pub/sub
pubsub = None  # Redis pub/sub object


async def redis_listener(): # Redis에서 진행도 메시지를 받아서 WebSocket 클라이언트들에게 전달하는 중계자
    """Background task to listen for Redis pub/sub messages and broadcast to WebSockets."""
    global redis_client, pubsub

    redis_client = await aioredis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )
    pubsub = redis_client.pubsub() # 채널 구독/메시지 수신용 객체
    await pubsub.subscribe("autoshorts:progress")

    logger.info("Redis listener started for progress updates")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = orjson.loads(message["data"])
                    run_id = data.get("run_id")

                    if run_id:
                        # Update in-memory state
                        if run_id in runs:
                            if "state" in data:
                                runs[run_id]["state"] = data["state"]
                            if "progress" in data:
                                runs[run_id]["progress"] = data["progress"]
                            if "log" in data:
                                runs[run_id]["logs"].append(data["log"])
                            if "artifacts" in data:
                                runs[run_id]["artifacts"].update(data["artifacts"])

                        # Broadcast to WebSocket clients (include artifacts)
                        await broadcast_to_websockets(
                            run_id,
                            {
                                "type": "progress",
                                "run_id": run_id,
                                "state": data.get("state"),
                                "progress": data.get("progress"),
                                "message": data.get("log", ""),
                                "artifacts": runs[run_id]["artifacts"] if run_id in runs else {},
                            },
                        )

                        logger.info(f"Broadcasted progress update for {run_id}")
                except Exception as e:
                    logger.error(f"Error processing Redis message: {e}")
    except asyncio.CancelledError:
        logger.info("Redis listener cancelled")
    finally:
        await pubsub.unsubscribe("autoshorts:progress")
        await redis_client.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting AutoShorts Backend...")
    logger.info(f"Environment: {settings.ENV}")
    logger.info(f"Image Provider: {settings.IMAGE_PROVIDER}")
    logger.info(f"TTS Provider: {settings.TTS_PROVIDER}")
    logger.info(f"Music Provider: {settings.MUSIC_PROVIDER}")

    # Ensure data directories exist
    Path("app/data/uploads").mkdir(parents=True, exist_ok=True)
    Path("app/data/outputs").mkdir(parents=True, exist_ok=True)
    Path("app/data/samples").mkdir(parents=True, exist_ok=True)

    # Start Redis listener as background task
    listener_task = asyncio.create_task(redis_listener())

    yield

    # Cleanup
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass

    logger.info("Shutting down AutoShorts Backend...")


app = FastAPI(
    title="AutoShorts API",
    description="스토리텔링형 숏츠 자동 제작 시스템",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for generated videos
app.mount("/outputs", StaticFiles(directory="app/data/outputs"), name="outputs")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "AutoShorts API",
        "version": "0.1.0",
        "status": "running",
        "environment": settings.ENV,
    }


@app.post("/api/runs", response_model=RunStatus)
async def create_run(spec: RunSpec):
    """
    Create a new shorts generation run.
    Initializes FSM and kicks off Celery orchestration.
    """
    from app.celery_app import celery
    from app.tasks.plan import plan_task
    import uuid

    # 폴더명으로 사용할 run_id 생성: 타임스탬프_프롬프트첫8글자
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    prompt_clean = "".join(c for c in spec.prompt if not c.isspace())[:8]
    run_id = f"{timestamp}_{prompt_clean}"

    logger.info(f"[DEBUG] Received run request:")
    logger.info(f"[DEBUG]   mode='{spec.mode}'")
    logger.info(f"[DEBUG]   num_cuts={spec.num_cuts}")
    logger.info(f"[DEBUG]   num_characters={spec.num_characters}")
    logger.info(f"[DEBUG]   characters={'YES (' + str(len(spec.characters)) + ' chars)' if spec.characters else 'NO'}")
    logger.info(f"Creating run {run_id} with spec: {spec.mode}, {spec.num_cuts} cuts")

    # Initialize FSM
    fsm = FSM(run_id)

    # Register FSM in global registry (중요!)
    from app.orchestrator.fsm import register_fsm

    register_fsm(fsm)

    # Store run metadata
    runs[run_id] = {
        "run_id": run_id,
        "spec": spec.model_dump(),
        "state": fsm.current_state.value,
        "progress": 0.0,
        "artifacts": {},
        "logs": [],
        "created_at": None,  # Add timestamp in production
    }

    # Transition to PLOT_GENERATION and start async task
    if fsm.transition_to(RunState.PLOT_GENERATION):
        runs[run_id]["state"] = fsm.current_state.value

        # Kick off plot generation task asynchronously
        plan_task.apply_async(args=[run_id, spec.model_dump()])

        await broadcast_to_websockets(
            run_id,
            {
                "type": "state_change",
                "state": fsm.current_state.value,
                "message": "Run created, starting plot generation...",
            },
        )

    return RunStatus(
        run_id=run_id,
        state=fsm.current_state.value,
        progress=0.0,
        artifacts=runs[run_id]["artifacts"],
        logs=runs[run_id]["logs"],
    )


@app.get("/api/runs/{run_id}", response_model=RunStatus)
async def get_run(run_id: str):
    """Get run status and artifacts."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run_data = runs[run_id]
    return RunStatus(
        run_id=run_id,
        state=run_data["state"],
        progress=run_data["progress"],
        artifacts=run_data["artifacts"],
        logs=run_data["logs"],
    )


@app.get("/api/fonts")
async def get_fonts():
    """Get list of available fonts for layout customization."""
    try:
        fonts = get_available_fonts()
        return {"fonts": fonts}
    except Exception as e:
        logger.error(f"Failed to get fonts: {e}")
        return {"fonts": []}


@app.get("/api/fonts/{font_id}")
async def get_font_file(font_id: str):
    """Serve font file for web preview."""
    from pathlib import Path
    from fastapi.responses import FileResponse
    from app.utils.fonts import FONTS_DIR

    # Check for .ttf first, then .otf
    for ext in [".ttf", ".otf"]:
        font_path = FONTS_DIR / f"{font_id}{ext}"
        if font_path.exists():
            return FileResponse(
                font_path,
                media_type=f"font/{ext[1:]}",  # "font/ttf" or "font/otf"
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 1 day
                    "Access-Control-Allow-Origin": "*"
                }
            )

    # System fonts can't be served
    raise HTTPException(status_code=404, detail=f"Font file not found: {font_id}")


@app.post("/api/uploads")
async def upload_reference_image(file: UploadFile = File(...)):
    """
    Upload reference image for ComfyUI.
    Saves to app/data/uploads/ and returns filename.
    """
    import uuid
    from pathlib import Path

    # Generate unique filename
    ext = Path(file.filename).suffix
    filename = f"ref_{uuid.uuid4().hex}{ext}"
    filepath = Path("app/data/uploads") / filename

    # Save file
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    logger.info(f"Uploaded reference image: {filename}")

    return {"filename": filename, "path": str(filepath), "size": len(content)}


@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """
    WebSocket endpoint for real-time run progress updates.
    """
    await websocket.accept()

    if run_id not in websocket_clients:
        websocket_clients[run_id] = []
    websocket_clients[run_id].append(websocket)

    logger.info(f"WebSocket connected for run {run_id}")

    try:
        # Send initial state
        if run_id in runs:
            await websocket.send_text(
                orjson.dumps(
                    {
                        "type": "initial_state",
                        "state": runs[run_id]["state"],
                        "progress": runs[run_id]["progress"],
                        "artifacts": runs[run_id]["artifacts"],
                        "logs": runs[run_id]["logs"],
                    }
                ).decode()
            )

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_text(orjson.dumps({"type": "pong"}).decode())

    except WebSocketDisconnect:
        websocket_clients[run_id].remove(websocket)
        logger.info(f"WebSocket disconnected for run {run_id}")


async def broadcast_to_websockets(run_id: str, message: dict):
    """Broadcast message to all WebSocket clients for a run."""
    if run_id in websocket_clients:
        dead_clients = []
        for client in websocket_clients[run_id]:
            try:
                await client.send_text(orjson.dumps(message).decode())
            except Exception as e:
                logger.error(f"Failed to send to WebSocket: {e}")
                dead_clients.append(client)

        # Cleanup dead connections
        for client in dead_clients:
            websocket_clients[run_id].remove(client)


# Helper to update run state (called by Celery tasks)
def update_run_state(
    run_id: str,
    state: str = None,
    progress: float = None,
    artifacts: dict = None,
    log_message: str = None,
):
    """Update run state and broadcast to WebSocket clients."""
    if run_id not in runs:
        return

    if state:
        runs[run_id]["state"] = state
    if progress is not None:
        runs[run_id]["progress"] = progress
    if artifacts:
        runs[run_id]["artifacts"].update(artifacts)
    if log_message:
        runs[run_id]["logs"].append(log_message)

    # Note: In async context, use asyncio.create_task to broadcast
    # For simplicity, this is a sync function called from Celery


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=settings.ENV == "dev"
    )
