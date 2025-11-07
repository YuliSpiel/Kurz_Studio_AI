"""
JSON layout schema for final shorts composition.
Defines the structure for timeline, scenes, characters, and assets.
"""
from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class Character(BaseModel):
    """Character definition."""
    char_id: str = Field(description="예: char_1, char_2")
    name: str = Field(description="캐릭터 이름")
    persona: str = Field(description="성격/설정")
    voice_profile: str = Field(description="음성 프로필 ID or 설명")
    seed: int = Field(description="고정 seed for consistency")


class ImageSlot(BaseModel):
    """Image slot positioning in scene."""
    slot_id: str = Field(description="Slot identifier (e.g., 'left', 'center', 'right', 'char_1_slot', 'background', 'scene')")
    type: Literal["character", "background", "prop", "scene"] = Field(
        description="Image type: character (Story Mode), background (Story Mode), scene (General Mode), or prop"
    )
    ref_id: Optional[str] = Field(None, description="char_id or asset ID")
    image_url: str = Field(description="생성된 이미지 경로")
    z_index: int = Field(default=0, description="레이어 순서")
    position: Optional[str] = Field(None, description="Position label (left, center, right) for character slots")
    x_pos: Optional[float] = Field(None, description="Normalized x position (0.0-1.0) for horizontal placement")
    image_prompt: Optional[str] = Field(None, description="Image generation prompt (for designer task)")
    aspect_ratio: Optional[str] = Field(None, description="Aspect ratio (1:1 for general mode, 2:3 for characters, 9:16 for backgrounds)")
    background: Optional[str] = Field(None, description="Background color for image generation (white for general mode)")


class TextLine(BaseModel):
    """Text line (dialogue or narration) with timing and display info."""
    line_id: str
    char_id: str
    text: str
    text_type: Literal["dialogue", "narration"] = Field(description="대사 또는 해설 구분")
    emotion: str = Field(default="neutral", description="감정 (예: neutral, happy, sad)")
    position: Literal["top"] = Field(default="top", description="자막 위치 (항상 상단)")
    audio_url: str = Field(default="", description="TTS 음성 파일 경로")
    start_ms: int
    duration_ms: int


class SFX(BaseModel):
    """Sound effect definition."""
    sfx_id: str
    tags: List[str] = Field(description="무드 태그 (예: ['soft_chime', 'emotional'])")
    audio_url: str = Field(description="SFX 파일 경로")
    start_ms: int
    volume: float = Field(default=0.5, ge=0.0, le=1.0)


# Backward compatibility aliases (deprecated)
Subtitle = TextLine  # Deprecated: use TextLine instead
DialogueLine = TextLine  # Deprecated: use TextLine instead


class BGM(BaseModel):
    """Background music definition."""
    bgm_id: str
    genre: str
    mood: str
    audio_url: str = Field(description="BGM 파일 경로")
    start_ms: int
    duration_ms: int
    volume: float = Field(default=0.3, ge=0.0, le=1.0)


class Scene(BaseModel):
    """Scene definition with all components."""
    scene_id: str
    sequence: int = Field(description="씬 순서")
    duration_ms: int

    # Visual
    images: List[ImageSlot] = Field(description="이미지 슬롯 배치")

    # Text (통합: 대사 + 해설)
    texts: List[TextLine] = Field(default_factory=list, description="대사/해설 텍스트 (text_type으로 구분)")

    # Audio
    bgm: Optional[BGM] = None
    sfx: List[SFX] = Field(default_factory=list)

    # Scene settings
    bg_seed: int = Field(description="배경 seed")
    transition: str = Field(default="fade", description="전환 효과")

    # Backward compatibility (deprecated, will be removed)
    @property
    def dialogue(self) -> List[TextLine]:
        """Deprecated: use texts instead."""
        return [t for t in self.texts if t.text_type == "dialogue"]

    @property
    def subtitles(self) -> List[TextLine]:
        """Deprecated: use texts instead."""
        return self.texts


class Timeline(BaseModel):
    """Overall timeline metadata."""
    total_duration_ms: int
    aspect_ratio: str = Field(default="9:16")
    fps: int = Field(default=30)
    resolution: str = Field(default="1080x1920")


class ShortsJSON(BaseModel):
    """Complete JSON schema for shorts composition."""

    project_id: str
    title: str
    mode: Literal["general", "story", "ad"]

    timeline: Timeline
    characters: List[Character]
    scenes: List[Scene]

    # Global assets
    global_bgm: Optional[BGM] = Field(None, description="전체 배경음악 (씬별 BGM 우선)")

    metadata: dict = Field(
        default_factory=dict,
        description="추가 메타데이터 (생성 모델, 파라미터 등)"
    )
