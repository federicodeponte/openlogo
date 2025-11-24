"""Data models for crawl4logo."""

from datetime import datetime
from typing import Dict
from pydantic import BaseModel, Field


class LogoResult(BaseModel):
    """Result of logo detection analysis."""

    url: str = Field(..., description="Image URL")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    description: str = Field(..., description="Logo description from AI analysis")
    page_url: str = Field(..., description="Source page URL where logo was found")
    image_hash: str = Field(..., description="MD5 hash of image content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Analysis timestamp")
    is_header: bool = Field(
        default=False, description="Whether logo was found in header/nav element"
    )
    rank_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Ranking score")
    detection_scores: Dict[str, Dict[str, float]] = Field(
        default_factory=dict, description="Additional detection scores (backward compatibility)"
    )
