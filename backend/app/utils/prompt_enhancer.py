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
        - suggested_num_cuts: Optimal number of cuts (1-10)
        - suggested_art_style: Recommended art style
        - suggested_music_genre: Recommended music genre
        - suggested_num_characters: Recommended number of characters (1-2)
        - reasoning: Brief explanation of suggestions
    """
    logger.info(f"[ENHANCE] Analyzing prompt: '{original_prompt[:50]}...'")

    # Build enhancement prompt
    system_prompt = f"""당신은 숏폼 영상 제작 전문가입니다. 사용자가 입력한 프롬프트를 분석하여 최적의 영상 제작 파라미터를 제안해주세요.

모드: {mode}

분석 기준:
1. **프롬프트 풍부화**: 원본 프롬프트를 더 구체적이고 시각적으로 표현력있게 개선
2. **컷 수 (num_cuts)**: 내용의 복잡도와 분량에 따라 1-10개 사이로 제안
   - 간단한 메시지: 1-3컷
   - 일반적인 스토리: 3-5컷
   - 복잡한 이야기: 5-10컷
3. **화풍 (art_style)**: 프롬프트의 분위기와 주제에 맞는 화풍 제안
   - 예: "파스텔 수채화", "애니메이션 스타일", "사실적인 유화", "미니멀 일러스트", "다이나믹 만화풍"
4. **음악 장르 (music_genre)**: 영상의 분위기에 맞는 음악 제안
   - 예: "ambient", "cinematic", "upbeat", "emotional piano", "energetic electronic"
5. **등장인물 수 (num_characters)**: 스토리에 필요한 캐릭터 수 (1-2명)

응답 형식 (JSON):
{{
  "enhanced_prompt": "풍부화된 프롬프트 (한국어, 구체적이고 시각적인 표현)",
  "suggested_num_cuts": 3,
  "suggested_art_style": "파스텔 수채화",
  "suggested_music_genre": "ambient",
  "suggested_num_characters": 1,
  "reasoning": "제안 이유에 대한 간단한 설명 (1-2문장)"
}}

중요: 반드시 valid JSON만 반환하세요. 마크다운 코드 블록이나 추가 설명 없이 순수 JSON만 출력하세요."""

    user_prompt = f"원본 프롬프트: {original_prompt}"

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
            max_tokens=1000
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
        logger.info(f"[ENHANCE] Suggested cuts: {result['suggested_num_cuts']}, "
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
