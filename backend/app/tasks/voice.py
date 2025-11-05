"""
성우 Agent: TTS/voice generation.
"""
import logging
import json
from pathlib import Path

from app.celery_app import celery
from app.config import settings
from app.utils.progress import publish_progress

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="tasks.voice")
def voice_task(self, run_id: str, json_path: str, spec: dict):
    """
    Generate TTS voice for all dialogue lines.

    Args:
        run_id: Run identifier
        json_path: Path to JSON layout
        spec: RunSpec as dict

    Returns:
        Dict with generated voice paths
    """
    logger.info(f"[{run_id}] Voice: Starting TTS generation...")
    publish_progress(run_id, progress=0.55, log="성우: 음성 합성 시작...")

    # TEST: 3초 대기
    import time
    time.sleep(3)

    try:
        # Load JSON
        with open(json_path, "r", encoding="utf-8") as f:
            layout = json.load(f)

        # Get TTS provider
        if settings.TTS_PROVIDER == "elevenlabs" and settings.ELEVENLABS_API_KEY:
            from app.providers.tts.elevenlabs_client import ElevenLabsClient
            client = ElevenLabsClient(api_key=settings.ELEVENLABS_API_KEY)
        elif settings.TTS_PROVIDER == "playht" and settings.PLAYHT_API_KEY:
            from app.providers.tts.playht_client import PlayHTClient
            client = PlayHTClient(api_key=settings.PLAYHT_API_KEY)
        else:
            # Fallback to stub when no API key is available
            logger.warning(f"No API key for {settings.TTS_PROVIDER}, using stub TTS")
            from app.providers.tts.stub_client import StubTTSClient
            client = StubTTSClient()

        voice_results = []

        # Map characters to voice profiles
        char_voices = {}
        for char in layout.get("characters", []):
            char_id = char["char_id"]
            voice_profile = spec.get("voice_id") or char.get("voice_profile", "default")
            char_voices[char_id] = voice_profile

        # Generate TTS for each dialogue line
        for scene in layout.get("scenes", []):
            scene_id = scene["scene_id"]

            for dialogue in scene.get("dialogue", []):
                line_id = dialogue["line_id"]
                char_id = dialogue["char_id"]
                text = dialogue["text"]
                emotion = dialogue.get("emotion", "neutral")

                voice_profile = char_voices.get(char_id, "default")

                logger.info(
                    f"[{run_id}] Generating TTS for {scene_id}/{line_id}: "
                    f"{text[:30]}... (voice={voice_profile}, emotion={emotion})"
                )

                # Generate TTS in run_id folder
                audio_dir = Path(f"app/data/outputs/{run_id}/audio")
                audio_dir.mkdir(parents=True, exist_ok=True)

                audio_path = client.generate_speech(
                    text=text,
                    voice_id=voice_profile,
                    emotion=emotion,
                    output_filename=str(audio_dir / f"{scene_id}_{line_id}.mp3")
                )

                # Update JSON
                dialogue["audio_url"] = str(audio_path)

                voice_results.append({
                    "scene_id": scene_id,
                    "line_id": line_id,
                    "audio_url": str(audio_path)
                })

                logger.info(f"[{run_id}] Generated: {audio_path}")

        # Save updated JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(layout, f, indent=2, ensure_ascii=False)

        logger.info(f"[{run_id}] Voice: Completed {len(voice_results)} lines")
        publish_progress(run_id, progress=0.65, log=f"성우: 모든 음성 합성 완료 ({len(voice_results)}개)")

        # Update progress
        from app.main import runs
        if run_id in runs:
            runs[run_id]["artifacts"]["voice"] = voice_results

        return {
            "run_id": run_id,
            "agent": "voice",
            "voice": voice_results,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"[{run_id}] Voice task failed: {e}", exc_info=True)
        raise
