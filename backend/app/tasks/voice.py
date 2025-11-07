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

        # Load voices.json for smart voice matching
        voices_config = None
        voices_path = Path("voices.json")
        if voices_path.exists():
            with open(voices_path, "r", encoding="utf-8") as f:
                voices_config = json.load(f)
            logger.info(f"[{run_id}] Loaded voices.json for voice matching")

        # Load characters.json for gender/personality info
        characters_json_path = Path(json_path).parent / "characters.json"
        characters_data = {}
        if characters_json_path.exists():
            with open(characters_json_path, "r", encoding="utf-8") as f:
                characters_data = json.load(f)
            logger.info(f"[{run_id}] Loaded characters.json for voice matching")

        # Map characters to voice IDs
        char_voices = {}
        for char in layout.get("characters", []):
            char_id = char["char_id"]

            # Use explicit voice_id from spec if provided (for backwards compatibility)
            if spec.get("voice_id"):
                voice_id = spec.get("voice_id")
                logger.info(f"[{run_id}] Using voice_id from spec for {char_id}: {voice_id}")
            # Try to get voice_id from characters.json (primary method)
            elif characters_data:
                char_data = next(
                    (c for c in characters_data.get("characters", []) if c["char_id"] == char_id),
                    None
                )
                if char_data and "voice_id" in char_data:
                    voice_id = char_data["voice_id"]
                    logger.info(f"[{run_id}] Using voice_id from characters.json for {char_id}: {voice_id}")
                else:
                    # Fallback to layout.json voice_profile or default
                    voice_id = char.get("voice_profile", "default")
                    logger.warning(f"[{run_id}] No voice_id in characters.json for {char_id}, using fallback: {voice_id}")
            else:
                # Fallback if characters.json not available
                voice_id = char.get("voice_profile", "default")
                logger.warning(f"[{run_id}] No characters.json, using fallback voice for {char_id}: {voice_id}")

            char_voices[char_id] = voice_id

        # Add narration voice if needed (for general mode or story mode narration)
        if "narration" not in char_voices:
            # Try to get from characters.json first
            if characters_data:
                narration_char = next(
                    (c for c in characters_data.get("characters", []) if c["char_id"] == "narration"),
                    None
                )
                if narration_char and "voice_id" in narration_char:
                    char_voices["narration"] = narration_char["voice_id"]
                    logger.info(f"[{run_id}] Using narration voice from characters.json: {narration_char['voice_id']}")
                elif voices_config:
                    # Fallback: use default narrator voice from voices.json
                    female_voices = voices_config.get("voices", {}).get("female", [])
                    if female_voices:
                        # Look for Anna Kim (narration specialist) or use first
                        anna_voice = next((v for v in female_voices if "Anna" in v.get("name", "")), female_voices[0])
                        char_voices["narration"] = anna_voice["voice_id"]
                        logger.info(f"[{run_id}] Using fallback narration voice: {anna_voice['name']}")
                    else:
                        char_voices["narration"] = "default"
            elif voices_config:
                # No characters.json, use voices.json fallback
                female_voices = voices_config.get("voices", {}).get("female", [])
                if female_voices:
                    anna_voice = next((v for v in female_voices if "Anna" in v.get("name", "")), female_voices[0])
                    char_voices["narration"] = anna_voice["voice_id"]
                    logger.info(f"[{run_id}] Using fallback narration voice: {anna_voice['name']}")
                else:
                    char_voices["narration"] = "default"

        # Generate TTS for each text line
        for scene in layout.get("scenes", []):
            scene_id = scene["scene_id"]

            for text_line in scene.get("texts", []):
                line_id = text_line["line_id"]
                char_id = text_line["char_id"]
                text = text_line["text"]
                emotion = text_line.get("emotion", "neutral")

                # Remove quotes for TTS generation (quotes are only for display)
                tts_text = text.strip('"')

                voice_profile = char_voices.get(char_id, "default")

                logger.info(
                    f"[{run_id}] Generating TTS for {scene_id}/{line_id}: "
                    f"{tts_text[:30]}... (voice={voice_profile}, emotion={emotion})"
                )

                # Generate TTS in run_id folder
                audio_dir = Path(f"app/data/outputs/{run_id}/audio")
                audio_dir.mkdir(parents=True, exist_ok=True)

                audio_path = client.generate_speech(
                    text=tts_text,
                    voice_id=voice_profile,
                    emotion=emotion,
                    output_filename=str(audio_dir / f"{scene_id}_{line_id}.mp3")
                )

                # Measure audio duration
                try:
                    from moviepy.editor import AudioFileClip
                    with AudioFileClip(str(audio_path)) as audio_clip:
                        audio_duration_ms = int(audio_clip.duration * 1000)
                    logger.info(f"[{run_id}] Audio duration: {audio_duration_ms}ms for {scene_id}/{line_id}")
                except Exception as e:
                    logger.warning(f"[{run_id}] Failed to measure audio duration: {e}, using default")
                    audio_duration_ms = None

                # Update JSON
                text_line["audio_url"] = str(audio_path)

                voice_results.append({
                    "scene_id": scene_id,
                    "line_id": line_id,
                    "audio_url": str(audio_path),
                    "audio_duration_ms": audio_duration_ms
                })

                logger.info(f"[{run_id}] Generated: {audio_path}")

        # Update scene durations based on TTS lengths
        for scene in layout.get("scenes", []):
            scene_id = scene["scene_id"]

            # Find all audio durations for this scene
            scene_audio_durations = [
                result["audio_duration_ms"]
                for result in voice_results
                if result["scene_id"] == scene_id and result["audio_duration_ms"] is not None
            ]

            if scene_audio_durations:
                # Use the longest audio duration for the scene, plus 500ms padding
                max_audio_duration = max(scene_audio_durations)
                new_duration = max_audio_duration + 500  # Add 500ms padding
                old_duration = scene.get("duration_ms", 5000)

                scene["duration_ms"] = new_duration
                logger.info(f"[{run_id}] Updated {scene_id} duration: {old_duration}ms → {new_duration}ms (based on TTS: {max_audio_duration}ms)")
            else:
                logger.warning(f"[{run_id}] No audio duration found for {scene_id}, keeping original duration")

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
