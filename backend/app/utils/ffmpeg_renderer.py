"""
FFmpeg-based video renderer for Kurz AI Studio.

This module provides a 2-stage rendering pipeline:
1. Python (PIL/Pillow): Generate composite frames for each scene (title + subtitle + images)
2. FFmpeg: Compose frames into video + audio mixing

Performance benefits over MoviePy:
- 5-10x faster rendering
- Lower memory usage (no Python video objects in memory)
- More reliable for long videos
"""
import logging
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import numpy as np

logger = logging.getLogger(__name__)


class FFmpegRenderer:
    """FFmpeg-based video renderer with PIL frame generation."""

    def __init__(self, run_id: str, layout: Dict, output_dir: Path):
        """
        Initialize renderer.

        Args:
            run_id: Run identifier for logging
            layout: Layout JSON with scenes, images, audio, etc.
            output_dir: Output directory for frames and final video
        """
        self.run_id = run_id
        self.layout = layout
        self.output_dir = output_dir
        self.frames_dir = output_dir / "frames"
        self.frames_dir.mkdir(parents=True, exist_ok=True)

        # Video settings
        self.width = 1080
        self.height = 1920
        self.fps = layout.get("timeline", {}).get("fps", 30)

        # Layout config
        self.layout_config = layout.get("metadata", {}).get("layout_config", {})
        self.use_title_block = self.layout_config.get("use_title_block", True)
        self.title_bg_color = self._hex_to_rgb(self.layout_config.get("title_bg_color", "#323296"))
        self.title_font_size = self.layout_config.get("title_font_size", 100)
        self.subtitle_font_size = self.layout_config.get("subtitle_font_size", 80)

        # Font paths
        from app.utils.fonts import get_font_path
        title_font_id = self.layout_config.get("title_font", "AppleGothic")
        subtitle_font_id = self.layout_config.get("subtitle_font", "AppleGothic")
        self.title_font_path = get_font_path(title_font_id)
        self.subtitle_font_path = get_font_path(subtitle_font_id)

        # Mode
        self.mode = layout.get("metadata", {}).get("mode", "general")

        logger.info(f"[{run_id}] FFmpegRenderer initialized: {self.width}x{self.height} @ {self.fps}fps")

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _load_font(self, font_path: str, font_size: int) -> ImageFont.FreeTypeFont:
        """Load TrueType font."""
        try:
            return ImageFont.truetype(font_path, font_size)
        except Exception as e:
            logger.warning(f"[{self.run_id}] Failed to load font {font_path}: {e}, using default")
            return ImageFont.load_default()

    def _draw_text_with_stroke(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        position: Tuple[int, int],
        font: ImageFont.FreeTypeFont,
        fill_color: Tuple[int, int, int],
        stroke_color: Tuple[int, int, int],
        stroke_width: int = 3
    ):
        """Draw text with stroke (outline)."""
        x, y = position

        # Draw stroke
        for offset_x in range(-stroke_width, stroke_width + 1):
            for offset_y in range(-stroke_width, stroke_width + 1):
                if offset_x != 0 or offset_y != 0:
                    draw.text((x + offset_x, y + offset_y), text, font=font, fill=stroke_color)

        # Draw main text
        draw.text((x, y), text, font=font, fill=fill_color)

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Wrap text to fit within max_width."""
        lines = []
        words = text.split()
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            text_width = bbox[2] - bbox[0]

            if text_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def _create_title_block(
        self,
        img: Image.Image,
        title_text: str,
        title_font: ImageFont.FreeTypeFont
    ) -> int:
        """
        Draw title block at the top of the image.

        Args:
            img: PIL Image to draw on (modified in-place)
            title_text: Title text
            title_font: Font for title

        Returns:
            Height of title block in pixels
        """
        draw = ImageDraw.Draw(img)

        # Wrap title text
        max_title_width = int(self.width * 0.90)
        title_lines = self._wrap_text(title_text, title_font, max_title_width)

        # Calculate title block height
        line_height = int(self.title_font_size * 1.3)  # 1.3x for line spacing
        padding_top = 20
        padding_bottom = 20
        padding_left = 30

        title_text_height = len(title_lines) * line_height
        title_block_height = title_text_height + padding_top + padding_bottom

        # Draw title background
        draw.rectangle(
            [(0, 0), (self.width, title_block_height)],
            fill=self.title_bg_color
        )

        # Draw title text (center-aligned, multi-line)
        current_y = padding_top
        for line in title_lines:
            # Calculate centered x position for each line
            bbox = title_font.getbbox(line)
            text_width = bbox[2] - bbox[0]
            x_centered = (self.width - text_width) // 2

            self._draw_text_with_stroke(
                draw,
                line,
                (x_centered, current_y),
                title_font,
                fill_color=(255, 255, 255),
                stroke_color=(0, 0, 0),
                stroke_width=3
            )
            current_y += line_height

        logger.info(f"[{self.run_id}] Drew title block: {len(title_lines)} lines, height={title_block_height}px")

        return title_block_height

    def _create_subtitle(
        self,
        img: Image.Image,
        subtitle_text: str,
        subtitle_font: ImageFont.FreeTypeFont,
        y_position: int,
        text_color: Tuple[int, int, int],
        stroke_color: Tuple[int, int, int]
    ):
        """
        Draw subtitle at specified y position.

        Args:
            img: PIL Image to draw on (modified in-place)
            subtitle_text: Subtitle text
            subtitle_font: Font for subtitle
            y_position: Y position for subtitle
            text_color: Text fill color
            stroke_color: Text stroke color
        """
        draw = ImageDraw.Draw(img)

        # Wrap subtitle text
        max_subtitle_width = int(self.width * 0.90)
        subtitle_lines = self._wrap_text(subtitle_text, subtitle_font, max_subtitle_width)

        # Calculate line height
        line_height = int(self.subtitle_font_size * 1.3)

        # Center subtitle horizontally
        current_y = y_position
        for line in subtitle_lines:
            bbox = subtitle_font.getbbox(line)
            text_width = bbox[2] - bbox[0]
            x_centered = (self.width - text_width) // 2

            self._draw_text_with_stroke(
                draw,
                line,
                (x_centered, current_y),
                subtitle_font,
                fill_color=text_color,
                stroke_color=stroke_color,
                stroke_width=2
            )
            current_y += line_height

    def _composite_scene_frame(
        self,
        scene: Dict,
        title_text: str,
        title_font: ImageFont.FreeTypeFont,
        subtitle_font: ImageFont.FreeTypeFont
    ) -> Image.Image:
        """
        Create a single composite frame for a scene.

        Args:
            scene: Scene data from layout.json
            title_text: Project title
            title_font: Font for title
            subtitle_font: Font for subtitle

        Returns:
            PIL Image (RGBA)
        """
        # Create base image
        if self.mode == "general":
            bg_color = (255, 255, 255, 255)  # White
        else:
            bg_color = (20, 20, 40, 255)  # Dark

        img = Image.new('RGBA', (self.width, self.height), bg_color)

        # Layer images (sorted by z_index)
        sorted_slots = sorted(scene.get("images", []), key=lambda s: s.get("z_index", 1))
        scene_image_top_y = None  # Track 1:1 image position for subtitle placement

        for img_slot in sorted_slots:
            img_url = img_slot.get("image_url")
            if not img_url or not Path(img_url).exists():
                continue

            img_type = img_slot.get("type", "character")
            layer_img = Image.open(img_url)

            # Convert to RGBA if needed
            if layer_img.mode != 'RGBA':
                layer_img = layer_img.convert('RGBA')

            # Handle different image types
            if img_type == "background":
                # Background: resize to fill screen
                layer_img = layer_img.resize((self.width, self.height), Image.Resampling.LANCZOS)
                img.paste(layer_img, (0, 0), layer_img)
                logger.info(f"[{self.run_id}] Composited background image (full screen)")

            elif img_type == "scene":
                # Scene image: check aspect ratio
                aspect_ratio = img_slot.get("aspect_ratio", "9:16")

                if aspect_ratio == "1:1":
                    # General Mode: 1:1 square image, positioned near bottom
                    new_width = self.width
                    new_height = int(layer_img.height * (new_width / layer_img.width))
                    layer_img = layer_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # Position at 80% of screen height
                    y_position = int(self.height * 0.80 - new_height * 0.80)
                    scene_image_top_y = y_position

                    img.paste(layer_img, ((self.width - new_width) // 2, y_position), layer_img)
                    logger.info(f"[{self.run_id}] Composited 1:1 scene image at y={y_position}px")
                else:
                    # Story Mode: 9:16 image, fill screen
                    layer_img = layer_img.resize((self.width, self.height), Image.Resampling.LANCZOS)
                    img.paste(layer_img, (0, 0), layer_img)
                    logger.info(f"[{self.run_id}] Composited 9:16 scene image (full screen)")

            else:
                # Character: resize and position
                new_height = int(self.height * 0.7)
                new_width = int(layer_img.width * (new_height / layer_img.height))
                layer_img = layer_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Position based on x_pos
                if "x_pos" in img_slot:
                    x_pos = img_slot["x_pos"]  # 0.25, 0.5, 0.75
                    x_center = int(x_pos * self.width)
                    x_pixel = x_center - (new_width // 2)
                    y_pixel = self.height - new_height  # Bottom-aligned

                    img.paste(layer_img, (x_pixel, y_pixel), layer_img)
                    logger.info(f"[{self.run_id}] Composited character at x={x_pos:.2f}, bottom-aligned")
                else:
                    # Legacy center positioning
                    x_pixel = (self.width - new_width) // 2
                    y_pixel = (self.height - new_height) // 2
                    img.paste(layer_img, (x_pixel, y_pixel), layer_img)

        # Add title block
        title_height = 0
        if title_text and self.use_title_block:
            title_height = self._create_title_block(img, title_text, title_font)

        # Add subtitle
        for text_line in scene.get("texts", []):
            text_content = text_line.get("text", "").strip('"')
            if not text_content:
                continue

            # Determine text color based on mode
            if self.mode == "general":
                text_color = (0, 0, 0)  # Black text
                stroke_color = (255, 255, 255)  # White stroke
            else:
                text_color = (255, 255, 255)  # White text
                stroke_color = (0, 0, 0)  # Black stroke

            # Position subtitle between title and image
            if scene_image_top_y is not None:
                # General mode: center between title and image
                available_space = scene_image_top_y - title_height
                subtitle_y = int(title_height + available_space / 2 - self.subtitle_font_size)
            else:
                # Story mode: below title
                subtitle_y = title_height + 40

            self._create_subtitle(
                img,
                text_content,
                subtitle_font,
                subtitle_y,
                text_color,
                stroke_color
            )
            logger.info(f"[{self.run_id}] Drew subtitle at y={subtitle_y}px: {text_content[:30]}...")

        return img

    def render_frames(self) -> List[Tuple[Path, float]]:
        """
        Render all scene frames.

        Returns:
            List of (frame_path, duration_seconds) tuples
        """
        logger.info(f"[{self.run_id}] Starting frame generation...")

        # Load fonts
        title_font = self._load_font(self.title_font_path, self.title_font_size)
        subtitle_font = self._load_font(self.subtitle_font_path, self.subtitle_font_size)

        title_text = self.layout.get("title", "")
        scenes = self.layout.get("scenes", [])

        frame_info = []

        for i, scene in enumerate(scenes):
            scene_id = scene["scene_id"]
            duration_sec = scene["duration_ms"] / 1000.0

            logger.info(f"[{self.run_id}] Rendering frame for {scene_id} (duration={duration_sec}s)")

            # Create composite frame
            frame_img = self._composite_scene_frame(scene, title_text, title_font, subtitle_font)

            # Save frame
            frame_path = self.frames_dir / f"scene_{i:04d}.png"
            frame_img.save(frame_path, "PNG")

            frame_info.append((frame_path, duration_sec))
            logger.info(f"[{self.run_id}] Saved frame: {frame_path}")

        logger.info(f"[{self.run_id}] Frame generation complete: {len(frame_info)} frames")
        return frame_info

    def compose_video(
        self,
        frame_info: List[Tuple[Path, float]],
        output_path: Path
    ) -> Path:
        """
        Compose frames into video using FFmpeg with audio mixing.

        Args:
            frame_info: List of (frame_path, duration_seconds) tuples
            output_path: Output video path

        Returns:
            Path to final video
        """
        logger.info(f"[{self.run_id}] Starting FFmpeg video composition...")

        # Create concat demuxer file for frames with durations
        concat_file = self.output_dir / "concat.txt"
        with open(concat_file, "w") as f:
            for frame_path, duration in frame_info:
                # Use absolute path to avoid path resolution issues
                abs_frame_path = frame_path.resolve()
                f.write(f"file '{abs_frame_path}'\n")
                f.write(f"duration {duration}\n")
            # Repeat last frame to ensure it's included
            if frame_info:
                last_frame, _ = frame_info[-1]
                abs_last_frame = last_frame.resolve()
                f.write(f"file '{abs_last_frame}'\n")

        logger.info(f"[{self.run_id}] Created concat file: {concat_file}")

        # Build FFmpeg command (input section)
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
        ]

        # Collect audio files
        audio_files = []
        filter_complex_parts = []

        # Global BGM
        global_bgm = self.layout.get("global_bgm")
        if global_bgm and global_bgm.get("audio_url"):
            bgm_path = Path(global_bgm["audio_url"])
            if bgm_path.exists() and bgm_path.stat().st_size > 100:
                audio_files.append(("bgm", str(bgm_path), global_bgm.get("volume", 0.5)))

        # Voice audio with timing
        scene_start_time = 0.0
        for scene in self.layout.get("scenes", []):
            scene_duration = scene["duration_ms"] / 1000.0

            for text_line in scene.get("texts", []):
                audio_url = text_line.get("audio_url")
                if audio_url and Path(audio_url).exists() and Path(audio_url).stat().st_size > 100:
                    text_start_in_scene = text_line.get("start_ms", 0) / 1000.0
                    absolute_start = scene_start_time + text_start_in_scene
                    audio_files.append(("voice", str(audio_url), 1.0, absolute_start))

            scene_start_time += scene_duration

        # Calculate total video duration
        total_video_duration = scene_start_time

        # Add audio inputs and build filter_complex
        audio_idx = 1  # 0 is video
        audio_streams = []

        for audio_info in audio_files:
            if audio_info[0] == "bgm":
                _, audio_path, volume = audio_info
                cmd.extend(["-i", audio_path])

                # BGM is 30 seconds long - only loop if video is longer than 30s
                if total_video_duration > 30.0:
                    # Loop BGM and apply volume
                    filter_complex_parts.append(f"[{audio_idx}:a]aloop=loop=-1:size=2e9,volume={volume}[bgm]")
                else:
                    # No loop needed - just apply volume
                    filter_complex_parts.append(f"[{audio_idx}:a]volume={volume}[bgm]")

                audio_streams.append("[bgm]")
                audio_idx += 1
            else:
                _, audio_path, volume, start_time = audio_info
                cmd.extend(["-i", audio_path])
                # Delay voice to match timing and apply volume
                filter_complex_parts.append(f"[{audio_idx}:a]adelay={int(start_time * 1000)}|{int(start_time * 1000)},volume={volume}[v{audio_idx}]")
                audio_streams.append(f"[v{audio_idx}]")
                audio_idx += 1

        # Mix all audio streams and add output encoding options
        if audio_streams:
            num_streams = len(audio_streams)
            mix_inputs = "".join(audio_streams)
            # Use duration=longest to include all voice clips, then FFmpeg will trim to video length
            filter_complex_parts.append(f"{mix_inputs}amix=inputs={num_streams}:duration=longest[aout]")

            cmd.extend([
                "-filter_complex", ";".join(filter_complex_parts),
                "-map", "0:v",
                "-map", "[aout]",
                # Video encoding options (MUST come after -map)
                "-r", str(self.fps),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "medium",
                "-crf", "23",
                # Audio encoding options
                "-c:a", "aac",
                "-b:a", "192k",
                # CRITICAL: Trim audio to match video duration
                "-shortest"
            ])
        else:
            # No audio - video only
            cmd.extend([
                "-map", "0:v",
                # Video encoding options (MUST come after -map)
                "-r", str(self.fps),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "medium",
                "-crf", "23"
            ])

        cmd.append(str(output_path))

        logger.info(f"[{self.run_id}] FFmpeg command: {' '.join(cmd)}")

        # Run FFmpeg
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"[{self.run_id}] FFmpeg completed successfully")
            logger.debug(f"[{self.run_id}] FFmpeg output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"[{self.run_id}] FFmpeg failed: {e.stderr}")
            raise

        return output_path

    def render(self, output_path: Path) -> Path:
        """
        Full rendering pipeline: frames → video.

        Args:
            output_path: Output video path

        Returns:
            Path to final video
        """
        # Step 1: Render frames
        frame_info = self.render_frames()

        # Step 2: Compose video with FFmpeg
        final_video = self.compose_video(frame_info, output_path)

        logger.info(f"[{self.run_id}] Rendering complete: {final_video}")
        return final_video
