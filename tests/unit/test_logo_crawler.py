"""Unit tests for LogoCrawler class."""

import pytest
from PIL import Image
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

        # Create mock images with valid dimensions
        img_large = Image.new("RGB", (100, 100))
        img_medium = Image.new("RGB", (50, 50))

        assert crawler.is_valid_image_size(img_large) is True
        assert crawler.is_valid_image_size(img_medium) is True

    def test_is_valid_image_size_invalid(self, mock_api_key):
        """Test invalid image size detection."""
        crawler = LogoCrawler(api_key=mock_api_key)

        # Create mock images with invalid dimensions (smaller than min 32x32)
        img_tiny = Image.new("RGB", (10, 10))
        img_small = Image.new("RGB", (30, 30))
        img_narrow = Image.new("RGB", (32, 10))

        assert crawler.is_valid_image_size(img_tiny) is False
        assert crawler.is_valid_image_size(img_small) is False
        assert crawler.is_valid_image_size(img_narrow) is False


class TestExtractMethods:
    """Test content extraction methods."""

    def test_extract_confidence_score_valid(self, mock_api_key):
        """Test extracting valid confidence score."""
        crawler = LogoCrawler(api_key=mock_api_key)

        # Test with standard format
        content = "Confidence Score: 0.95\nDescription: Test logo"
        assert crawler.extract_confidence_score(content) == 0.95

        # Test with alternate format
        content = "Confidence: 0.75"
        assert crawler.extract_confidence_score(content) == 0.75

        # Test with number at start
        content = "0.85 - This is a logo"
        assert crawler.extract_confidence_score(content) == 0.85

    def test_extract_confidence_score_invalid(self, mock_api_key):
        """Test extracting confidence from invalid content."""
        crawler = LogoCrawler(api_key=mock_api_key)

        # Test with no confidence score
        assert crawler.extract_confidence_score("invalid json") == 0.0

        # Test with no parseable number
        content = "This is just text"
        assert crawler.extract_confidence_score(content) == 0.0

    def test_extract_description_valid(self, mock_api_key):
        """Test extracting valid description."""
        crawler = LogoCrawler(api_key=mock_api_key)

        # Test with Description: marker
        content = "Confidence Score: 0.95\nDescription: A beautiful logo"
        assert crawler.extract_description(content) == "A beautiful logo"

        # Test without Description marker
        content = "This is a company logo with blue colors"
        desc = crawler.extract_description(content)
        assert "logo" in desc.lower()

    def test_extract_description_filters_confidence(self, mock_api_key):
        """Test that description filters out confidence lines."""
        crawler = LogoCrawler(api_key=mock_api_key)

        # Test that confidence lines are filtered
        content = "Confidence: 0.95\nThis is the actual description"
        desc = crawler.extract_description(content)
        assert "Confidence" not in desc
        assert "actual description" in desc


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
