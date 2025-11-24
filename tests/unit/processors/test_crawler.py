"""Unit tests for CrawlerEngine."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fede_crawl4ai.processors.crawler import CrawlerEngine


class TestCrawlerEngine:
    """Test CrawlerEngine functionality."""

    def test_initialization(self):
        """Test crawler initializes with correct defaults."""
        crawler = CrawlerEngine()
        assert crawler._timeout == 30
        assert "LogoCrawler" in crawler._user_agent

    def test_initialization_with_custom_values(self):
        """Test crawler initializes with custom values."""
        crawler = CrawlerEngine(timeout=60, user_agent="CustomBot/1.0")
        assert crawler._timeout == 60
        assert crawler._user_agent == "CustomBot/1.0"

    # Note: fetch_page success case tested via integration tests
    # Async mocking complexity makes unit testing difficult

    @pytest.mark.asyncio
    async def test_fetch_page_404(self):
        """Test page fetch with 404 error."""
        crawler = CrawlerEngine()

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = mock_session_class.return_value.__aenter__.return_value
            mock_response = Mock()
            mock_response.status = 404
            mock_session.get.return_value.__aenter__.return_value = mock_response

            result = await crawler.fetch_page("https://example.com/notfound")

            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_page_network_error(self):
        """Test page fetch with network error."""
        crawler = CrawlerEngine()

        with patch("aiohttp.ClientSession.get", side_effect=Exception("Network error")):
            result = await crawler.fetch_page("https://example.com")

            assert result is None

    def test_extract_images(self):
        """Test extracting images from HTML."""
        crawler = CrawlerEngine()

        html = """
        <html>
            <body>
                <img src="/logo.png">
                <img src="https://cdn.example.com/banner.jpg">
                <img src="icon.svg">
            </body>
        </html>
        """

        images = crawler.extract_images(html, "https://example.com")

        assert len(images) == 3
        assert "https://example.com/logo.png" in images
        assert "https://cdn.example.com/banner.jpg" in images
        assert "https://example.com/icon.svg" in images

    def test_extract_header_images(self):
        """Test extracting images from header/nav elements."""
        crawler = CrawlerEngine()

        html = """
        <html>
            <header>
                <img src="/header-logo.png">
            </header>
            <nav>
                <img src="/nav-icon.svg">
            </nav>
            <body>
                <img src="/body-image.jpg">
            </body>
        </html>
        """

        header_images = crawler.extract_header_images(html, "https://example.com")

        assert len(header_images) == 2
        assert "https://example.com/header-logo.png" in header_images
        assert "https://example.com/nav-icon.svg" in header_images
        # Body image should NOT be included
        assert "https://example.com/body-image.jpg" not in header_images

    def test_is_valid_image_url(self):
        """Test image URL validation."""
        crawler = CrawlerEngine()

        # Valid image URLs
        assert crawler.is_valid_image_url("https://example.com/logo.png") is True
        assert crawler.is_valid_image_url("https://example.com/image.jpg") is True
        assert crawler.is_valid_image_url("https://example.com/icon.svg") is True
        assert crawler.is_valid_image_url("https://example.com/photo.webp") is True

        # Invalid URLs
        assert crawler.is_valid_image_url("https://example.com/page.html") is False
        assert crawler.is_valid_image_url("https://example.com/script.js") is False
        assert crawler.is_valid_image_url("https://example.com/") is False

    def test_filter_valid_images(self):
        """Test filtering list of URLs to only images."""
        crawler = CrawlerEngine()

        urls = [
            "https://example.com/logo.png",
            "https://example.com/page.html",
            "https://example.com/icon.svg",
            "https://example.com/script.js",
            "https://example.com/photo.jpg",
        ]

        valid = crawler.filter_valid_images(urls)

        assert len(valid) == 3
        assert "https://example.com/logo.png" in valid
        assert "https://example.com/icon.svg" in valid
        assert "https://example.com/photo.jpg" in valid
        assert "https://example.com/page.html" not in valid
        assert "https://example.com/script.js" not in valid

    def test_extract_images_with_no_images(self):
        """Test extracting images from HTML with no img tags."""
        crawler = CrawlerEngine()

        html = "<html><body><p>No images here</p></body></html>"

        images = crawler.extract_images(html, "https://example.com")

        assert len(images) == 0

    def test_extract_images_handles_missing_src(self):
        """Test that images without src attribute are skipped."""
        crawler = CrawlerEngine()

        html = """
        <html>
            <body>
                <img src="/logo.png">
                <img alt="No src attribute">
                <img src="/icon.svg">
            </body>
        </html>
        """

        images = crawler.extract_images(html, "https://example.com")

        assert len(images) == 2  # Only images with src
        assert "https://example.com/logo.png" in images
        assert "https://example.com/icon.svg" in images
