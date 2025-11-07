"""
Pydantic models for run specifications and status.
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, List


class CharacterInput(BaseModel):
    """Character information for Story Mode."""
    name: str
    gender: Literal["male", "female", "other"]
    role: str
    personality: str
    appearance: str
    reference_image: Optional[str] = None


class RunSpec(BaseModel):
    """Input specification for a shorts generation run."""

    mode: Literal["general", "story", "ad"] = Field(
        description="Generation mode: general (일반), story (스토리텔링), or ad (광고)"
    )

    prompt: str = Field(
        description="줄글 요청 (예: '우주를 여행하는 고양이 이야기')"
    )

    num_characters: int = Field(
        default=1,
        ge=1,
        le=3,
        description="등장인물 수 (1-3, Story Mode에서는 최대 3명)"
    )

    num_cuts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="컷(씬) 수 (1~10)"
    )

    art_style: str = Field(
        default="파스텔 수채화",
        description="화풍 (예: 파스텔 수채화, 애니메이션, 사실적)"
    )

    music_genre: str = Field(
        default="ambient",
        description="음악 장르 (예: ambient, cinematic, upbeat)"
    )

    reference_images: Optional[List[str]] = Field(
        default=None,
        description="업로드된 참조 이미지 파일명 리스트"
    )

    # Advanced options
    lora_strength: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="LoRA 강도 (0.0~1.0)"
    )

    voice_id: Optional[str] = Field(
        default=None,
        description="TTS 음성 ID (선택적)"
    )

    # Story Mode specific fields
    characters: Optional[List[CharacterInput]] = Field(
        default=None,
        description="캐릭터 정보 리스트 (Story Mode에서 사용)"
    )


class RunStatus(BaseModel):
    """Run status and progress information."""

    run_id: str
    state: str  # RunState enum value
    progress: float = Field(ge=0.0, le=1.0)

    artifacts: Dict[str, str] = Field(
        default_factory=dict,
        description="Generated artifacts (csv_path, json_path, video_url, etc.)"
    )

    logs: List[str] = Field(
        default_factory=list,
        description="Progress logs"
    )
