"""Unit tests for OpenAIAnalyzer."""

import pytest
from unittest.mock import AsyncMock, patch
from fede_crawl4ai.analyzers.openai_analyzer import OpenAIAnalyzer
from fede_crawl4ai.models import LogoResult


class TestOpenAIAnalyzer:
    """Test OpenAIAnalyzer implementation."""

    @pytest.mark.asyncio
    async def test_analyze_success(self):
        """Test successful logo analysis."""
        analyzer = OpenAIAnalyzer(api_key="test_key")

        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "Confidence Score: 0.95\nDescription: Red and white company logo"
                    }
                }
            ]
        }

        with patch.object(
            analyzer, "_call_api", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await analyzer.analyze(
                image_base64="fake_base64_data",
                image_url="https://example.com/logo.png",
                page_url="https://example.com",
            )

            assert result is not None
            assert isinstance(result, LogoResult)
            assert result.confidence == 0.95
            assert "Red and white company logo" in result.description
            assert result.url == "https://example.com/logo.png"

    @pytest.mark.asyncio
    async def test_analyze_api_error(self):
        """Test handling of API errors."""
        analyzer = OpenAIAnalyzer(api_key="test_key")

        with patch.object(analyzer, "_call_api", new_callable=AsyncMock, return_value=None):
            result = await analyzer.analyze(
                image_base64="fake_base64_data",
                image_url="https://example.com/logo.png",
                page_url="https://example.com",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_analyze_null_response(self):
        """Test handling of 'null' response (no logo detected)."""
        analyzer = OpenAIAnalyzer(api_key="test_key")

        mock_response = {"choices": [{"message": {"content": "null"}}]}

        with patch.object(
            analyzer, "_call_api", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await analyzer.analyze(
                image_base64="fake_base64_data",
                image_url="https://example.com/not-logo.png",
                page_url="https://example.com",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_analyze_invalid_response_structure(self):
        """Test handling of invalid API response structure."""
        analyzer = OpenAIAnalyzer(api_key="test_key")

        mock_response = {"choices": []}  # Empty choices

        with patch.object(
            analyzer, "_call_api", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await analyzer.analyze(
                image_base64="fake_base64_data",
                image_url="https://example.com/logo.png",
                page_url="https://example.com",
            )

            assert result is None
