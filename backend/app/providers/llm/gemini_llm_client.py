"""
Gemini LLM Client for text generation using Google's Generative AI.
"""
import logging
from typing import List, Dict, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiLLMClient:
    """
    Client for interacting with Google's Gemini models (gemini-2.5-flash).
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initialize the Gemini LLM client.

        Args:
            api_key: Google AI API key
            model_name: Model identifier (default: gemini-2.5-flash)
        """
        if not api_key:
            raise ValueError("Gemini API key is required")

        self.api_key = api_key
        self.model_name = model_name

        # Configure genai
        genai.configure(api_key=self.api_key)

        # Initialize model
        self.model = genai.GenerativeModel(self.model_name)

        logger.info(f"Initialized GeminiLLMClient with model: {self.model_name}")

    def generate_text(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        max_retries: int = 3,
        json_mode: bool = False
    ) -> str:
        """
        Generate text using Gemini model with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            max_retries: Maximum number of retry attempts

        Returns:
            Generated text as string

        Raises:
            Exception: If API call fails after all retries
        """
        import time

        # Combine system and user messages
        # Gemini doesn't have explicit system role, so we prepend system message to user prompt
        combined_prompt = ""

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                combined_prompt += f"{content}\n\n"
            elif role == "user":
                combined_prompt += f"{content}"

        logger.info(f"[GEMINI] Generating text with temperature={temperature}, max_tokens={max_tokens}")
        logger.info(f"[GEMINI] Prompt length: {len(combined_prompt)} chars")
        logger.info(f"[GEMINI] Prompt preview (first 500 chars): {combined_prompt[:500]}...")

        # Generate content with safety settings
        from google.generativeai.types import HarmCategory, HarmBlockThreshold

        safety_settings = [
            {
                "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": HarmBlockThreshold.BLOCK_NONE,
            },
        ]

        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(f"[GEMINI] Attempt {attempt + 1}/{max_retries}")

                # Build generation config
                gen_config_params = {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
                if json_mode:
                    gen_config_params["response_mime_type"] = "application/json"

                response = self.model.generate_content(
                    combined_prompt,
                    generation_config=genai.types.GenerationConfig(**gen_config_params),
                    safety_settings=safety_settings,
                )

                # Extract text from response
                if not response.candidates:
                    error_msg = "No candidates in response"
                    logger.warning(f"[GEMINI] {error_msg}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    raise ValueError(error_msg)

                # Check for blocked responses
                candidate = response.candidates[0]
                finish_reason = candidate.finish_reason

                logger.debug(f"[GEMINI] Finish reason: {finish_reason} ({finish_reason.name if hasattr(finish_reason, 'name') else 'unknown'})")
                logger.debug(f"[GEMINI] Safety ratings: {candidate.safety_ratings}")

                # finish_reason enum: STOP (success), MAX_TOKENS (hit limit), SAFETY (blocked), RECITATION, OTHER
                # Allow STOP and MAX_TOKENS - both provide usable content
                # Note: finish_reason can be int or Enum depending on API version
                finish_reason_value = finish_reason.value if hasattr(finish_reason, 'value') else finish_reason
                if finish_reason_value not in [1, 2]:  # 1=STOP, 2=MAX_TOKENS
                    error_msg = (
                        f"Response blocked with finish_reason={finish_reason} ({finish_reason.name if hasattr(finish_reason, 'name') else 'unknown'}). "
                        f"Safety ratings: {candidate.safety_ratings}"
                    )
                    logger.warning(f"[GEMINI] {error_msg}")

                    # If safety-blocked, retry with adjusted temperature
                    if attempt < max_retries - 1:
                        temperature = max(0.3, temperature - 0.2)  # Lower temperature
                        logger.info(f"[GEMINI] Retrying with lower temperature: {temperature}")
                        time.sleep(2 ** attempt)
                        continue
                    raise ValueError(error_msg)

                # Try to extract text - handle cases where parts might be empty
                try:
                    result_text = response.text
                except ValueError as e:
                    # response.text raises ValueError if no valid parts
                    # Try to extract from parts directly
                    if candidate.content and candidate.content.parts:
                        result_text = "".join([p.text for p in candidate.content.parts if hasattr(p, 'text')])
                    else:
                        error_msg = f"No text content in response: {e}"
                        logger.warning(f"[GEMINI] {error_msg}")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        raise ValueError(error_msg)

                # For JSON mode, accept shorter responses since valid JSON can be compact
                min_length = 10 if json_mode else 50
                if not result_text or len(result_text) < min_length:
                    error_msg = f"Generated text too short ({len(result_text)} chars, min: {min_length})"
                    logger.warning(f"[GEMINI] {error_msg}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise ValueError(error_msg)

                logger.info(f"[GEMINI] ✅ Generated {len(result_text)} characters successfully")
                return result_text

            except Exception as e:
                last_error = e
                error_str = str(e)
                logger.error(f"[GEMINI] Attempt {attempt + 1} failed: {e}")

                # Check for rate limit (429) error - need longer wait
                is_rate_limit = "429" in error_str or "quota" in error_str.lower() or "exhausted" in error_str.lower()

                if attempt < max_retries - 1:
                    if is_rate_limit:
                        # For rate limit, wait longer (10s, 20s, 40s)
                        wait_time = 10 * (2 ** attempt)
                        logger.warning(f"[GEMINI] Rate limit detected, waiting {wait_time}s before retry...")
                    else:
                        wait_time = 2 ** attempt
                        logger.info(f"[GEMINI] Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    # Final attempt failed - provide user-friendly error for rate limit
                    if is_rate_limit:
                        raise ValueError("API 요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요.")
                    logger.error(f"[GEMINI] All {max_retries} attempts failed")
                    raise last_error
