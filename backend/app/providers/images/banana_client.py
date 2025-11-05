"""
Banana image generation client.
Uses Banana.dev serverless GPU infrastructure for Stable Diffusion models.
"""
import logging
import httpx
import base64
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class BananaClient:
    """Banana image generation provider."""

    def __init__(self, api_key: str, model_key: str):
        """
        Initialize Banana client.

        Args:
            api_key: Banana API key
            model_key: Banana model key (specific to deployed model)
        """
        self.api_key = api_key
        self.model_key = model_key
        self.base_url = "https://api.banana.dev"
        logger.info(f"Banana client initialized with model: {model_key[:20]}...")

    def generate_image(
        self,
        prompt: str,
        seed: int = 42,
        width: int = 512,
        height: int = 768,
        num_inference_steps: int = 25,
        guidance_scale: float = 7.5,
        negative_prompt: Optional[str] = None,
        output_prefix: str = "banana_output",
        **kwargs
    ) -> Path:
        """
        Generate image using Banana API.

        Args:
            prompt: Text prompt for image generation
            seed: Random seed for reproducibility
            width: Image width (default: 512)
            height: Image height (default: 768 for 9:16 ratio)
            num_inference_steps: Number of denoising steps (default: 25)
            guidance_scale: Classifier-free guidance scale (default: 7.5)
            negative_prompt: Negative prompt (optional)
            output_prefix: Prefix for output filename
            **kwargs: Additional parameters (ignored)

        Returns:
            Path to generated image file
        """
        logger.info(f"Banana: Generating image with prompt: {prompt[:50]}...")

        # Default negative prompt for quality
        if not negative_prompt:
            negative_prompt = "ugly, blurry, low quality, distorted, deformed"

        # Prepare request payload
        payload = {
            "apiKey": self.api_key,
            "modelKey": self.model_key,
            "modelInputs": {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "seed": seed,
                "width": width,
                "height": height,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
            }
        }

        try:
            # Call Banana API
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/start/v4",
                    json=payload
                )
                response.raise_for_status()

                result = response.json()

                # Check for errors
                if "message" in result and result.get("message") != "success":
                    raise ValueError(f"Banana API error: {result.get('message')}")

                # Extract image from response
                # Banana typically returns base64 encoded image in modelOutputs
                model_outputs = result.get("modelOutputs", [])

                if not model_outputs:
                    raise ValueError("No output from Banana API")

                # Handle different response formats
                image_data = None
                if isinstance(model_outputs, list) and len(model_outputs) > 0:
                    image_data = model_outputs[0].get("image_base64")
                elif isinstance(model_outputs, dict):
                    image_data = model_outputs.get("image_base64") or model_outputs.get("image")

                if not image_data:
                    raise ValueError(f"No image data in response: {result}")

                # Decode base64 image
                try:
                    image_bytes = base64.b64decode(image_data)
                except Exception as e:
                    raise ValueError(f"Failed to decode image: {e}")

                # Save image
                output_dir = Path("backend/app/data/outputs/images")
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{output_prefix}.png"

                with open(output_path, "wb") as f:
                    f.write(image_bytes)

                logger.info(f"Banana: Image saved to {output_path}")
                return output_path

        except httpx.HTTPError as e:
            logger.error(f"Banana HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Banana generation error: {e}")
            raise

    def check_status(self) -> bool:
        """
        Check if Banana service is available.

        Returns:
            True if service is available
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                # Simple health check
                response = client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
