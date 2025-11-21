"""
Pydantic models for run specifications and status.
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, List, Any


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

    narrative_tone: Optional[str] = Field(
        default=None,
        description="서술 말투 (예: 격식형, 서술형, 친근한반말, 진지한나레이션, 감정강조, 코믹풍자)"
    )

    plot_structure: Optional[str] = Field(
        default=None,
        description="플롯 구조 (예: 기승전결, 고구마사이다, 3막구조, 비교형, 반전형, 정보나열, 감정곡선, 질문형, 루프형)"
    )

    video_title: Optional[str] = Field(
        default=None,
        description="사용자 지정 영상 제목"
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

    # Layout customization
    layout_config: Optional[Dict] = Field(
        default=None,
        description="레이아웃 커스터마이징 설정 (title_bg_color, title_font, title_font_size, subtitle_font, subtitle_font_size)"
    )

    # Test mode flags
    stub_image_mode: bool = Field(
        default=False,
        description="테스트 모드: 이미지 생성 API 호출 생략 (더미 이미지 사용)"
    )

    stub_music_mode: bool = Field(
        default=False,
        description="테스트 모드: 음악 생성 API 호출 생략 (더미 음원 사용)"
    )

    stub_tts_mode: bool = Field(
        default=False,
        description="테스트 모드: TTS API 호출 생략 (더미 음성 사용)"
    )

    # Plot review mode
    review_mode: bool = Field(
        default=False,
        description="검수 모드: 플롯 생성 후 사용자 검수 단계 추가"
    )


class RunStatus(BaseModel):
    """Run status and progress information."""

    run_id: str
    state: str  # RunState enum value
    progress: float = Field(ge=0.0, le=1.0)

    artifacts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Generated artifacts (csv_path, json_path, video_url, qa_result, etc.)"
    )

    logs: List[str] = Field(
        default_factory=list,
        description="Progress logs"
    )
