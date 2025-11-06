"""
디자이너 Agent: Image generation via ComfyUI.
"""
import logging
import json
from pathlib import Path

from app.celery_app import celery
from app.config import settings
from app.utils.progress import publish_progress

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="tasks.designer")
def designer_task(self, run_id: str, json_path: str, spec: dict):
    """
    Generate images for all scenes using ComfyUI.

    Args:
        run_id: Run identifier
        json_path: Path to JSON layout
        spec: RunSpec as dict

    Returns:
        Dict with generated image paths
    """
    logger.info(f"[{run_id}] Designer: Starting image generation...")
    publish_progress(run_id, progress=0.3, log="디자이너: 이미지 생성 시작...")

    # TEST: 3초 대기
    import time
    time.sleep(3)

    try:
        # Load layout JSON
        with open(json_path, "r", encoding="utf-8") as f:
            layout = json.load(f)

        # Load plot.json for expression/pose info
        plot_json_path = Path(json_path).parent / "plot.json"
        plot_data = {}
        if plot_json_path.exists():
            with open(plot_json_path, "r", encoding="utf-8") as f:
                plot_data = json.load(f)
            logger.info(f"[{run_id}] Loaded plot.json for expression/pose data")

        # Load characters.json for appearance info
        characters_json_path = Path(json_path).parent / "characters.json"
        characters_data = {}
        if characters_json_path.exists():
            with open(characters_json_path, "r", encoding="utf-8") as f:
                characters_data = json.load(f)
            logger.info(f"[{run_id}] Loaded characters.json for appearance data")

        # Get image provider
        client = None
        provider = settings.IMAGE_PROVIDER

        if provider == "gemini":
            # Gemini (Nano Banana) provider
            if settings.GEMINI_API_KEY:
                try:
                    from app.providers.images.gemini_image_client import GeminiImageClient
                    client = GeminiImageClient(api_key=settings.GEMINI_API_KEY)
                    logger.info(f"[{run_id}] Using Gemini (Nano Banana) image provider")
                except Exception as e:
                    logger.warning(f"Gemini not available: {e}, using stub images")
                    client = None
            else:
                logger.warning("GEMINI_API_KEY not set, using stub")

        elif provider == "comfyui":
            # ComfyUI provider
            try:
                from app.providers.images.comfyui_client import ComfyUIClient
                client = ComfyUIClient(base_url=settings.COMFY_URL)
                # Test connection
                import httpx
                response = httpx.get(f"{settings.COMFY_URL}/system_stats", timeout=2.0)
                response.raise_for_status()
                logger.info(f"[{run_id}] Using ComfyUI image provider")
            except Exception as e:
                logger.warning(f"ComfyUI not available: {e}, using stub images")
                client = None

        if not client:
            logger.warning("Using stub image generation (no provider available)")
            # Use stub - create placeholder images

        image_results = []

        # Generate images for each scene
        for scene in layout.get("scenes", []):
            scene_id = scene["scene_id"]
            logger.info(f"[{run_id}] Generating images for {scene_id}...")

            # Process each image slot
            for img_slot in scene.get("images", []):
                slot_id = img_slot["slot_id"]
                img_type = img_type = img_slot["type"]

                # Check if image_prompt is pre-computed (Story Mode)
                if "image_prompt" in img_slot and img_slot["image_prompt"]:
                    # Use pre-computed prompt from json_converter
                    art_style = spec.get('art_style', '파스텔 수채화')
                    base_prompt = img_slot["image_prompt"]

                    if img_type == "background":
                        # Background image: use prompt directly with art style
                        prompt = f"{art_style}, {base_prompt}"
                        seed = scene.get("bg_seed", settings.BG_SEED_BASE)
                    else:
                        # Character image: prompt already includes appearance + expression + pose
                        prompt = f"{art_style}, {base_prompt}"
                        char_id = img_slot.get("ref_id")
                        char = next(
                            (c for c in layout.get("characters", []) if c["char_id"] == char_id),
                            None
                        )
                        seed = char.get("seed", settings.BASE_CHAR_SEED) if char else settings.BASE_CHAR_SEED
                else:
                    # Legacy mode: Build prompt from scratch
                    if img_type == "character":
                        # Get character info
                        char_id = img_slot.get("ref_id")
                        char = next(
                            (c for c in layout.get("characters", []) if c["char_id"] == char_id),
                            None
                        )
                        if char:
                            art_style = spec.get('art_style', '파스텔 수채화')

                            # Get appearance from characters.json
                            appearance = char['persona']  # fallback
                            if characters_data:
                                char_data = next(
                                    (c for c in characters_data.get("characters", []) if c["char_id"] == char_id),
                                    None
                                )
                                if char_data:
                                    appearance = char_data.get("appearance", char['persona'])

                            # Get expression/pose from plot.json for this scene
                            expression = "neutral"
                            pose = "standing"
                            if plot_data:
                                scene_data = next(
                                    (s for s in plot_data.get("scenes", []) if s["scene_id"] == scene_id),
                                    None
                                )
                                if scene_data and scene_data.get("char_id") == char_id:
                                    expression = scene_data.get("expression", "neutral")
                                    pose = scene_data.get("pose", "standing")

                            # Build prompt: art_style + appearance + expression + pose
                            if expression != "none" and pose != "none":
                                prompt = f"{art_style}, {appearance}, {expression} expression, {pose} pose"
                            else:
                                prompt = f"{art_style}, {appearance}"

                            seed = char.get("seed", settings.BASE_CHAR_SEED)
                        else:
                            prompt = f"character, {spec.get('art_style', '')}"
                            seed = settings.BASE_CHAR_SEED
                    elif img_type == "background":
                        prompt = f"background scene, {spec.get('art_style', '')}"
                        seed = scene.get("bg_seed", settings.BG_SEED_BASE)
                    else:
                        prompt = f"prop, {spec.get('art_style', '')}"
                        seed = settings.BG_SEED_BASE + 100

                # Generate image
                logger.info(f"[{run_id}] Generating {scene_id}/{slot_id}: {prompt[:50]}...")

                image_path = None
                if client:
                    try:
                        # Generate image based on provider type
                        if provider == "gemini":
                            image_path = client.generate_image(
                                prompt=prompt,
                                seed=seed,
                                width=512,
                                height=768,  # 9:16 ratio
                                output_prefix=f"app/data/outputs/{run_id}/{scene_id}_{slot_id}"
                            )
                        elif provider == "comfyui":
                            image_path = client.generate_image(
                                prompt=prompt,
                                seed=seed,
                                lora_name=settings.ART_STYLE_LORA,
                                lora_strength=spec.get("lora_strength", 0.8),
                                reference_images=spec.get("reference_images", []),
                                output_prefix=f"app/data/outputs/{run_id}/{scene_id}_{slot_id}"
                            )
                    except Exception as e:
                        logger.error(f"[{run_id}] Image generation failed for {scene_id}/{slot_id}: {e}")
                        logger.warning(f"[{run_id}] Falling back to stub image")
                        image_path = None

                if not image_path:
                    # Create stub image (1x1 pixel PNG)
                    import base64
                    stub_png = base64.b64decode(
                        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                    )
                    stub_dir = Path(f"app/data/outputs/{run_id}/images")
                    stub_dir.mkdir(parents=True, exist_ok=True)
                    image_path = stub_dir / f"{scene_id}_{slot_id}.png"
                    with open(image_path, "wb") as f:
                        f.write(stub_png)
                    logger.info(f"[{run_id}] Created stub image: {image_path}")
                    publish_progress(run_id, log=f"디자이너: stub 이미지 생성 - {scene_id}_{slot_id}")
                else:
                    # Apply background removal to character images (not background)
                    if img_type == "character" and Path(image_path).exists():
                        try:
                            from rembg import remove
                            from PIL import Image

                            logger.info(f"[{run_id}] Removing background from character image: {image_path}")

                            # Load image
                            input_image = Image.open(image_path)

                            # Remove background
                            output_image = remove(input_image)

                            # Save as PNG with alpha
                            output_path = Path(image_path).with_suffix('.png')
                            output_image.save(output_path, 'PNG')

                            image_path = output_path
                            logger.info(f"[{run_id}] Background removed: {image_path}")
                            publish_progress(run_id, log=f"디자이너: 배경 제거 완료 - {scene_id}_{slot_id}")
                        except Exception as e:
                            logger.warning(f"[{run_id}] Background removal failed: {e}, using original image")

                # Update JSON with image path
                img_slot["image_url"] = str(image_path)
                image_results.append({
                    "scene_id": scene_id,
                    "slot_id": slot_id,
                    "image_url": str(image_path)
                })

                logger.info(f"[{run_id}] Generated: {image_path}")

        # Save updated JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(layout, f, indent=2, ensure_ascii=False)

        logger.info(f"[{run_id}] Designer: Completed {len(image_results)} images")
        publish_progress(run_id, progress=0.4, log=f"디자이너: 모든 이미지 생성 완료 ({len(image_results)}개)")

        # Update progress
        from app.main import runs
        if run_id in runs:
            runs[run_id]["progress"] = 0.5
            runs[run_id]["artifacts"]["images"] = image_results

        return {
            "run_id": run_id,
            "agent": "designer",
            "images": image_results,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"[{run_id}] Designer task failed: {e}", exc_info=True)
        raise
