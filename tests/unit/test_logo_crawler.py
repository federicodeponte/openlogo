"""Unit tests for LogoCrawler class."""

import pytest
from fede_crawl4ai import LogoCrawler


class TestLogoCrawlerInit:
    """Test LogoCrawler initialization."""

    def test_init_with_api_key(self, mock_api_key):
        """Test successful initialization with API key."""
        crawler = LogoCrawler(api_key=mock_api_key)
        assert crawler.api_key == mock_api_key
        assert crawler.use_azure is False
        assert crawler.min_width == 32
        assert crawler.min_height == 32

    def test_init_without_api_key(self):
        """Test initialization fails without API key."""
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            LogoCrawler(api_key=None)

    def test_init_with_azure(self, mock_api_key):
        """Test initialization with Azure OpenAI."""
        crawler = LogoCrawler(api_key=mock_api_key, use_azure=True)
        assert crawler.use_azure is True


class TestImageValidation:
    """Test image validation methods."""

    def test_is_valid_image_size_valid(self, mock_api_key):
        """Test valid image size detection."""
        crawler = LogoCrawler(api_key=mock_api_key)
        # Image larger than min dimensions should be valid
        assert crawler.is_valid_image_size(100, 100) is True
        assert crawler.is_valid_image_size(50, 50) is True

    def test_is_valid_image_size_invalid(self, mock_api_key):
        """Test invalid image size detection."""
        crawler = LogoCrawler(api_key=mock_api_key)
        # Images smaller than min dimensions should be invalid
        assert crawler.is_valid_image_size(10, 10) is False
        assert crawler.is_valid_image_size(30, 30) is False
        assert crawler.is_valid_image_size(32, 10) is False


class TestExtractMethods:
    """Test content extraction methods."""

    def test_extract_confidence_score_valid(self, mock_api_key):
        """Test extracting valid confidence score."""
        crawler = LogoCrawler(api_key=mock_api_key)

        # Test with valid JSON
        content = '{"is_logo": true, "confidence": 0.95}'
        assert crawler.extract_confidence_score(content) == 0.95

        # Test with different confidence
        content = '{"is_logo": true, "confidence": 0.75}'
        assert crawler.extract_confidence_score(content) == 0.75

    def test_extract_confidence_score_invalid(self, mock_api_key):
        """Test extracting confidence from invalid content."""
        crawler = LogoCrawler(api_key=mock_api_key)

        # Test with invalid JSON
        assert crawler.extract_confidence_score("invalid json") == 0.0

        # Test with missing confidence field
        content = '{"is_logo": true}'
        assert crawler.extract_confidence_score(content) == 0.0

    def test_extract_description_valid(self, mock_api_key):
        """Test extracting valid description."""
        crawler = LogoCrawler(api_key=mock_api_key)

        content = '{"is_logo": true, "description": "A beautiful logo"}'
        assert crawler.extract_description(content) == "A beautiful logo"

    def test_extract_description_invalid(self, mock_api_key):
        """Test extracting description from invalid content."""
        crawler = LogoCrawler(api_key=mock_api_key)

        # Test with invalid JSON
        assert crawler.extract_description("invalid") == "No description available"

        # Test with missing description
        content = '{"is_logo": true}'
        assert crawler.extract_description(content) == "No description available"


class TestImageHash:
    """Test image hashing functionality."""

    def test_get_image_hash(self, mock_api_key):
        """Test image hash generation."""
        crawler = LogoCrawler(api_key=mock_api_key)

        # Same content should produce same hash
        content1 = b"test image data"
        content2 = b"test image data"
        assert crawler.get_image_hash(content1) == crawler.get_image_hash(content2)

        # Different content should produce different hash
        content3 = b"different image data"
        assert crawler.get_image_hash(content1) != crawler.get_image_hash(content3)

    def test_get_image_hash_consistency(self, mock_api_key):
        """Test that hash is consistent across multiple calls."""
        crawler = LogoCrawler(api_key=mock_api_key)

        content = b"consistent test data"
        hash1 = crawler.get_image_hash(content)
        hash2 = crawler.get_image_hash(content)
        hash3 = crawler.get_image_hash(content)

        assert hash1 == hash2 == hash3
