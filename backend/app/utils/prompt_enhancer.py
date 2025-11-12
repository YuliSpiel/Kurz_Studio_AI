"""
Prompt Enhancement Module
Uses Gemini Flash to analyze and enrich user prompts for video generation.
"""
import logging
from typing import Dict, Any
import json

from app.providers.llm.gemini_llm_client import GeminiLLMClient
from app.config import settings

logger = logging.getLogger(__name__)


def enhance_prompt(original_prompt: str, mode: str = "general") -> Dict[str, Any]:
    """
    Analyze and enhance a user prompt for video generation.

    Args:
        original_prompt: Original user input prompt
        mode: Generation mode (general, story, ad)

    Returns:
        Dict containing:
        - enhanced_prompt: Enriched version of the prompt
        - suggested_title: Catchy video title (max 30 chars)
        - suggested_num_cuts: Optimal number of cuts (1-10)
        - suggested_art_style: Recommended art style
        - suggested_music_genre: Recommended music genre
        - suggested_num_characters: Recommended number of characters (1-2)
        - reasoning: Brief explanation of suggestions
    """
    logger.info(f"[ENHANCE] Analyzing prompt: '{original_prompt[:50]}...'")

    # Build enhancement prompt (concise to reduce tokens)
    system_prompt = f"""Analyze this video prompt and return JSON only. Be concise.

{{
  "enhanced_prompt": "detailed Korean description",
  "suggested_title": "catchy video title (max 30 chars)",
  "suggested_num_cuts": 1-10,
  "suggested_art_style": "style name",
  "suggested_music_genre": "genre",
  "suggested_num_characters": 1-2,
  "reasoning": "brief Korean explanation (max 2 sentences)"
}}"""

    user_prompt = f"Prompt: {original_prompt}\nMode: {mode}"

    try:
        # Initialize Gemini client
        if not settings.GEMINI_API_KEY:
            raise ValueError("No Gemini API key configured")

        client = GeminiLLMClient(api_key=settings.GEMINI_API_KEY)

        # Call Gemini Flash
        response_text = client.generate_text(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        logger.info(f"[ENHANCE] Raw LLM response: {response_text[:200]}...")

        # Parse JSON response
        # Clean potential markdown code blocks
        cleaned_response = response_text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()

        result = json.loads(cleaned_response)

        # Validate fields
        required_fields = [
            "enhanced_prompt",
            "suggested_title",
            "suggested_num_cuts",
            "suggested_art_style",
            "suggested_music_genre",
            "suggested_num_characters",
            "reasoning"
        ]

        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")

        # Validate ranges
        result["suggested_num_cuts"] = max(1, min(10, int(result["suggested_num_cuts"])))
        result["suggested_num_characters"] = max(1, min(2, int(result["suggested_num_characters"])))

        logger.info(f"[ENHANCE] Successfully enhanced prompt")
        logger.info(f"[ENHANCE] Suggested title: '{result['suggested_title']}', "
                   f"cuts: {result['suggested_num_cuts']}, "
                   f"characters: {result['suggested_num_characters']}, "
                   f"art_style: '{result['suggested_art_style']}'")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"[ENHANCE] Failed to parse JSON response: {e}")
        logger.error(f"[ENHANCE] Raw response was: {response_text}")
        raise ValueError(f"LLM returned invalid JSON: {e}")

    except Exception as e:
        logger.error(f"[ENHANCE] Failed to enhance prompt: {e}", exc_info=True)
        raise
