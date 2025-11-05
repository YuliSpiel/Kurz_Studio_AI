"""
ComfyUI HTTP API client for image generation.
Supports Flux.1-dev + LoRA + OmniRef workflow.
"""
import logging
import json
import time
from pathlib import Path
from typing import List, Optional
import httpx

logger = logging.getLogger(__name__)


class ComfyUIClient:
    """Client for ComfyUI HTTP API."""

    def __init__(self, base_url: str = "http://localhost:8188"):
        """
        Initialize ComfyUI client.

        Args:
            base_url: ComfyUI server URL
        """
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=300.0)
        logger.info(f"ComfyUI client initialized: {self.base_url}")

    def upload_image(self, image_path: str) -> str:
        """
        Upload reference image to ComfyUI input folder.

        Args:
            image_path: Local path to image

        Returns:
            Uploaded filename
        """
        try:
            with open(image_path, "rb") as f:
                files = {"image": f}
                response = self.client.post(f"{self.base_url}/upload/image", files=files)
                response.raise_for_status()

            result = response.json()
            filename = result.get("name", Path(image_path).name)
            logger.info(f"Uploaded image: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to upload image: {e}")
            raise

    def load_workflow_template(self, template_path: str) -> dict:
        """
        Load workflow JSON template.

        Args:
            template_path: Path to workflow JSON

        Returns:
            Workflow dict
        """
        from pathlib import Path

        # Convert to Path object for easier handling
        path = Path(template_path)

        # If path is not absolute and doesn't exist, try adding backend/ prefix
        if not path.is_absolute() and not path.exists():
            # Try with backend/ prefix
            backend_path = Path("backend") / template_path
            if backend_path.exists():
                path = backend_path

        with open(path, "r") as f:
            return json.load(f)

    def substitute_workflow_params(
        self,
        workflow: dict,
        prompt: str,
        seed: int,
        lora_name: str = "",
        lora_strength: float = 0.8,
        reference_images: Optional[List[str]] = None
    ) -> dict:
        """
        Substitute parameters in workflow template.

        This is a simplified version. In production, you'd have a proper
        node ID mapping based on your actual workflow structure.

        Args:
            workflow: Workflow template dict
            prompt: Text prompt
            seed: Random seed
            lora_name: LoRA model name
            lora_strength: LoRA strength (0-1)
            reference_images: List of reference image filenames

        Returns:
            Modified workflow dict
        """
        # Deep copy to avoid mutation
        import copy
        workflow = copy.deepcopy(workflow)

        # Example substitution (adjust based on actual workflow structure)
        # This assumes specific node IDs - you'll need to customize this
        for node_id, node in workflow.items():
            if node.get("class_type") == "CLIPTextEncode":
                # Update prompt
                if "inputs" in node and "text" in node["inputs"]:
                    node["inputs"]["text"] = prompt

            elif node.get("class_type") == "KSampler":
                # Update seed
                if "inputs" in node:
                    node["inputs"]["seed"] = seed

            elif node.get("class_type") == "LoraLoader":
                # Update LoRA
                if "inputs" in node:
                    if lora_name:
                        node["inputs"]["lora_name"] = lora_name
                    node["inputs"]["strength_model"] = lora_strength

            elif node.get("class_type") == "LoadImage" and reference_images:
                # Update reference image
                if "inputs" in node and reference_images:
                    node["inputs"]["image"] = reference_images[0]

        return workflow

    def queue_prompt(self, workflow: dict) -> str:
        """
        Queue a workflow for execution.

        Args:
            workflow: Workflow dict

        Returns:
            Prompt ID
        """
        try:
            payload = {"prompt": workflow}
            response = self.client.post(f"{self.base_url}/prompt", json=payload)
            response.raise_for_status()

            result = response.json()
            prompt_id = result.get("prompt_id")
            logger.info(f"Queued prompt: {prompt_id}")
            return prompt_id

        except Exception as e:
            logger.error(f"Failed to queue prompt: {e}")
            raise

    def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> dict:
        """
        Wait for prompt to complete (polling-based).

        Args:
            prompt_id: Prompt ID
            timeout: Timeout in seconds

        Returns:
            Completion status dict
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = self.client.get(f"{self.base_url}/history/{prompt_id}")
                response.raise_for_status()

                history = response.json()

                if prompt_id in history:
                    logger.info(f"Prompt {prompt_id} completed")
                    return history[prompt_id]

                time.sleep(2)

            except Exception as e:
                logger.warning(f"Error polling history: {e}")
                time.sleep(2)

        raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout}s")

    def get_output_images(self, prompt_id: str, history: dict) -> List[str]:
        """
        Extract output image filenames from history.

        Args:
            prompt_id: Prompt ID
            history: History dict from wait_for_completion

        Returns:
            List of output image filenames
        """
        outputs = history.get("outputs", {})
        images = []

        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img in node_output["images"]:
                    filename = img.get("filename")
                    if filename:
                        images.append(filename)

        logger.info(f"Extracted {len(images)} output images for {prompt_id}")
        return images

    def download_image(self, filename: str, output_path: str):
        """
        Download generated image from ComfyUI output folder.

        Args:
            filename: Image filename
            output_path: Local save path
        """
        try:
            # ComfyUI output images are in /view?filename=...
            url = f"{self.base_url}/view?filename={filename}"
            response = self.client.get(url)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Downloaded image: {output_path}")

        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            raise

    def generate_image(
        self,
        prompt: str,
        seed: int,
        lora_name: str = "",
        lora_strength: float = 0.8,
        reference_images: Optional[List[str]] = None,
        output_prefix: str = "output",
        workflow_path: Optional[str] = None
    ) -> Path:
        """
        High-level image generation workflow.

        Args:
            prompt: Text prompt
            seed: Random seed
            lora_name: LoRA model name
            lora_strength: LoRA strength
            reference_images: Local paths to reference images
            output_prefix: Output filename prefix
            workflow_path: Custom workflow path (optional)

        Returns:
            Path to generated image
        """
        logger.info(f"Generating image: {prompt[:50]}... (seed={seed})")

        # Upload reference images if provided
        uploaded_refs = []
        if reference_images:
            for ref_path in reference_images:
                if Path(ref_path).exists():
                    uploaded_name = self.upload_image(ref_path)
                    uploaded_refs.append(uploaded_name)

        # Load and substitute workflow
        if not workflow_path:
            from app.config import settings
            workflow_path = settings.COMFY_WORKFLOW

        workflow = self.load_workflow_template(workflow_path)
        workflow = self.substitute_workflow_params(
            workflow=workflow,
            prompt=prompt,
            seed=seed,
            lora_name=lora_name,
            lora_strength=lora_strength,
            reference_images=uploaded_refs
        )

        # Queue and wait
        prompt_id = self.queue_prompt(workflow)
        history = self.wait_for_completion(prompt_id)

        # Get output images
        output_images = self.get_output_images(prompt_id, history)

        if not output_images:
            raise RuntimeError("No output images generated")

        # Download first image
        output_dir = Path("app/data/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_filename = f"{output_prefix}_{int(time.time())}.png"
        output_path = output_dir / output_filename

        self.download_image(output_images[0], str(output_path))

        return output_path
