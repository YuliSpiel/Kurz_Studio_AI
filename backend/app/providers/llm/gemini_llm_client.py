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
    ) -> str:
        """
        Generate text using Gemini model.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text as string

        Raises:
            Exception: If API call fails
        """
        try:
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
            logger.debug(f"[GEMINI] Prompt length: {len(combined_prompt)} chars")

            # Generate content
            response = self.model.generate_content(
                combined_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )

            # Extract text from response
            if not response.candidates:
                raise ValueError("No candidates in response")

            result_text = response.text

            logger.info(f"[GEMINI] Generated {len(result_text)} characters")

            return result_text

        except Exception as e:
            logger.error(f"[GEMINI] Error generating text: {e}", exc_info=True)
            raise
