"""
ElevenLabs Sound Effects API for music generation.
ElevenLabs provides sound effects and music generation capabilities.
"""
import logging
import httpx
from pathlib import Path
from typing import Optional

from app.providers.music.base import MusicProvider

logger = logging.getLogger(__name__)


class ElevenLabsMusicClient(MusicProvider):
    """ElevenLabs Sound Effects API for background music generation."""

    def __init__(self, api_key: str):
        """
        Initialize ElevenLabs Music client.

        Args:
            api_key: ElevenLabs API key
        """
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        logger.info("ElevenLabs Music client initialized")

    def generate_music(
        self,
        genre: str,
        mood: str,
        duration_ms: int,
        output_filename: str = "bgm.mp3"
    ) -> Path:
        """
        Generate background music using ElevenLabs Sound Effects API.

        Args:
            genre: Music genre (ambient, cinematic, upbeat, etc.)
            mood: Mood descriptor (calm, energetic, mysterious, etc.)
            duration_ms: Desired duration in milliseconds
            output_filename: Output file path

        Returns:
            Path to generated audio file
        """
        duration_sec = duration_ms / 1000

        # ElevenLabs Sound Effects API를 사용하여 음악 생성
        # 프롬프트 구성: 장르 + 무드 + 길이
        prompt = self._build_music_prompt(genre, mood, duration_sec)

        logger.info(f"ElevenLabs Music: Generating with prompt: {prompt}")

        try:
            # ElevenLabs Sound Effects API 호출
            url = f"{self.base_url}/sound-generation"

            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }

            payload = {
                "text": prompt,
                "duration_seconds": min(duration_sec, 30),  # ElevenLabs v2 최대 30초
                "prompt_influence": 0.3,  # 프롬프트 영향력 (0-1)
                "model_id": "eleven_text_to_sound_v2"  # v2 모델 사용
            }

            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                # 오디오 파일 저장
                output_path = Path(output_filename)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "wb") as f:
                    f.write(response.content)

                logger.info(f"ElevenLabs Music: Generated successfully -> {output_path}")
                return output_path

        except httpx.HTTPError as e:
            logger.error(f"ElevenLabs Music API error: {e}")

            # Fallback: 더미 파일 생성
            logger.warning("Falling back to stub mode (creating silent audio)")
            return self._create_stub_audio(output_filename, duration_ms)

    def _build_music_prompt(self, genre: str, mood: str, duration_sec: float) -> str:
        """
        음악 생성 프롬프트 구성.

        Args:
            genre: 장르
            mood: 무드
            duration_sec: 길이 (초)

        Returns:
            ElevenLabs Sound Effects API용 프롬프트
        """
        # 장르-무드 조합으로 자연스러운 음악 프롬프트 생성
        genre_map = {
            "ambient": "ambient atmospheric background music",
            "cinematic": "cinematic orchestral music",
            "upbeat": "upbeat energetic music",
            "lofi": "lofi chill music",
            "electronic": "electronic synthesizer music",
            "acoustic": "acoustic guitar music"
        }

        mood_map = {
            "calm": "calm and peaceful",
            "energetic": "energetic and lively",
            "mysterious": "mysterious and intriguing",
            "dreamy": "dreamy and ethereal",
            "happy": "happy and cheerful",
            "sad": "melancholic and emotional"
        }

        genre_desc = genre_map.get(genre.lower(), genre)
        mood_desc = mood_map.get(mood.lower(), mood)

        # ElevenLabs Sound Effects는 자연어 프롬프트 사용
        prompt = f"{mood_desc} {genre_desc}, instrumental, no vocals, looping"

        return prompt

    def _create_stub_audio(self, output_filename: str, duration_ms: int) -> Path:
        """
        Stub 오디오 파일 생성 (API 실패 시 폴백).

        Args:
            output_filename: 출력 파일명
            duration_ms: 길이 (밀리초)

        Returns:
            생성된 파일 경로
        """
        from pydub import AudioSegment
        from pydub.generators import Sine

        # 매우 낮은 주파수의 사인파 생성 (거의 무음)
        silent_tone = Sine(20).to_audio_segment(duration=duration_ms, volume=-60)

        output_path = Path(output_filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        silent_tone.export(output_path, format="mp3")

        logger.info(f"Stub audio created: {output_path}")
        return output_path
