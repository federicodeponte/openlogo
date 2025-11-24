"""Unit tests for LogoRanker."""

import pytest
from fede_crawl4ai.processors.ranker import LogoRanker
from fede_crawl4ai.models import LogoResult


class TestLogoRanker:
    """Test LogoRanker functionality."""

    def test_filter_by_confidence(self):
        """Test filtering logos by confidence threshold."""
        ranker = LogoRanker(confidence_threshold=0.8)

        logos = [
            LogoResult(
                url="https://example.com/logo1.png",
                confidence=0.95,
                description="High confidence",
                page_url="https://example.com",
                image_hash="hash1",
            ),
            LogoResult(
                url="https://example.com/logo2.png",
                confidence=0.75,
                description="Below threshold",
                page_url="https://example.com",
                image_hash="hash2",
            ),
            LogoResult(
                url="https://example.com/logo3.png",
                confidence=0.85,
                description="Above threshold",
                page_url="https://example.com",
                image_hash="hash3",
            ),
        ]

        filtered = ranker.filter_by_confidence(logos)

        assert len(filtered) == 2
        assert all(logo.confidence >= 0.8 for logo in filtered)

    def test_rank_by_confidence(self):
        """Test ranking logos by confidence score."""
        ranker = LogoRanker()

        logos = [
            LogoResult(
                url="https://example.com/logo1.png",
                confidence=0.7,
                description="Low",
                page_url="https://example.com",
                image_hash="hash1",
            ),
            LogoResult(
                url="https://example.com/logo2.png",
                confidence=0.95,
                description="High",
                page_url="https://example.com",
                image_hash="hash2",
            ),
            LogoResult(
                url="https://example.com/logo3.png",
                confidence=0.85,
                description="Medium",
                page_url="https://example.com",
                image_hash="hash3",
            ),
        ]

        ranked = ranker.rank(logos)

        assert ranked[0].confidence == 0.95  # Highest first
        assert ranked[1].confidence == 0.85
        assert ranked[2].confidence == 0.7

    def test_rank_header_boost(self):
        """Test that header logos get boosted ranking."""
        ranker = LogoRanker()

        logos = [
            LogoResult(
                url="https://example.com/logo1.png",
                confidence=0.85,
                description="Main content",
                page_url="https://example.com",
                image_hash="hash1",
                is_header=False,
            ),
            LogoResult(
                url="https://example.com/logo2.png",
                confidence=0.8,
                description="Header logo",
                page_url="https://example.com",
                image_hash="hash2",
                is_header=True,
            ),
        ]

        ranked = ranker.rank(logos)

        # Header logo (0.8 + 0.2 boost = 1.0) should rank higher than main content (0.85)
        assert ranked[0].is_header is True
        assert ranked[0].rank_score == 1.0  # 0.8 + 0.2
        assert ranked[1].rank_score == 0.85

    def test_rank_empty_list(self):
        """Test ranking empty list returns empty list."""
        ranker = LogoRanker()
        assert ranker.rank([]) == []

    def test_get_top_logos(self):
        """Test getting top N logos."""
        ranker = LogoRanker()

        logos = [
            LogoResult(
                url=f"https://example.com/logo{i}.png",
                confidence=0.5 + (i * 0.05),  # Use 0.05 to stay within 0-1 range
                description=f"Logo {i}",
                page_url="https://example.com",
                image_hash=f"hash{i}",
            )
            for i in range(10)
        ]

        top_3 = ranker.get_top_logos(logos, n=3)

        assert len(top_3) == 3
        # Should be in descending order
        assert top_3[0].confidence > top_3[1].confidence
        assert top_3[1].confidence > top_3[2].confidence

    def test_filter_and_rank(self):
        """Test combined filter and rank operation."""
        ranker = LogoRanker(confidence_threshold=0.8)

        logos = [
            LogoResult(
                url="https://example.com/logo1.png",
                confidence=0.95,
                description="High",
                page_url="https://example.com",
                image_hash="hash1",
            ),
            LogoResult(
                url="https://example.com/logo2.png",
                confidence=0.75,
                description="Low - filtered out",
                page_url="https://example.com",
                image_hash="hash2",
            ),
            LogoResult(
                url="https://example.com/logo3.png",
                confidence=0.85,
                description="Medium",
                page_url="https://example.com",
                image_hash="hash3",
            ),
        ]

        result = ranker.filter_and_rank(logos)

        assert len(result) == 2  # One filtered out
        assert result[0].confidence == 0.95  # Highest first
        assert result[1].confidence == 0.85

    def test_rank_score_capped_at_1(self):
        """Test that rank scores are capped at 1.0."""
        ranker = LogoRanker()

        logo = LogoResult(
            url="https://example.com/logo.png",
            confidence=0.95,
            description="Header logo",
            page_url="https://example.com",
            image_hash="hash",
            is_header=True,
        )

        ranked = ranker.rank([logo])

        # 0.95 + 0.2 = 1.15, but should be capped at 1.0
        assert ranked[0].rank_score == 1.0

    def test_custom_threshold(self):
        """Test ranker with custom confidence threshold."""
        ranker = LogoRanker(confidence_threshold=0.9)

        logos = [
            LogoResult(
                url="https://example.com/logo1.png",
                confidence=0.95,
                description="Above threshold",
                page_url="https://example.com",
                image_hash="hash1",
            ),
            LogoResult(
                url="https://example.com/logo2.png",
                confidence=0.85,
                description="Below threshold",
                page_url="https://example.com",
                image_hash="hash2",
            ),
        ]

        filtered = ranker.filter_by_confidence(logos)

        assert len(filtered) == 1
        assert filtered[0].confidence == 0.95
