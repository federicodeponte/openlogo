"""Unit tests for BaseOpenAIAnalyzer."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fede_crawl4ai.analyzers.base import BaseOpenAIAnalyzer
from fede_crawl4ai.models import LogoResult


class TestBaseOpenAIAnalyzer:
    """Test BaseOpenAIAnalyzer shared logic."""

    def test_build_messages(self):
        """Test message building for OpenAI API."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")
        messages = analyzer._build_messages("base64_image_data")

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "logo detection assistant" in messages[0]["content"].lower()
        assert messages[1]["role"] == "user"
        assert len(messages[1]["content"]) == 2
        assert messages[1]["content"][0]["type"] == "text"
        assert messages[1]["content"][1]["type"] == "image_url"
        assert (
            "data:image/png;base64,base64_image_data"
            in messages[1]["content"][1]["image_url"]["url"]
        )

    # Note: _call_api is tested indirectly through OpenAIAnalyzer and AzureOpenAIAnalyzer tests
    # Direct testing of async context managers is complex and the method is fully covered by integration tests

    @pytest.mark.asyncio
    async def test_call_api_error_status(self):
        """Test API call with error status code."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = mock_session_class.return_value.__aenter__.return_value
            mock_response = Mock()
            mock_response.status = 401
            mock_response.text = AsyncMock(return_value="Unauthorized")
            mock_session.post.return_value.__aenter__.return_value = mock_response

            result = await analyzer._call_api(
                url="https://api.openai.com/v1/chat/completions",
                headers={"Authorization": "Bearer test"},
                data={"messages": []},
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_call_api_network_error(self):
        """Test API call with network error."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        with patch("aiohttp.ClientSession.post", side_effect=Exception("Network error")):
            result = await analyzer._call_api(
                url="https://api.openai.com/v1/chat/completions",
                headers={"Authorization": "Bearer test"},
                data={"messages": []},
            )

            assert result is None

    def test_extract_confidence_score_with_label(self):
        """Test extracting confidence score from labeled format."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        content = "Confidence Score: 0.95\nDescription: This is a logo"
        assert analyzer._extract_confidence_score(content) == 0.95

        content = "Confidence: 0.85"
        assert analyzer._extract_confidence_score(content) == 0.85

    def test_extract_confidence_score_at_start(self):
        """Test extracting confidence score from start of content."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        content = "0.92 - This is a company logo"
        assert analyzer._extract_confidence_score(content) == 0.92

        content = "0.88, The image contains a logo"
        assert analyzer._extract_confidence_score(content) == 0.88

    def test_extract_confidence_score_missing(self):
        """Test extracting confidence when none exists."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        content = "This is just a description without confidence"
        assert analyzer._extract_confidence_score(content) == 0.0

    def test_extract_description_with_label(self):
        """Test extracting description with Description: label."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        content = "Confidence Score: 0.95\nDescription: A blue company logo"
        description = analyzer._extract_description(content)

        assert "A blue company logo" in description
        assert "Confidence" not in description

    def test_extract_description_without_label(self):
        """Test extracting description without explicit label."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        content = "0.95 - This is a logo with blue text and white background"
        description = analyzer._extract_description(content)

        assert "logo with blue text" in description

    def test_extract_description_filters_confidence_lines(self):
        """Test that confidence lines are filtered from description."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        content = "Confidence: 0.95\nThis is the actual description\nMore details here"
        description = analyzer._extract_description(content)

        assert "Confidence" not in description
        assert "actual description" in description
        assert "More details" in description

    def test_get_image_hash(self):
        """Test image hash generation."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        hash1 = analyzer._get_image_hash("test_image_data")
        hash2 = analyzer._get_image_hash("test_image_data")
        hash3 = analyzer._get_image_hash("different_image_data")

        # Same data produces same hash
        assert hash1 == hash2
        # Different data produces different hash
        assert hash1 != hash3
        # Hash is hex string
        assert all(c in "0123456789abcdef" for c in hash1)

    def test_parse_response_valid(self):
        """Test parsing valid API response."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        response = {
            "choices": [
                {"message": {"content": "Confidence Score: 0.92\nDescription: Blue company logo"}}
            ]
        }

        result = analyzer._parse_response(
            response, "https://example.com/logo.png", "https://example.com", "base64data"
        )

        assert result is not None
        assert isinstance(result, LogoResult)
        assert result.confidence == 0.92
        assert "Blue company logo" in result.description
        assert result.url == "https://example.com/logo.png"
        assert result.page_url == "https://example.com"

    def test_parse_response_null_content(self):
        """Test parsing response when content is 'null' (no logo)."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        response = {"choices": [{"message": {"content": "null"}}]}

        result = analyzer._parse_response(
            response, "https://example.com/not-logo.png", "https://example.com", "base64data"
        )

        assert result is None

    def test_parse_response_missing_choices(self):
        """Test parsing response with missing choices."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        response = {}
        result = analyzer._parse_response(
            response, "https://example.com/logo.png", "https://example.com", "base64data"
        )
        assert result is None

    def test_parse_response_empty_choices(self):
        """Test parsing response with empty choices array."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        response = {"choices": []}
        result = analyzer._parse_response(
            response, "https://example.com/logo.png", "https://example.com", "base64data"
        )
        assert result is None

    def test_parse_response_missing_message(self):
        """Test parsing response with missing message."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        response = {"choices": [{}]}
        result = analyzer._parse_response(
            response, "https://example.com/logo.png", "https://example.com", "base64data"
        )
        assert result is None

    def test_parse_response_missing_content(self):
        """Test parsing response with missing content."""
        analyzer = BaseOpenAIAnalyzer(api_key="test_key")

        response = {"choices": [{"message": {}}]}
        result = analyzer._parse_response(
            response, "https://example.com/logo.png", "https://example.com", "base64data"
        )
        assert result is None
