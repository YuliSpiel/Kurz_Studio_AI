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

        # Map characters to voice profiles
        char_voices = {}
        for char in layout.get("characters", []):
            char_id = char["char_id"]

            # Use explicit voice_id from spec if provided
            if spec.get("voice_id"):
                voice_profile = spec.get("voice_id")
            # Smart voice matching for Story Mode
            elif voices_config and characters_data:
                # Find character in characters.json
                char_data = next(
                    (c for c in characters_data.get("characters", []) if c["char_id"] == char_id),
                    None
                )
                if char_data:
                    gender = char_data.get("gender", "other")
                    role = char_data.get("role", "")
                    personality = char_data.get("personality", "")

                    # Select voice based on gender and personality/role
                    voice_list = voices_config.get("voices", {}).get(gender, [])
                    if voice_list:
                        # Smart matching: match personality keywords to voice descriptions
                        best_voice = voice_list[0]  # Default to first

                        # Keywords for voice matching
                        personality_lower = personality.lower()
                        role_lower = role.lower()

                        for voice in voice_list:
                            voice_desc = voice.get("description", "").lower()
                            voice_roles = [r.lower() for r in voice.get("recommended_roles", [])]

                            # Match based on personality keywords
                            if any(keyword in personality_lower for keyword in ["밝", "활발", "친밀", "따뜻"]):
                                if "밝" in voice_desc or "따뜻" in voice_desc or "친밀" in voice_desc:
                                    best_voice = voice
                                    break
                            elif any(keyword in personality_lower for keyword in ["전문", "냉철", "이성", "쿨"]):
                                if "쿨" in voice_desc or "세련" in voice_desc or "전문" in voice_desc:
                                    best_voice = voice
                                    break
                            elif any(keyword in personality_lower for keyword in ["느린", "묵직", "차분"]):
                                if "느린" in voice_desc or "묵직" in voice_desc:
                                    best_voice = voice
                                    break

                            # Match based on role
                            if role_lower and any(role_keyword in " ".join(voice_roles) for role_keyword in role_lower.split()):
                                best_voice = voice
                                break

                        voice_profile = best_voice["voice_id"]
                        logger.info(f"[{run_id}] Matched {char_id} ({gender}, {personality[:20]}...) to voice: {best_voice['name']}")
                    else:
                        voice_profile = char.get("voice_profile", "default")
                else:
                    voice_profile = char.get("voice_profile", "default")
            else:
                voice_profile = char.get("voice_profile", "default")

            char_voices[char_id] = voice_profile

        # Add narrator voice if needed
        if "narrator" not in char_voices and voices_config:
            # Use a neutral narrator voice (default to first female voice)
            female_voices = voices_config.get("voices", {}).get("female", [])
            if female_voices:
                char_voices["narrator"] = female_voices[0]["voice_id"]
                logger.info(f"[{run_id}] Using narrator voice: {female_voices[0]['name']}")
            else:
                char_voices["narrator"] = "default"

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

                # Update JSON
                text_line["audio_url"] = str(audio_path)

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
