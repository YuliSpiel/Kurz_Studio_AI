"""
작곡가 Agent: Music/BGM generation.
"""
import logging
import json
from pathlib import Path

from app.celery_app import celery
from app.config import settings
from app.utils.progress import publish_progress

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="tasks.composer")
def composer_task(self, run_id: str, json_path: str, spec: dict):
    """
    Generate background music and SFX.

    Args:
        run_id: Run identifier
        json_path: Path to JSON layout
        spec: RunSpec as dict

    Returns:
        Dict with generated audio paths
    """
    logger.info(f"[{run_id}] Composer: Starting music generation...")
    publish_progress(run_id, progress=0.45, log="작곡가: 배경음악 생성 시작...")

    # TEST: 3초 대기
    import time
    time.sleep(3)

    try:
        # Load JSON
        with open(json_path, "r", encoding="utf-8") as f:
            layout = json.load(f)

        # Get music provider
        if settings.MUSIC_PROVIDER == "mubert":
            from app.providers.music.mubert_client import MubertClient
            client = MubertClient(api_key=settings.MUBERT_API_KEY)
        elif settings.MUSIC_PROVIDER == "udio":
            from app.providers.music.udio_stub import UdioClient
            client = UdioClient(api_key=settings.UDIO_API_KEY)
        elif settings.MUSIC_PROVIDER == "suno":
            from app.providers.music.suno_stub import SunoClient
            client = SunoClient()
        else:
            raise ValueError(f"Unsupported music provider: {settings.MUSIC_PROVIDER}")

        audio_results = []

        # Generate global BGM if needed
        total_duration_ms = layout.get("timeline", {}).get("total_duration_ms", 30000)
        music_genre = spec.get("music_genre", "ambient")

        logger.info(f"[{run_id}] Generating global BGM: {music_genre}, {total_duration_ms}ms")

        # Generate music in run_id folder
        audio_dir = Path(f"app/data/outputs/{run_id}/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)

        bgm_path = client.generate_music(
            genre=music_genre,
            mood="cinematic",
            duration_ms=total_duration_ms,
            output_filename=str(audio_dir / "global_bgm.mp3")
        )

        # Update JSON
        if "global_bgm" not in layout or layout["global_bgm"] is None:
            layout["global_bgm"] = {
                "bgm_id": "global_bgm",
                "genre": music_genre,
                "mood": "cinematic",
                "audio_url": str(bgm_path),
                "start_ms": 0,
                "duration_ms": total_duration_ms,
                "volume": 0.3
            }
        else:
            layout["global_bgm"]["audio_url"] = str(bgm_path)

        publish_progress(run_id, progress=0.5, log=f"작곡가: 배경음악 생성 완료 - {bgm_path}")

        audio_results.append({
            "type": "bgm",
            "id": "global_bgm",
            "path": str(bgm_path)
        })

        logger.info(f"[{run_id}] BGM generated: {bgm_path}")

        # Generate SFX for scenes (placeholder)
        for scene in layout.get("scenes", []):
            for sfx in scene.get("sfx", []):
                # For now, use placeholder SFX
                sfx_path = Path("app/data/samples/placeholder_sfx.mp3")
                sfx["audio_url"] = str(sfx_path)

        # Save updated JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(layout, f, indent=2, ensure_ascii=False)

        logger.info(f"[{run_id}] Composer: Completed")

        # Update progress
        from app.main import runs
        if run_id in runs:
            runs[run_id]["artifacts"]["audio"] = audio_results

        return {
            "run_id": run_id,
            "agent": "composer",
            "audio": audio_results,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"[{run_id}] Composer task failed: {e}", exc_info=True)
        raise
