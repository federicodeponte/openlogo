"""HTTP crawling and image extraction engine."""

import logging
from typing import List, Optional
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class CrawlerEngine:
    """Engine for crawling websites and extracting image URLs."""

    def __init__(self, timeout: int = 30, user_agent: Optional[str] = None):
        """
        Initialize crawler engine.

        Args:
            timeout: HTTP request timeout in seconds (default: 30)
            user_agent: Custom user agent string (optional)
        """
        self._timeout = timeout
        self._user_agent = user_agent or "LogoCrawler/0.3.0"

    async def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from URL.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string, or None if fetch failed
        """
        headers = {"User-Agent": self._user_agent}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=self._timeout), headers=headers
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        logger.info(f"Successfully fetched {url} ({len(html)} bytes)")
                        return html
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return None

        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    def extract_images(self, html: str, base_url: str) -> List[str]:
        """
        Extract all image URLs from HTML.

        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs

        Returns:
            List of absolute image URLs
        """
        soup = BeautifulSoup(html, "html.parser")
        images = []

        # Extract from <img> tags
        for img in soup.find_all("img"):
            if src := img.get("src"):
                absolute_url = urljoin(base_url, src)
                images.append(absolute_url)

        logger.info(f"Extracted {len(images)} images from HTML")
        return images

    def extract_header_images(self, html: str, base_url: str) -> List[str]:
        """
        Extract images specifically from header/nav elements.

        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs

        Returns:
            List of absolute image URLs found in header/nav
        """
        soup = BeautifulSoup(html, "html.parser")
        header_images = []

        # Find header/nav elements
        for element in soup.find_all(["header", "nav"]):
            for img in element.find_all("img"):
                if src := img.get("src"):
                    absolute_url = urljoin(base_url, src)
                    header_images.append(absolute_url)

        logger.info(f"Extracted {len(header_images)} images from header/nav elements")
        return header_images

    def is_valid_image_url(self, url: str) -> bool:
        """
        Check if URL appears to be a valid image.

        Args:
            url: URL to check

        Returns:
            True if URL looks like an image
        """
        # Basic check - can be improved
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico"}
        parsed = urlparse(url.lower())
        path = parsed.path

        return any(path.endswith(ext) for ext in image_extensions)

    def filter_valid_images(self, urls: List[str]) -> List[str]:
        """
        Filter list of URLs to only valid image URLs.

        Args:
            urls: List of URLs to filter

        Returns:
            List of URLs that appear to be images
        """
        valid = [url for url in urls if self.is_valid_image_url(url)]
        logger.debug(f"Filtered {len(urls)} URLs → {len(valid)} valid images")
        return valid
