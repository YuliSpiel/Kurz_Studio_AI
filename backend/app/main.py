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
    Body,
    Request,
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
from app.utils.auth import get_current_user
from app.routers import auth, runs as runs_router
from app.database import get_db
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

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

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(runs_router.router, prefix="/api")


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
async def create_run(
    spec: RunSpec,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new shorts generation run.
    Initializes FSM and kicks off Celery orchestration.
    Authentication is required.
    """
    from app.celery_app import celery
    from app.tasks.plan import plan_task
    from app.models.run import Run as RunModel, RunMode, RunState as DBRunState
    import uuid

    # 폴더명으로 사용할 run_id 생성: 타임스탬프_프롬프트첫8글자
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    # 한글, 영문, 숫자만 남기고 특수문자 제거
    prompt_clean = "".join(c for c in spec.prompt if c.isalnum())[:8]
    run_id = f"{timestamp}_{prompt_clean}"

    # Log user info
    logger.info(f"[DEBUG] Received run request from user {current_user.username} ({current_user.id}):")
    logger.info(f"[DEBUG]   mode='{spec.mode}'")
    logger.info(f"[DEBUG]   num_cuts={spec.num_cuts}")
    logger.info(f"[DEBUG]   num_characters={spec.num_characters}")
    logger.info(f"[DEBUG]   characters={'YES (' + str(len(spec.characters)) + ' chars)' if spec.characters else 'NO'}")
    logger.info(f"[DEBUG]   review_mode={spec.review_mode}")
    logger.info(f"Creating run {run_id} with spec: {spec.mode}, {spec.num_cuts} cuts")

    # Save run to database
    db_run = RunModel(
        run_id=run_id,
        user_id=current_user.id,
        mode=RunMode(spec.mode),
        prompt=spec.prompt,
        num_cuts=spec.num_cuts,
        num_characters=spec.num_characters,
        state=DBRunState.IDLE,
        progress=0,
    )
    db.add(db_run)
    await db.commit()
    logger.info(f"[{run_id}] Saved to database with user_id={current_user.id}")

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
        "mode": spec.mode,  # Add mode for easy access
        "user_id": str(current_user.id),  # Store user_id in memory
    }

    logger.info(f"[{run_id}] Added to runs dict. Total runs: {len(runs)}")
    logger.info(f"[{run_id}] Verification: run_id in runs = {run_id in runs}")

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


@app.post("/api/v1/enhance-prompt")
async def enhance_prompt_endpoint(request: dict):
    """
    Enhance user prompt using AI analysis.

    Request body:
        {
            "original_prompt": "사용자 입력 프롬프트",
            "mode": "general" (optional, default: "general")
        }

    Response:
        {
            "enhanced_prompt": "풍부화된 프롬프트",
            "suggested_title": "제안된 영상 제목",
            "suggested_num_cuts": 3,
            "suggested_art_style": "파스텔 수채화",
            "suggested_music_genre": "ambient",
            "suggested_num_characters": 1,
            "reasoning": "제안 이유"
        }
    """
    from app.utils.prompt_enhancer import enhance_prompt

    original_prompt = request.get("original_prompt")
    mode = request.get("mode", "general")

    if not original_prompt:
        raise HTTPException(status_code=400, detail="original_prompt is required")

    if mode not in ["general", "story", "ad"]:
        raise HTTPException(status_code=400, detail="mode must be 'general', 'story', or 'ad'")

    try:
        logger.info(f"[ENHANCE] Enhancing prompt for mode={mode}: '{original_prompt[:50]}...'")
        result = enhance_prompt(original_prompt, mode)
        logger.info(f"[ENHANCE] Successfully enhanced prompt")
        return result
    except ValueError as e:
        logger.error(f"[ENHANCE] Validation error: {e}")
        # Raise HTTP 500 error so frontend shows error modal
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"[ENHANCE] Failed to enhance prompt: {e}", exc_info=True)
        # Raise HTTP 500 error so frontend shows error modal
        raise HTTPException(status_code=500, detail=f"프롬프트 분석 중 오류 발생: {str(e)}")


@app.get("/api/v1/runs/{run_id}/plot-json")
async def get_plot_json(run_id: str):
    """
    Get plot as JSON for user editing.

    Response:
        {
            "run_id": "abc123",
            "plot": {...},  // plot.json content
            "mode": "general"
        }
    """
    logger.info(f"[{run_id}] plot-json requested")
    logger.info(f"[{run_id}] run_id in runs dict: {run_id in runs}")

    # Try to get plot_json_path from runs dict if available
    plot_json_path = None
    mode = "general"  # default mode

    if run_id in runs:
        run_data = runs[run_id]
        plot_json_path = run_data["artifacts"].get("plot_json_path")
        mode = run_data.get("spec", {}).get("mode", mode)

    # Fallback: construct path from run_id (useful after server restart)
    if not plot_json_path:
        plot_json_path = settings.OUTPUT_DIR / run_id / "plot.json"
        logger.info(f"[{run_id}] Using fallback path: {plot_json_path}")

    # Convert to Path if it's a string
    plot_json_path = Path(plot_json_path) if not isinstance(plot_json_path, Path) else plot_json_path

    # Check if file exists
    if not plot_json_path.exists():
        # Provide more helpful error message
        if run_id not in runs:
            logger.warning(f"[{run_id}] Run not in memory (server may have restarted) and file not found at: {plot_json_path}")
            # Check if run directory exists
            run_dir = settings.OUTPUT_DIR / run_id
            if run_dir.exists():
                logger.info(f"[{run_id}] Run directory exists, checking for plot.json...")
                if (run_dir / "plot.json").exists():
                    plot_json_path = run_dir / "plot.json"
                    logger.info(f"[{run_id}] Found plot.json in run directory")
                else:
                    raise HTTPException(status_code=404, detail=f"Plot JSON not found. The run may still be generating.")
            else:
                raise HTTPException(status_code=404, detail=f"Run directory not found.")
        else:
            logger.warning(f"[{run_id}] File not found at: {plot_json_path}")
            raise HTTPException(status_code=404, detail=f"Plot JSON file not generated yet. Please wait...")

    try:
        import json
        plot_content = json.loads(Path(plot_json_path).read_text(encoding="utf-8"))

        # Try to infer mode from plot content if not available
        if "scenes" in plot_content:
            first_scene = plot_content["scenes"][0] if plot_content["scenes"] else {}
            # Story mode has char1_id, General/Ad mode has image_prompt
            if "char1_id" in first_scene:
                mode = "story"
            elif "image_prompt" in first_scene:
                mode = "general"  # or could be "ad", but we default to general

        logger.info(f"[{run_id}] Successfully loaded plot.json (mode: {mode})")
        return {
            "run_id": run_id,
            "plot": plot_content,
            "mode": mode
        }
    except Exception as e:
        logger.error(f"[{run_id}] Failed to read plot JSON: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read plot JSON: {str(e)}")


@app.post("/api/v1/runs/{run_id}/plot-confirm")
async def confirm_plot(
    run_id: str,
    request: dict = Body(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm plot and proceed to asset generation.

    CRITICAL: This endpoint requires authentication.

    Request body (optional):
        {
            "edited_plot": {...} (optional - if user edited plot JSON)
        }

    Response:
        {
            "status": "success",
            "message": "Plot confirmed, proceeding to asset generation"
        }
    """
    logger.info(f"[{run_id}] ========== PLOT-CONFIRM REQUEST RECEIVED ==========")
    logger.info(f"[{run_id}] User: {current_user.username} ({current_user.id})")
    logger.info(f"[{run_id}] Request body: {request}")

    from app.orchestrator.fsm import get_fsm, RunState
    from app.tasks.designer import designer_task
    from app.tasks.composer import composer_task
    from app.tasks.voice import voice_task
    from app.tasks.director import layout_ready_task
    from celery import chord, group
    from app.utils.progress import publish_progress

    # Check if run exists (either in memory or on filesystem)
    output_dir = Path(f"app/data/outputs/{run_id}")
    if run_id not in runs and not output_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # CRITICAL: Clear in-memory cache to force reload from Redis
    # This ensures we get the latest FSM state updated by Celery worker
    from app.orchestrator.fsm import _fsm_registry
    if run_id in _fsm_registry:
        del _fsm_registry[run_id]
        logger.info(f"[{run_id}] Cleared FSM from memory cache to force Redis reload")

    fsm = get_fsm(run_id)
    if not fsm:
        raise HTTPException(status_code=404, detail=f"FSM not found for run {run_id}")

    if fsm.current_state != RunState.PLOT_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm plot: current state is {fsm.current_state.value}, expected PLOT_REVIEW"
        )

    # Check ownership: only the run owner can confirm the plot
    from app.models.run import Run as RunModel
    from sqlalchemy import select as sql_select
    result = await db.execute(
        sql_select(RunModel).where(RunModel.run_id == run_id)
    )
    db_run = result.scalars().first()

    if db_run and db_run.user_id != current_user.id:
        logger.warning(f"[{run_id}] User {current_user.username} tried to confirm plot owned by user_id {db_run.user_id}")
        raise HTTPException(status_code=403, detail="You don't have permission to confirm this plot")

    try:
        import json

        # Determine paths (from memory or filesystem)
        if run_id in runs:
            plot_json_path = runs[run_id]["artifacts"].get("plot_json_path")
            characters_json_path = runs[run_id]["artifacts"].get("characters_path")
            layout_json_path = runs[run_id]["artifacts"].get("json_path")
            spec = runs[run_id].get("spec", {})

            # CRITICAL: If layout_json_path is None, fallback to filesystem
            if layout_json_path is None:
                layout_json_path = output_dir / "layout.json"
                logger.warning(f"[{run_id}] layout_json_path was None in runs dict, using filesystem fallback")

            # Ensure all paths exist, if not fallback to filesystem
            if plot_json_path is None:
                plot_json_path = output_dir / "plot.json"
            if characters_json_path is None:
                characters_json_path = output_dir / "characters.json"
        else:
            # Fallback to filesystem
            plot_json_path = output_dir / "plot.json"
            characters_json_path = output_dir / "characters.json"
            layout_json_path = output_dir / "layout.json"
            # Try to load spec from layout.json if it exists
            spec = {}
            if layout_json_path.exists():
                with open(layout_json_path, 'r', encoding='utf-8') as f:
                    layout_data = json.load(f)
                    spec = layout_data.get("spec", {})

        # If user edited plot, update plot.json and regenerate layout.json
        if request and "edited_plot" in request:
            edited_plot = request["edited_plot"]

            # Save edited plot.json
            with open(plot_json_path, 'w', encoding='utf-8') as f:
                json.dump(edited_plot, f, indent=2, ensure_ascii=False)

            logger.info(f"[{run_id}] Updated plot.json from user edits")

            # Regenerate layout.json from updated plot.json
            from app.utils.json_converter import convert_plot_to_json

            characters_data = None
            if Path(characters_json_path).exists():
                with open(characters_json_path, 'r', encoding='utf-8') as f:
                    characters_data = json.load(f)

            # Update plot.json with edited characters if they exist
            if "characters" in edited_plot:
                # Update appearance field in characters.json from description in edited_plot
                updated_characters_list = []
                for char in edited_plot["characters"]:
                    char_copy = {
                        "char_id": char["char_id"],
                        "name": char["name"],
                        "appearance": char.get("description", ""),  # Map description -> appearance
                    }
                    # Preserve voice_id and seed if they exist in original characters.json
                    if characters_data:
                        for orig_char in characters_data.get("characters", []):
                            if orig_char["char_id"] == char["char_id"]:
                                char_copy["voice_id"] = orig_char.get("voice_id")
                                char_copy["seed"] = orig_char.get("seed")
                                break
                    updated_characters_list.append(char_copy)

                updated_characters = {"characters": updated_characters_list}
                with open(characters_json_path, 'w', encoding='utf-8') as f:
                    json.dump(updated_characters, f, indent=2, ensure_ascii=False)
                logger.info(f"[{run_id}] Updated characters.json from edited plot")

            # Convert plot.json to layout.json
            layout_path = convert_plot_to_json(
                plot_json_path=str(plot_json_path),
                run_id=run_id,
                art_style=spec.get("art_style", "파스텔 수채화"),
                music_genre=spec.get("music_genre", "ambient"),
                video_title=spec.get("video_title"),
                layout_config=spec.get("layout_config"),
                review_mode=spec.get("review_mode", False)
            )

            # Update runs if in memory
            if run_id in runs:
                runs[run_id]["artifacts"]["json_path"] = str(layout_path)

            logger.info(f"[{run_id}] Regenerated layout.json from edited plot")

        # Transition to ASSET_GENERATION
        publish_progress(run_id, progress=0.25, log="플롯 확정 - 에셋 생성 시작...")
        if fsm.transition_to(RunState.ASSET_GENERATION):
            logger.info(f"[{run_id}] Plot confirmed, transitioning to ASSET_GENERATION")
            publish_progress(run_id, state="ASSET_GENERATION", progress=0.3, log="에셋 생성 시작 (디자이너, 작곡가, 성우)")

            # Update state in memory if run exists
            if run_id in runs:
                runs[run_id]["state"] = fsm.current_state.value

            # Use layout_json_path from above (already determined)
            json_path_str = str(layout_json_path)

            asset_tasks = group(
                designer_task.s(run_id, json_path_str, spec),
                composer_task.s(run_id, json_path_str, spec),
                voice_task.s(run_id, json_path_str, spec),
            )

            workflow = chord(asset_tasks)(layout_ready_task.s(run_id, json_path_str))
            logger.info(f"[{run_id}] Asset generation chord started (will transition to LAYOUT_REVIEW)")

            return {
                "status": "success",
                "message": "Plot confirmed, proceeding to asset generation"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to transition to ASSET_GENERATION")

    except Exception as e:
        logger.error(f"[{run_id}] Failed to confirm plot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to confirm plot: {str(e)}")


@app.post("/api/v1/runs/{run_id}/plot-regenerate")
async def regenerate_plot(run_id: str):
    """
    Regenerate plot with higher temperature for variety.

    Response:
        {
            "status": "success",
            "message": "Plot regeneration started"
        }
    """
    from app.orchestrator.fsm import get_fsm, RunState, register_fsm, FSM
    from app.tasks.plan import plan_task
    from app.utils.progress import publish_progress
    import json

    # Check if run exists in memory or can be restored from filesystem
    output_dir = settings.OUTPUT_DIR / run_id
    spec = None

    if run_id not in runs:
        # Try to restore from filesystem
        layout_json_path = output_dir / "layout.json"
        if not layout_json_path.exists():
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found (no layout.json)")

        # Load spec from layout.json
        try:
            with open(layout_json_path, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)
                spec = layout_data.get("spec", {})
                if not spec:
                    # Reconstruct minimal spec from layout
                    layout_config = layout_data.get("layout_config", {})
                    spec = {
                        "mode": layout_data.get("mode", "general"),
                        "prompt": layout_data.get("title", ""),
                        "art_style": layout_config.get("art_style", "파스텔 수채화"),
                        "review_mode": True,
                    }
                # Ensure required fields have defaults
                spec.setdefault("num_characters", 2)
                spec.setdefault("num_cuts", 7)
                spec.setdefault("mode", "general")
                spec.setdefault("review_mode", True)
                spec.setdefault("art_style", "파스텔 수채화")
                spec.setdefault("music_genre", "ambient")
            logger.info(f"[{run_id}] Restored spec from filesystem for plot regeneration: {spec}")
        except Exception as e:
            logger.error(f"[{run_id}] Failed to load spec from layout.json: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to restore run spec: {str(e)}")

        # Create in-memory run entry
        runs[run_id] = {
            "spec": spec,
            "state": "PLOT_REVIEW",
            "progress": 0.0,
            "logs": [],
            "artifacts": {},
        }
    else:
        spec = runs[run_id]["spec"]

    # Get or create FSM
    fsm = get_fsm(run_id)
    if not fsm:
        # Create new FSM in PLOT_REVIEW state (since we're regenerating from review)
        fsm = FSM(run_id, initial_state=RunState.PLOT_REVIEW)
        register_fsm(fsm)
        logger.info(f"[{run_id}] Created new FSM in PLOT_REVIEW state")

    # Handle FAILED state - allow recovery by transitioning to PLOT_REVIEW first
    if fsm.current_state == RunState.FAILED:
        logger.info(f"[{run_id}] Recovering from FAILED state, transitioning to PLOT_REVIEW first")
        if not fsm.transition_to(RunState.PLOT_REVIEW):
            raise HTTPException(status_code=500, detail="Failed to recover from FAILED state")

    if fsm.current_state != RunState.PLOT_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot regenerate plot: current state is {fsm.current_state.value}, expected PLOT_REVIEW"
        )

    try:
        # Transition back to PLOT_GENERATION
        publish_progress(run_id, progress=0.1, log="플롯 재생성 요청 - 기획자 다시 작업 중...")
        if fsm.transition_to(RunState.PLOT_GENERATION):
            logger.info(f"[{run_id}] Plot regeneration requested, transitioning back to PLOT_GENERATION")

            runs[run_id]["state"] = fsm.current_state.value

            # Restart plan task
            plan_task.delay(run_id, spec)
            logger.info(f"[{run_id}] Plan task restarted for plot regeneration")

            return {
                "status": "success",
                "message": "Plot regeneration started"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to transition to PLOT_GENERATION")

    except Exception as e:
        logger.error(f"[{run_id}] Failed to regenerate plot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to regenerate plot: {str(e)}")


@app.post("/api/v1/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    """
    Cancel a running video generation task.
    Revokes all pending/running Celery tasks and marks FSM as FAILED.
    """
    from app.api.cancel import cancel_run_handler
    return await cancel_run_handler(run_id, runs)


@app.get("/api/v1/runs/{run_id}/layout-config")
async def get_layout_config(run_id: str):
    """
    Get current layout configuration from layout.json.

    Response:
        {
            "run_id": "abc123",
            "layout_config": {
                "use_title_block": true,
                "title_bg_color": "#323296",
                "title_font_size": 100,
                "subtitle_font_size": 80,
                "title_font": "Paperlogy-7Bold",
                "subtitle_font": "Paperlogy-4Regular"
            },
            "title": "Project Title"
        }
    """
    logger.info(f"[{run_id}] layout-config requested")

    # Try to get layout_json_path from runs dict if available
    layout_json_path = None

    if run_id in runs:
        layout_json_path = runs[run_id]["artifacts"].get("json_path")

    # Fallback: construct path from run_id
    if not layout_json_path:
        layout_json_path = Path(f"app/data/outputs/{run_id}/layout.json").resolve()
        logger.info(f"[{run_id}] Using fallback path: {layout_json_path}")

    # Check if file exists
    if not Path(layout_json_path).exists():
        raise HTTPException(status_code=404, detail=f"Layout JSON not found for run {run_id}")

    try:
        import json
        layout_content = json.loads(Path(layout_json_path).read_text(encoding="utf-8"))

        layout_config = layout_content.get("metadata", {}).get("layout_config", {})
        title = layout_content.get("title", "")

        # Return empty config if not set - frontend will use user's saved VideoSettings as defaults
        # This allows user's profile settings to be applied as the default layout values
        logger.info(f"[{run_id}] Successfully loaded layout config (has_config={bool(layout_config)})")
        return {
            "run_id": run_id,
            "layout_config": layout_config,
            "title": title
        }

    except Exception as e:
        logger.error(f"[{run_id}] Failed to load layout config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load layout config: {str(e)}")


@app.post("/api/v1/runs/{run_id}/layout-confirm")
async def confirm_layout(run_id: str, request: Dict = Body(default={})):
    """
    Confirm layout and proceed to video rendering.
    Optionally accepts updated layout_config and title.

    Request Body (optional):
        {
            "layout_config": {
                "use_title_block": true,
                "title_bg_color": "#323296",
                "title_font_size": 100,
                "subtitle_font_size": 80,
                "title_font": "Paperlogy-7Bold",
                "subtitle_font": "Paperlogy-4Regular"
            },
            "title": "Updated video title"
        }

    Response:
        {
            "status": "success",
            "message": "Layout confirmed, proceeding to rendering"
        }
    """
    from app.orchestrator.fsm import get_fsm, RunState
    from app.tasks.director import director_task
    from app.utils.progress import publish_progress

    # Check if run exists (either in memory or on filesystem)
    output_dir = Path(f"app/data/outputs/{run_id}")
    if run_id not in runs and not output_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # CRITICAL: Clear in-memory cache to force reload from Redis
    from app.orchestrator.fsm import _fsm_registry
    if run_id in _fsm_registry:
        del _fsm_registry[run_id]
        logger.info(f"[{run_id}] Cleared FSM from memory cache to force Redis reload")

    fsm = get_fsm(run_id)
    if not fsm:
        raise HTTPException(status_code=404, detail=f"FSM not found for run {run_id}")

    if fsm.current_state != RunState.LAYOUT_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm layout: current state is {fsm.current_state.value}, expected LAYOUT_REVIEW"
        )

    try:
        import json

        # Determine paths (from memory or filesystem)
        if run_id in runs:
            layout_json_path = runs[run_id]["artifacts"].get("json_path")
            if layout_json_path is None:
                layout_json_path = output_dir / "layout.json"
        else:
            layout_json_path = output_dir / "layout.json"

        if not Path(layout_json_path).exists():
            raise HTTPException(status_code=404, detail=f"Layout JSON not found for run {run_id}")

        # If user updated layout_config or title, save it to layout.json
        if request and ("layout_config" in request or "title" in request):
            # Load current layout.json
            with open(layout_json_path, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)

            # Update layout_config in metadata if provided
            if "layout_config" in request:
                updated_config = request["layout_config"]
                if "metadata" not in layout_data:
                    layout_data["metadata"] = {}
                layout_data["metadata"]["layout_config"] = updated_config
                logger.info(f"[{run_id}] Updated layout_config in layout.json: {updated_config}")

            # Update title if provided
            if "title" in request:
                updated_title = request["title"]
                layout_data["title"] = updated_title
                logger.info(f"[{run_id}] Updated title in layout.json: {updated_title}")

            # Save updated layout.json
            with open(layout_json_path, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, indent=2, ensure_ascii=False)

        # Transition to RENDERING
        publish_progress(run_id, progress=0.65, log="레이아웃 확정 - 영상 합성 시작...")
        if fsm.transition_to(RunState.RENDERING):
            logger.info(f"[{run_id}] Layout confirmed, transitioning to RENDERING")
            publish_progress(run_id, state="RENDERING", progress=0.7, log="영상 합성 시작 (감독)")

            # Update state in memory if run exists
            if run_id in runs:
                runs[run_id]["state"] = fsm.current_state.value

            # Start rendering task
            # Note: director_task expects (asset_results, run_id, json_path)
            # When called from layout-confirm (not from chord callback), pass empty list for asset_results
            director_task.delay([], run_id, str(layout_json_path))
            logger.info(f"[{run_id}] Director task started for rendering")

            return {
                "status": "success",
                "message": "Layout confirmed, proceeding to rendering"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to transition to RENDERING")

    except Exception as e:
        logger.error(f"[{run_id}] Failed to confirm layout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to confirm layout: {str(e)}")


@app.post("/api/v1/runs/{run_id}/layout-regenerate")
async def regenerate_layout(run_id: str):
    """
    Regenerate assets (images, audio, music) if user rejects layout.

    Response:
        {
            "status": "success",
            "message": "Asset regeneration started"
        }
    """
    from app.orchestrator.fsm import get_fsm, RunState
    from app.tasks.designer import designer_task
    from app.tasks.composer import composer_task
    from app.tasks.voice import voice_task
    from app.tasks.director import layout_ready_task
    from celery import chord, group
    from app.utils.progress import publish_progress

    if run_id not in runs:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    fsm = get_fsm(run_id)
    if not fsm:
        raise HTTPException(status_code=404, detail=f"FSM not found for run {run_id}")

    if fsm.current_state != RunState.LAYOUT_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot regenerate layout: current state is {fsm.current_state.value}, expected LAYOUT_REVIEW"
        )

    try:
        # Transition back to ASSET_GENERATION
        publish_progress(run_id, progress=0.3, log="레이아웃 재생성 요청 - 에셋 다시 생성 중...")
        if fsm.transition_to(RunState.ASSET_GENERATION):
            logger.info(f"[{run_id}] Layout regeneration requested, transitioning back to ASSET_GENERATION")

            runs[run_id]["state"] = fsm.current_state.value

            # Get paths and spec
            output_dir = Path(f"app/data/outputs/{run_id}")
            layout_json_path = runs[run_id]["artifacts"].get("json_path") or output_dir / "layout.json"
            spec = runs[run_id].get("spec", {})

            # Restart asset generation chord
            asset_tasks = group(
                designer_task.s(run_id, str(layout_json_path), spec),
                composer_task.s(run_id, str(layout_json_path), spec),
                voice_task.s(run_id, str(layout_json_path), spec),
            )

            workflow = chord(asset_tasks)(layout_ready_task.s(run_id, str(layout_json_path)))
            logger.info(f"[{run_id}] Asset generation chord restarted for layout regeneration")

            return {
                "status": "success",
                "message": "Asset regeneration started"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to transition to ASSET_GENERATION")

    except Exception as e:
        logger.error(f"[{run_id}] Failed to regenerate layout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to regenerate layout: {str(e)}")


# ============ Asset Review Endpoints ============

@app.get("/api/v1/runs/{run_id}/assets")
async def get_assets(run_id: str):
    """
    Get assets (scenes with images, BGM) for review.
    """
    from pathlib import Path

    output_dir = settings.OUTPUT_DIR / run_id
    layout_json_path = output_dir / "layout.json"
    plot_json_path = output_dir / "plot.json"

    if not layout_json_path.exists():
        raise HTTPException(status_code=404, detail="Layout not found")

    with open(layout_json_path, "r") as f:
        layout = orjson.loads(f.read())

    # Load plot.json for original prompts (with {char_1} variables)
    plot_prompts = {}
    if plot_json_path.exists():
        with open(plot_json_path, "r") as f:
            plot_data = orjson.loads(f.read())
            for plot_scene in plot_data.get("scenes", []):
                scene_id = plot_scene.get("scene_id")
                if scene_id and plot_scene.get("image_prompt"):
                    plot_prompts[scene_id] = plot_scene["image_prompt"]

    # Build scenes array
    scenes = []
    for i, scene in enumerate(layout.get("scenes", [])):
        scene_id = scene.get("scene_id", f"scene_{i+1}")
        scene_number = i + 1

        # Get image URL
        image_url = None
        for img in scene.get("images", []):
            if img.get("image_url"):
                # Convert file path to URL
                image_path = img["image_url"]
                if Path(image_path).exists():
                    image_url = f"/outputs/{run_id}/{Path(image_path).name}"
                break

        # Get image prompt from plot.json (original with {char_1} variables)
        # Fall back to layout.json if not found
        image_prompt = plot_prompts.get(scene_id)
        if not image_prompt:
            for img in scene.get("images", []):
                if img.get("image_prompt"):
                    image_prompt = img["image_prompt"]
                    break

        # Get narration text
        narration = None
        for text in scene.get("texts", []):
            if text.get("text"):
                narration = text["text"]
                break

        scenes.append({
            "scene_id": scene_id,
            "scene_number": scene_number,
            "image_url": image_url,
            "image_prompt": image_prompt,
            "narration": narration
        })

    # Get BGM info
    global_bgm = layout.get("global_bgm", {})
    bgm_audio_url = None
    if global_bgm.get("audio_url"):
        bgm_path = global_bgm["audio_url"]
        if Path(bgm_path).exists():
            bgm_audio_url = f"/outputs/{run_id}/audio/{Path(bgm_path).name}"

    bgm = {
        "audio_url": bgm_audio_url,
        "prompt": global_bgm.get("prompt")
    }

    return {
        "run_id": run_id,
        "scenes": scenes,
        "bgm": bgm
    }


@app.post("/api/v1/runs/{run_id}/assets/confirm")
async def confirm_assets(run_id: str):
    """
    Confirm assets and proceed to LAYOUT_REVIEW or RENDERING.
    """
    from app.orchestrator.fsm import get_fsm, RunState
    from app.tasks.director import director_task, layout_ready_task
    from app.utils.progress import publish_progress

    fsm = get_fsm(run_id)

    if not fsm:
        raise HTTPException(status_code=404, detail="Run not found")

    # If already in LAYOUT_REVIEW, trigger layout_ready_task to move to next stage
    if fsm.current_state == RunState.LAYOUT_REVIEW:
        logger.info(f"[{run_id}] Already in LAYOUT_REVIEW, triggering layout_ready_task")

        # Get layout.json path
        output_dir = settings.OUTPUT_DIR / run_id
        layout_json_path = output_dir / "layout.json"

        if not layout_json_path.exists():
            raise HTTPException(status_code=404, detail="Layout not found")

        # Trigger layout_ready_task to handle LAYOUT_REVIEW → RENDERING transition
        layout_ready_task.delay([], run_id, str(layout_json_path))

        publish_progress(
            run_id,
            state="LAYOUT_REVIEW",
            progress=0.65,
            log="레이아웃 검수 단계로 진행 중..."
        )
        return {"status": "confirmed", "next_state": "LAYOUT_REVIEW"}

    # If already past LAYOUT_REVIEW, return success (idempotent)
    if fsm.current_state in [RunState.RENDERING, RunState.QA, RunState.END]:
        logger.info(f"[{run_id}] Assets already confirmed, current state: {fsm.current_state.value}")
        return {"status": "confirmed", "next_state": fsm.current_state.value}

    if fsm.current_state != RunState.ASSET_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm assets: current state is {fsm.current_state.value}, expected ASSET_REVIEW"
        )

    # Get layout.json path
    output_dir = settings.OUTPUT_DIR / run_id
    layout_json_path = output_dir / "layout.json"

    if not layout_json_path.exists():
        raise HTTPException(status_code=404, detail="Layout not found")

    # Transition to LAYOUT_REVIEW (for review mode)
    if fsm.transition_to(RunState.LAYOUT_REVIEW):
        logger.info(f"[{run_id}] Transitioned from ASSET_REVIEW to LAYOUT_REVIEW")
        publish_progress(
            run_id,
            state="LAYOUT_REVIEW",
            progress=0.65,
            log="에셋 검수 완료 - 레이아웃 검수 단계"
        )
        return {"status": "confirmed", "next_state": "LAYOUT_REVIEW"}
    else:
        raise HTTPException(status_code=500, detail="Failed to transition to LAYOUT_REVIEW")


@app.post("/api/v1/runs/{run_id}/assets/regenerate-image/{scene_id}")
async def regenerate_scene_image(run_id: str, scene_id: str, request: Request):
    """
    Regenerate image for a specific scene.
    """
    from pathlib import Path
    from app.orchestrator.fsm import get_fsm, RunState
    from app.providers.images.gemini_image_client import GeminiImageClient

    fsm = get_fsm(run_id)

    if not fsm:
        raise HTTPException(status_code=404, detail="Run not found")

    if fsm.current_state != RunState.ASSET_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot regenerate image: current state is {fsm.current_state.value}, expected ASSET_REVIEW"
        )

    # Get request body
    body = await request.json() if await request.body() else {}
    new_prompt = body.get("image_prompt")

    # Get layout.json
    output_dir = settings.OUTPUT_DIR / run_id
    layout_json_path = output_dir / "layout.json"

    if not layout_json_path.exists():
        raise HTTPException(status_code=404, detail="Layout not found")

    with open(layout_json_path, "r") as f:
        layout = orjson.loads(f.read())

    # Find the scene
    scene_idx = None
    for i, scene in enumerate(layout.get("scenes", [])):
        if scene.get("scene_id") == scene_id:
            scene_idx = i
            break

    if scene_idx is None:
        raise HTTPException(status_code=404, detail=f"Scene {scene_id} not found")

    scene = layout["scenes"][scene_idx]

    # Update prompt if provided
    if new_prompt:
        for img in scene.get("images", []):
            img["image_prompt"] = new_prompt

    # Regenerate image
    try:
        image_prompt = new_prompt or scene.get("images", [{}])[0].get("image_prompt", "")
        mode = layout.get("metadata", {}).get("mode", "general")

        # Use GeminiImageClient to generate new image
        client = GeminiImageClient(api_key=settings.GEMINI_API_KEY)

        # Determine aspect ratio based on mode
        if mode == "general":
            width, height = 1024, 1024  # 1:1 for general mode
        else:
            width, height = 768, 1024  # 9:16 for story mode

        output_prefix = str(output_dir / f"{scene_id}_center")
        new_image_path = client.generate_image(
            prompt=image_prompt,
            width=width,
            height=height,
            output_prefix=output_prefix
        )

        # Update layout.json with new image path
        for img in scene.get("images", []):
            img["image_url"] = str(new_image_path)

        with open(layout_json_path, "wb") as f:
            f.write(orjson.dumps(layout, option=orjson.OPT_INDENT_2))

        logger.info(f"[{run_id}] Regenerated image for {scene_id}")

        return {
            "status": "regenerated",
            "image_url": f"/outputs/{run_id}/{Path(new_image_path).name}"
        }

    except Exception as e:
        logger.error(f"[{run_id}] Failed to regenerate image for {scene_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to regenerate image: {str(e)}")


@app.post("/api/v1/runs/{run_id}/assets/regenerate-bgm")
async def regenerate_bgm(run_id: str, request: Request):
    """
    Regenerate background music.
    """
    from pathlib import Path
    from app.orchestrator.fsm import get_fsm, RunState
    from app.providers.music.elevenlabs_music_client import ElevenLabsMusicClient

    fsm = get_fsm(run_id)

    if not fsm:
        raise HTTPException(status_code=404, detail="Run not found")

    if fsm.current_state != RunState.ASSET_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot regenerate BGM: current state is {fsm.current_state.value}, expected ASSET_REVIEW"
        )

    # Get request body
    body = await request.json() if await request.body() else {}
    new_prompt = body.get("prompt")

    # Get layout.json
    output_dir = settings.OUTPUT_DIR / run_id
    layout_json_path = output_dir / "layout.json"

    if not layout_json_path.exists():
        raise HTTPException(status_code=404, detail="Layout not found")

    with open(layout_json_path, "r") as f:
        layout = orjson.loads(f.read())

    # Get current BGM prompt or use new one
    global_bgm = layout.get("global_bgm", {})
    bgm_prompt = new_prompt or global_bgm.get("prompt", "upbeat background music")

    try:
        # Generate new BGM using ElevenLabs
        audio_dir = output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        client = ElevenLabsMusicClient(api_key=settings.ELEVENLABS_API_KEY)

        # Parse genre and mood from prompt (simple parsing)
        genre = "ambient"
        mood = "calm"
        if "energetic" in bgm_prompt.lower() or "upbeat" in bgm_prompt.lower():
            mood = "energetic"
            genre = "upbeat"
        elif "mysterious" in bgm_prompt.lower():
            mood = "mysterious"
            genre = "cinematic"
        elif "happy" in bgm_prompt.lower():
            mood = "happy"
            genre = "upbeat"

        new_bgm_path = client.generate_music(
            genre=genre,
            mood=mood,
            duration_ms=30000,  # 30 seconds
            output_filename=str(audio_dir / "global_bgm.mp3")
        )

        # Update layout.json
        layout["global_bgm"]["audio_url"] = str(new_bgm_path)
        layout["global_bgm"]["prompt"] = bgm_prompt

        with open(layout_json_path, "wb") as f:
            f.write(orjson.dumps(layout, option=orjson.OPT_INDENT_2))

        logger.info(f"[{run_id}] Regenerated BGM")

        return {
            "status": "regenerated",
            "audio_url": f"/outputs/{run_id}/audio/{Path(new_bgm_path).name}"
        }

    except Exception as e:
        logger.error(f"[{run_id}] Failed to regenerate BGM: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to regenerate BGM: {str(e)}")


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
