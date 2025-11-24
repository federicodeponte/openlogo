"""Unit tests for data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError
from fede_crawl4ai.models import LogoResult


class TestLogoResult:
    """Test LogoResult data model."""

    def test_logo_result_creation_with_required_fields(self):
        """Test creating LogoResult with only required fields."""
        result = LogoResult(
            url="https://example.com/logo.png",
            confidence=0.95,
            description="Company logo with blue text",
            page_url="https://example.com",
            image_hash="abc123def456",
        )

        assert result.url == "https://example.com/logo.png"
        assert result.confidence == 0.95
        assert result.description == "Company logo with blue text"
        assert result.page_url == "https://example.com"
        assert result.image_hash == "abc123def456"
        assert isinstance(result.timestamp, datetime)
        assert result.is_header is False
        assert result.rank_score == 0.0
        assert result.detection_scores == {}

    def test_logo_result_creation_with_all_fields(self):
        """Test creating LogoResult with all fields."""
        timestamp = datetime.now()
        scores = {"header": {"score": 0.9}, "position": {"score": 0.8}}

        result = LogoResult(
            url="https://example.com/logo.png",
            confidence=0.95,
            description="Company logo",
            page_url="https://example.com",
            image_hash="abc123",
            timestamp=timestamp,
            is_header=True,
            rank_score=0.98,
            detection_scores=scores,
        )

        assert result.timestamp == timestamp
        assert result.is_header is True
        assert result.rank_score == 0.98
        assert result.detection_scores == scores

    def test_confidence_must_be_between_0_and_1(self):
        """Test that confidence score is validated to be between 0 and 1."""
        # Valid confidence scores
        LogoResult(
            url="https://example.com/logo.png",
            confidence=0.0,
            description="Low confidence",
            page_url="https://example.com",
            image_hash="abc123",
        )

        LogoResult(
            url="https://example.com/logo.png",
            confidence=1.0,
            description="High confidence",
            page_url="https://example.com",
            image_hash="abc123",
        )

        # Invalid confidence scores
        with pytest.raises(ValidationError):
            LogoResult(
                url="https://example.com/logo.png",
                confidence=-0.1,
                description="Negative confidence",
                page_url="https://example.com",
                image_hash="abc123",
            )

        with pytest.raises(ValidationError):
            LogoResult(
                url="https://example.com/logo.png",
                confidence=1.5,
                description="Too high confidence",
                page_url="https://example.com",
                image_hash="abc123",
            )

    def test_rank_score_must_be_between_0_and_1(self):
        """Test that rank_score is validated to be between 0 and 1."""
        # Valid rank scores
        LogoResult(
            url="https://example.com/logo.png",
            confidence=0.9,
            description="Logo",
            page_url="https://example.com",
            image_hash="abc123",
            rank_score=0.0,
        )

        LogoResult(
            url="https://example.com/logo.png",
            confidence=0.9,
            description="Logo",
            page_url="https://example.com",
            image_hash="abc123",
            rank_score=1.0,
        )

        # Invalid rank scores
        with pytest.raises(ValidationError):
            LogoResult(
                url="https://example.com/logo.png",
                confidence=0.9,
                description="Logo",
                page_url="https://example.com",
                image_hash="abc123",
                rank_score=-0.1,
            )

        with pytest.raises(ValidationError):
            LogoResult(
                url="https://example.com/logo.png",
                confidence=0.9,
                description="Logo",
                page_url="https://example.com",
                image_hash="abc123",
                rank_score=1.1,
            )

    def test_required_fields_cannot_be_none(self):
        """Test that required fields raise ValidationError when None."""
        with pytest.raises(ValidationError):
            LogoResult(
                url=None,
                confidence=0.9,
                description="Logo",
                page_url="https://example.com",
                image_hash="abc123",
            )

        with pytest.raises(ValidationError):
            LogoResult(
                url="https://example.com/logo.png",
                confidence=None,
                description="Logo",
                page_url="https://example.com",
                image_hash="abc123",
            )

    def test_default_timestamp_is_set(self):
        """Test that timestamp defaults to current time."""
        before = datetime.now()
        result = LogoResult(
            url="https://example.com/logo.png",
            confidence=0.9,
            description="Logo",
            page_url="https://example.com",
            image_hash="abc123",
        )
        after = datetime.now()

        assert before <= result.timestamp <= after
