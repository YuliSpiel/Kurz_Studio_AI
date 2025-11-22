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


def _validate_image_with_vision(
    image_path: Path,
    expected_description: str,
    api_key: str,
    run_id: str = ""
) -> tuple[bool, str]:
    """
    Validate generated image matches expected description using Gemini Vision.

    Args:
        image_path: Path to the generated image
        expected_description: Expected character/scene description to validate against
        api_key: Gemini API key
        run_id: Run identifier for logging

    Returns:
        Tuple of (is_valid, reason)
    """
    import base64
    import httpx

    if not image_path or not Path(image_path).exists():
        return False, "Image file not found"

    try:
        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Determine mime type
        suffix = Path(image_path).suffix.lower()
        mime_type = "image/png" if suffix == ".png" else "image/jpeg"

        # Build validation prompt
        validation_prompt = f"""이미지를 분석하고 다음 설명과 일치하는지 확인해주세요.

예상 설명: {expected_description}

다음 항목을 확인해주세요:
1. 동물이 있다면: 종류(개, 고양이 등)와 색상(흰색, 갈색, 검정 등)이 설명과 일치하는가?
2. 사람이 있다면: 성별, 머리색, 외모 특징이 설명과 일치하는가?
3. 주요 색상이 설명과 일치하는가?

응답 형식 (JSON만 반환):
{{"match": true/false, "reason": "불일치 이유 또는 일치 확인", "detected": "실제 감지된 내용"}}

중요: 색상(특히 흰색 vs 갈색/황금색)과 동물 종류가 명확히 다르면 match=false로 판정하세요."""

        # Call Gemini Vision API
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "contents": [{
                "parts": [
                    {"text": validation_prompt},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": image_data
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 500
            }
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

        # Parse response
        candidates = result.get("candidates", [])
        if not candidates:
            logger.warning(f"[{run_id}] Vision validation: No response from API")
            return True, "Validation skipped - no API response"

        response_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        logger.info(f"[{run_id}] Vision validation response: {response_text[:200]}")

        # Parse JSON response
        import json
        import re

        # Extract JSON from response (may have markdown formatting)
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            validation_result = json.loads(json_match.group())
            is_match = validation_result.get("match", True)
            reason = validation_result.get("reason", "")
            detected = validation_result.get("detected", "")

            if not is_match:
                logger.warning(f"[{run_id}] Image validation FAILED: {reason} (detected: {detected})")
                return False, f"{reason} (감지됨: {detected})"
            else:
                logger.info(f"[{run_id}] Image validation PASSED: {reason}")
                return True, reason
        else:
            logger.warning(f"[{run_id}] Could not parse validation response, assuming valid")
            return True, "Could not parse response"

    except Exception as e:
        logger.warning(f"[{run_id}] Vision validation error: {e}")
        # On error, don't block - assume valid
        return True, f"Validation error: {e}"


def _is_stub_image(image_path: Path) -> bool:
    """
    Check if image is a stub (1x1 pixel or very small).

    Args:
        image_path: Path to image file

    Returns:
        True if stub image, False otherwise
    """
    if not image_path or not Path(image_path).exists():
        return True

    try:
        from PIL import Image
        img = Image.open(image_path)
        width, height = img.size

        # Stub images are 1x1 or very small (< 100x100)
        if width < 100 or height < 100:
            logger.warning(f"Detected stub image: {image_path} (size: {width}x{height})")
            return True

        return False
    except Exception as e:
        logger.error(f"Failed to check image size: {e}")
        return True  # Treat as stub if we can't check


def _cleanup_unused_images(run_id: str, layout: dict, json_path: str):
    """
    Delete image files that were generated but are not actually referenced in layout.json.
    This happens when an image was generated for a scene that should have reused a previous image.

    Args:
        run_id: Run identifier
        layout: Layout JSON data
        json_path: Path to layout.json
    """
    try:
        output_dir = Path(json_path).parent

        # Collect all image URLs referenced in layout.json
        referenced_images = set()
        for scene in layout.get("scenes", []):
            for img_slot in scene.get("images", []):
                image_url = img_slot.get("image_url", "")
                if image_url:
                    # Convert to absolute path for comparison
                    if not Path(image_url).is_absolute():
                        image_url = str(output_dir / image_url)
                    referenced_images.add(Path(image_url).resolve())

        logger.info(f"[{run_id}] Cleanup: Found {len(referenced_images)} referenced images in layout.json")

        # Find all generated image files in the output directory
        generated_images = []
        for pattern in ["scene_*.png", "scene_*.jpg", "bg_*.png", "bg_*.jpg", "char_*.png", "char_*.jpg"]:
            generated_images.extend(output_dir.glob(pattern))

        logger.info(f"[{run_id}] Cleanup: Found {len(generated_images)} generated image files")

        # Delete images that are not referenced
        deleted_count = 0
        for img_path in generated_images:
            img_path_resolved = img_path.resolve()
            if img_path_resolved not in referenced_images:
                try:
                    img_path.unlink()
                    logger.info(f"[{run_id}] Cleanup: Deleted unused image: {img_path.name}")
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"[{run_id}] Cleanup: Failed to delete {img_path.name}: {e}")

        if deleted_count > 0:
            logger.info(f"[{run_id}] Cleanup: Deleted {deleted_count} unused image(s)")
        else:
            logger.info(f"[{run_id}] Cleanup: No unused images to delete")

    except Exception as e:
        logger.warning(f"[{run_id}] Cleanup failed: {e}")
        # Don't raise - cleanup failure should not block the pipeline


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

    # Check stub mode
    stub_mode = spec.get("stub_image_mode", False)
    if stub_mode:
        logger.warning(f"[{run_id}] 🧪 STUB IMAGE MODE: Skipping Gemini API calls")
        publish_progress(run_id, progress=0.32, log="🧪 테스트: 더미 이미지 사용 (API 생략)")

    # TEST: 3초 대기
    import time
    time.sleep(3)

    try:
        # Load layout JSON
        with open(json_path, "r", encoding="utf-8") as f:
            layout = json.load(f)

        # Check if this is story mode (for background removal)
        is_story_mode = layout.get("mode") == "story"
        logger.info(f"[{run_id}] Mode: {layout.get('mode')}, Background removal: {'enabled' if is_story_mode else 'disabled'}")

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
        char_descriptions = {}  # char_id -> description mapping
        if characters_json_path.exists():
            with open(characters_json_path, "r", encoding="utf-8") as f:
                characters_data = json.load(f)
            logger.info(f"[{run_id}] Loaded characters.json for appearance data")

            # Build character description lookup
            for char in characters_data.get("characters", []):
                if char.get("appearance"):
                    char_descriptions[char["char_id"]] = char["appearance"]
            logger.info(f"[{run_id}] [TEMPLATE] Loaded {len(char_descriptions)} character descriptions for substitution")

        def substitute_char_variables(prompt: str) -> str:
            """Replace {char_1}, {char_2} etc. with actual character descriptions."""
            if not prompt or not char_descriptions:
                return prompt

            result = prompt
            for char_id, description in char_descriptions.items():
                placeholder = f"{{{char_id}}}"
                if placeholder in result:
                    result = result.replace(placeholder, description)
                    logger.debug(f"[{run_id}] [TEMPLATE] Substituted {placeholder} with description")
            return result

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
        cached_background = None  # Cache for background image reuse (Story Mode)
        cached_background_prompt = None  # Track the prompt of cached background
        cached_characters = {}  # Cache for character images: {prompt: image_path} (Story Mode)
        cached_scene = None  # Cache for scene image reuse (General Mode)
        cached_scene_prompt = None  # Track the prompt of cached scene

        # Generate images for each scene
        for scene in layout.get("scenes", []):
            scene_id = scene["scene_id"]
            logger.info(f"[{run_id}] Generating images for {scene_id}...")

            # Process each image slot
            for img_slot in scene.get("images", []):
                slot_id = img_slot["slot_id"]
                img_type = img_type = img_slot["type"]

                # CRITICAL: Check if image_url is already populated by json_converter
                # This happens when plot.json has image_prompt="" and json_converter copied the previous URL
                existing_image_url = img_slot.get("image_url", "")
                if existing_image_url:
                    logger.info(f"[{run_id}] Image already provided by json_converter for {scene_id}/{slot_id}: {existing_image_url}")
                    logger.info(f"[{run_id}] Skipping image generation - using pre-populated URL")
                    image_results.append({
                        "scene_id": scene_id,
                        "slot_id": slot_id,
                        "image_url": existing_image_url
                    })
                    # Update cache for next scenes
                    if img_type == "scene":
                        cached_scene = existing_image_url
                        cached_scene_prompt = img_slot.get("image_prompt", "")
                    elif img_type == "background":
                        cached_background = existing_image_url
                        cached_background_prompt = img_slot.get("image_prompt", "")
                    continue  # Skip generation entirely

                # Check for background reuse (Story Mode)
                if img_type == "background" and "image_prompt" in img_slot:
                    base_prompt = img_slot.get("image_prompt", "")

                    # Reuse background if:
                    # 1. Empty string (explicit reuse request), OR
                    # 2. Same prompt as previously cached background
                    if base_prompt == "" and cached_background:
                        logger.info(f"[{run_id}] Reusing previous background (empty prompt) for {scene_id}")
                        img_slot["image_url"] = cached_background
                        image_results.append({
                            "scene_id": scene_id,
                            "slot_id": slot_id,
                            "image_url": cached_background
                        })
                        continue  # Skip generation, use cached background
                    elif base_prompt and base_prompt == cached_background_prompt and cached_background:
                        logger.info(f"[{run_id}] Reusing previous background (same prompt) for {scene_id}: {base_prompt[:50]}...")
                        img_slot["image_url"] = cached_background
                        image_results.append({
                            "scene_id": scene_id,
                            "slot_id": slot_id,
                            "image_url": cached_background
                        })
                        continue  # Skip generation, use cached background

                # Check for scene reuse (General Mode)
                if img_type == "scene" and "image_prompt" in img_slot:
                    base_prompt = img_slot.get("image_prompt", "")

                    # Reuse scene if empty prompt (explicit reuse signal from plot.json)
                    if base_prompt == "" and cached_scene:
                        logger.info(f"[{run_id}] ✅ Reusing previous scene image (empty prompt) for {scene_id}")
                        img_slot["image_url"] = cached_scene
                        image_results.append({
                            "scene_id": scene_id,
                            "slot_id": slot_id,
                            "image_url": cached_scene
                        })
                        continue  # Skip generation, use cached scene

                # Check if image_prompt is provided (non-empty)
                if "image_prompt" in img_slot and img_slot["image_prompt"] != "":
                    # Use pre-computed prompt from json_converter
                    art_style = spec.get('art_style', '파스텔 수채화')
                    base_prompt = img_slot["image_prompt"]

                    # TEMPLATE SUBSTITUTION: Replace {char_1}, {char_2} etc.
                    base_prompt = substitute_char_variables(base_prompt)

                    if img_type == "background":
                        # Background image: use prompt directly with art style
                        # Add negative constraints to avoid text/speech bubbles
                        prompt = f"{art_style}, {base_prompt}, no text, no speech bubbles, no Korean text, no letters, no words"
                        seed = scene.get("bg_seed", settings.BG_SEED_BASE)
                    elif img_type == "scene":
                        # General Mode: unified scene image (characters + background)
                        # Add negative constraints to avoid text/speech bubbles
                        prompt = f"{art_style}, {base_prompt}, no text, no speech bubbles, no Korean text, no letters, no words"
                        seed = scene.get("bg_seed", settings.BG_SEED_BASE)
                        logger.info(f"[{run_id}] General mode scene image: {prompt[:50]}...")
                    else:
                        # Character image (Story Mode): prompt already includes appearance + expression + pose
                        # Add negative constraints to avoid text/speech bubbles
                        prompt = f"{art_style}, {base_prompt}, no text, no speech bubbles, no Korean text, no letters, no words"
                        char_id = img_slot.get("ref_id")
                        char = next(
                            (c for c in layout.get("characters", []) if c["char_id"] == char_id),
                            None
                        )
                        seed = char.get("seed", settings.BASE_CHAR_SEED) if char else settings.BASE_CHAR_SEED

                        # Check character image cache (Story Mode)
                        if img_type == "character" and base_prompt in cached_characters:
                            cached_path = cached_characters[base_prompt]
                            logger.info(f"[{run_id}] Reusing cached character image for {scene_id}/{slot_id}: {base_prompt[:50]}...")
                            img_slot["image_url"] = cached_path
                            image_results.append({
                                "scene_id": scene_id,
                                "slot_id": slot_id,
                                "image_url": cached_path
                            })
                            continue  # Skip generation, use cached character
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
                            # Add negative constraints to avoid text/speech bubbles
                            if expression != "none" and pose != "none":
                                prompt = f"{art_style}, {appearance}, {expression} expression, {pose} pose, no text, no speech bubbles, no Korean text, no letters, no words"
                            else:
                                prompt = f"{art_style}, {appearance}, no text, no speech bubbles, no Korean text, no letters, no words"

                            seed = char.get("seed", settings.BASE_CHAR_SEED)
                        else:
                            prompt = f"character, {spec.get('art_style', '')}, no text, no speech bubbles, no Korean text, no letters, no words"
                            seed = settings.BASE_CHAR_SEED
                    elif img_type == "background":
                        prompt = f"background scene, {spec.get('art_style', '')}, no text, no speech bubbles, no Korean text, no letters, no words"
                        seed = scene.get("bg_seed", settings.BG_SEED_BASE)
                    elif img_type == "scene":
                        # General mode: unified scene image (characters + background)
                        # Prompt already built in json_converter, just add art style
                        prompt = f"{spec.get('art_style', '파스텔 수채화')}, {base_prompt}, no text, no speech bubbles, no Korean text, no letters, no words"
                        seed = scene.get("bg_seed", settings.BG_SEED_BASE)
                    else:
                        prompt = f"prop, {spec.get('art_style', '')}, no text, no speech bubbles, no Korean text, no letters, no words"
                        seed = settings.BG_SEED_BASE + 100

                # Generate image
                logger.info(f"[{run_id}] Generating {scene_id}/{slot_id}: {prompt[:50]}...")

                # Set dimensions based on image type and aspect ratio
                if img_type == "character":
                    # Character: Generate larger image for cropping to standard size
                    # Generate at 1.5x size, then crop to 512x768 for consistency
                    gen_width, gen_height = 768, 1152
                    target_width, target_height = 512, 768
                elif img_type == "scene" and img_slot.get("aspect_ratio") == "1:1":
                    # General Mode: 1:1 square images for center placement
                    gen_width, gen_height = 1080, 1080
                    target_width, target_height = gen_width, gen_height
                else:
                    # Background or Scene (Story Mode): 9:16 ratio (full vertical screen)
                    gen_width, gen_height = 1080, 1920
                    target_width, target_height = gen_width, gen_height

                image_path = None

                if stub_mode:
                    # Stub mode: Skip API call, directly create stub image
                    logger.info(f"[{run_id}] 🧪 STUB MODE: Skipping image generation for {scene_id}/{slot_id}")
                    image_path = None  # Force stub image creation
                elif client:
                    # Generate image with validation and retry
                    max_validation_retries = 2
                    validation_enabled = provider == "gemini" and settings.GEMINI_API_KEY

                    # Get validation description (character appearance or image prompt)
                    validation_description = ""
                    if img_type == "character":
                        char_id = img_slot.get("ref_id")
                        if char_id and char_id in char_descriptions:
                            validation_description = char_descriptions[char_id]
                    elif "image_prompt" in img_slot:
                        validation_description = img_slot.get("image_prompt", "")

                    for attempt in range(max_validation_retries + 1):
                        try:
                            # Generate image based on provider type
                            # Vary seed on retry to get different result
                            current_seed = seed + (attempt * 100) if attempt > 0 else seed

                            if provider == "gemini":
                                image_path = client.generate_image(
                                    prompt=prompt,
                                    seed=current_seed,
                                    width=gen_width,
                                    height=gen_height,
                                    output_prefix=f"app/data/outputs/{run_id}/{scene_id}_{slot_id}"
                                )
                            elif provider == "comfyui":
                                image_path = client.generate_image(
                                    prompt=prompt,
                                    seed=current_seed,
                                    lora_name=settings.ART_STYLE_LORA,
                                    lora_strength=spec.get("lora_strength", 0.8),
                                    reference_images=spec.get("reference_images", []),
                                    output_prefix=f"app/data/outputs/{run_id}/{scene_id}_{slot_id}"
                                )

                            if not image_path:
                                logger.warning(f"[{run_id}] Image generation returned None for {scene_id}/{slot_id}")
                                continue

                            logger.info(f"[{run_id}] ✓ Image generated for {scene_id}/{slot_id}: {image_path} (attempt {attempt + 1})")

                            # Validate image with Gemini Vision (only for gemini provider and if description exists)
                            if validation_enabled and validation_description and attempt < max_validation_retries:
                                is_valid, reason = _validate_image_with_vision(
                                    image_path=Path(image_path),
                                    expected_description=validation_description,
                                    api_key=settings.GEMINI_API_KEY,
                                    run_id=run_id
                                )

                                if not is_valid:
                                    logger.warning(f"[{run_id}] 🔄 Image validation failed for {scene_id}/{slot_id}: {reason}")
                                    logger.info(f"[{run_id}] Retrying image generation (attempt {attempt + 2}/{max_validation_retries + 1})...")
                                    publish_progress(run_id, log=f"디자이너: 이미지 검증 실패, 재생성 중... ({scene_id})")
                                    continue  # Retry generation
                                else:
                                    logger.info(f"[{run_id}] ✅ Image validation passed for {scene_id}/{slot_id}")
                                    break  # Success - exit retry loop
                            else:
                                break  # No validation needed or last attempt - exit loop

                        except Exception as e:
                            logger.error(f"[{run_id}] Image generation failed for {scene_id}/{slot_id}: {e}")
                            if attempt < max_validation_retries:
                                continue
                            image_path = None
                            break

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
                    # Debug: Log conditions for background removal
                    logger.info(f"[{run_id}] [DEBUG] Checking rembg conditions: is_story_mode={is_story_mode}, img_type={img_type}, path_exists={Path(image_path).exists()}, image_path={image_path}")

                    # Crop character images to standard size for consistency
                    if img_type == "character" and Path(image_path).exists():
                        try:
                            from PIL import Image

                            logger.info(f"[{run_id}] Cropping character image to standard size: {image_path}")

                            img = Image.open(image_path)
                            img_width, img_height = img.size

                            # Target size: 512x768 (defined earlier)
                            # Crop from center, slightly biased to top (for face positioning)
                            left = (img_width - target_width) // 2
                            top = int((img_height - target_height) * 0.35)  # Start at 35% to keep face in upper portion
                            right = left + target_width
                            bottom = top + target_height

                            # Ensure crop dimensions are within image bounds
                            if right <= img_width and bottom <= img_height:
                                img_cropped = img.crop((left, top, right, bottom))
                                img_cropped.save(image_path)
                                logger.info(f"[{run_id}] Cropped to {target_width}x{target_height}: {image_path}")
                            else:
                                logger.warning(f"[{run_id}] Image too small to crop ({img_width}x{img_height}), keeping original")
                        except Exception as e:
                            logger.warning(f"[{run_id}] Image cropping failed: {e}, using original image")

                    # Apply background removal to character images (ONLY in Story Mode)
                    if is_story_mode and img_type == "character" and Path(image_path).exists():
                        try:
                            from rembg import remove
                            from PIL import Image

                            logger.info(f"[{run_id}] [Story Mode] Removing background from character image: {image_path}")

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

                # Cache background for reuse in next scenes
                if img_type == "background":
                    cached_background = str(image_path)
                    # Store the prompt used for this background
                    if "image_prompt" in img_slot:
                        cached_background_prompt = img_slot["image_prompt"]
                    logger.info(f"[{run_id}] Cached background for reuse: {cached_background}")

                # Cache character image for reuse (Story Mode)
                if img_type == "character" and "image_prompt" in img_slot:
                    char_prompt = img_slot["image_prompt"]
                    cached_characters[char_prompt] = str(image_path)
                    logger.info(f"[{run_id}] Cached character image for reuse: {char_prompt[:50]}...")

                # Cache scene image for reuse (General Mode)
                if img_type == "scene":
                    cached_scene = str(image_path)
                    # Store the prompt used for this scene
                    if "image_prompt" in img_slot:
                        cached_scene_prompt = img_slot["image_prompt"]
                    logger.info(f"[{run_id}] Cached scene image for reuse: {cached_scene}")

                logger.info(f"[{run_id}] Generated: {image_path}")

        # Save updated JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(layout, f, indent=2, ensure_ascii=False)

        logger.info(f"[{run_id}] Designer: Completed {len(image_results)} images")
        publish_progress(run_id, progress=0.4, log=f"디자이너: 모든 이미지 생성 완료 ({len(image_results)}개)")

        # Cleanup unused images (images that were generated but not referenced in layout.json)
        # DISABLED: Cleanup logic has path mismatch issues (generates in root, layout.json refs images/)
        # _cleanup_unused_images(run_id, layout, json_path)

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
