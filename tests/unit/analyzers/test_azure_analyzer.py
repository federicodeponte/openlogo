"""Unit tests for AzureOpenAIAnalyzer."""

import pytest
from unittest.mock import AsyncMock, patch
from fede_crawl4ai.analyzers.azure_analyzer import AzureOpenAIAnalyzer
from fede_crawl4ai.models import LogoResult


class TestAzureOpenAIAnalyzer:
    """Test AzureOpenAIAnalyzer implementation."""

    @pytest.mark.asyncio
    async def test_analyze_success(self):
        """Test successful logo analysis with Azure."""
        analyzer = AzureOpenAIAnalyzer(
            api_key="test_key",
            endpoint="https://test.openai.azure.com",
            deployment="gpt-4o-mini",
        )

        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "Confidence Score: 0.93\nDescription: Blue tech company logo"
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
            assert result.confidence == 0.93
            assert "Blue tech company logo" in result.description

    @pytest.mark.asyncio
    async def test_analyze_with_custom_deployment(self):
        """Test analysis with custom deployment name."""
        analyzer = AzureOpenAIAnalyzer(
            api_key="test_key",
            endpoint="https://test.openai.azure.com",
            deployment="custom-gpt-4",
            api_version="2024-03-01",
        )

        assert analyzer.deployment == "custom-gpt-4"
        assert analyzer.api_version == "2024-03-01"
        assert analyzer.endpoint == "https://test.openai.azure.com"

    @pytest.mark.asyncio
    async def test_analyze_api_error(self):
        """Test handling of Azure API errors."""
        analyzer = AzureOpenAIAnalyzer(api_key="test_key", endpoint="https://test.openai.azure.com")

        with patch.object(analyzer, "_call_api", new_callable=AsyncMock, return_value=None):
            result = await analyzer.analyze(
                image_base64="fake_base64_data",
                image_url="https://example.com/logo.png",
                page_url="https://example.com",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_analyze_null_response(self):
        """Test handling of 'null' response from Azure."""
        analyzer = AzureOpenAIAnalyzer(api_key="test_key", endpoint="https://test.openai.azure.com")

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
