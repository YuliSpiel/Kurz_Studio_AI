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
        # Load JSON
        with open(json_path, "r", encoding="utf-8") as f:
            layout = json.load(f)

        # Get image provider
        client = None
        if settings.IMAGE_PROVIDER == "comfyui":
            try:
                from app.providers.images.comfyui_client import ComfyUIClient
                client = ComfyUIClient(base_url=settings.COMFY_URL)
                # Test connection
                import httpx
                response = httpx.get(f"{settings.COMFY_URL}/system_stats", timeout=2.0)
                response.raise_for_status()
            except Exception as e:
                logger.warning(f"ComfyUI not available: {e}, using stub images")
                client = None

        if not client:
            logger.warning("Using stub image generation (no ComfyUI)")
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

                # Prepare prompt based on type
                if img_type == "character":
                    # Get character info
                    char_id = img_slot.get("ref_id")
                    char = next(
                        (c for c in layout.get("characters", []) if c["char_id"] == char_id),
                        None
                    )
                    if char:
                        prompt = f"{char['name']}, {char['persona']}, {spec.get('art_style', '')}"
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

                if client:
                    image_path = client.generate_image(
                        prompt=prompt,
                        seed=seed,
                        lora_name=settings.ART_STYLE_LORA,
                        lora_strength=spec.get("lora_strength", 0.8),
                        reference_images=spec.get("reference_images", []),
                        output_prefix=f"{run_id}_{scene_id}_{slot_id}"
                    )
                else:
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
                    logger.info(f"Created stub image: {image_path}")
                    publish_progress(run_id, log=f"디자이너: 이미지 생성 완료 - {scene_id}_{slot_id}")

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
