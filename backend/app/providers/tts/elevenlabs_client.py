"""
ElevenLabs TTS client implementation.
"""
import logging
from pathlib import Path
import httpx

from app.providers.tts.base import TTSProvider

logger = logging.getLogger(__name__)


class ElevenLabsClient(TTSProvider):
    """ElevenLabs TTS provider."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str):
        """
        Initialize ElevenLabs client.

        Args:
            api_key: ElevenLabs API key
        """
        self.api_key = api_key
        self.client = httpx.Client(
            headers={"xi-api-key": api_key},
            timeout=60.0
        )
        logger.info("ElevenLabs client initialized")

    def generate_speech(
        self,
        text: str,
        voice_id: str = "default",
        emotion: str = "neutral",
        output_filename: str = "output.mp3"
    ) -> Path:
        """
        Generate speech using ElevenLabs.

        Args:
            text: Text to synthesize
            voice_id: Voice ID (use "default" for first available)
            emotion: Not directly supported, affects stability/similarity
            output_filename: Output filename

        Returns:
            Path to generated audio file
        """
        logger.info(f"Generating speech with ElevenLabs: {text[:50]}...")

        try:
            # If voice_id is "default", use yuna (Korean voice)
            if voice_id == "default" or voice_id == "yuna":
                voice_id = "xi3rF0t7dg7uN2M0WUhr"  # yuna (Korean voice)

            # API endpoint
            url = f"{self.BASE_URL}/text-to-speech/{voice_id}"

            # Request payload - use multilingual model for Korean support
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }

            # Adjust voice settings based on emotion (simple heuristic)
            if emotion in ["happy", "excited"]:
                payload["voice_settings"]["stability"] = 0.3
            elif emotion in ["sad", "calm"]:
                payload["voice_settings"]["stability"] = 0.7

            response = self.client.post(url, json=payload)
            response.raise_for_status()

            # Save audio
            # If output_filename is an absolute path or contains directories, use it directly
            output_path = Path(output_filename)

            # If it's just a filename (no directory), put it in default output directory
            if not output_path.parent or output_path.parent == Path('.'):
                output_dir = Path("app/data/outputs")
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / output_filename
            else:
                # Create parent directories if they don't exist
                output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Speech generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}")
            # Fallback: create silent audio or raise
            raise

    def list_voices(self) -> list:
        """List available voices."""
        try:
            response = self.client.get(f"{self.BASE_URL}/voices")
            response.raise_for_status()
            voices = response.json().get("voices", [])
            return voices
        except Exception as e:
            logger.error(f"Failed to list voices: {e}")
            return []
