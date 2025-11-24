"""Protocol definitions (interfaces) for crawl4logo components.

Protocols define the contracts that implementations must follow,
enabling dependency injection and easy testing with mocks.
"""

from typing import Protocol, Optional, List
from .models import LogoResult


class ImageAnalyzer(Protocol):
    """Interface for image analysis services (OpenAI, Azure, etc.)."""

    async def analyze(
        self,
        image_base64: str,
        image_url: str,
        page_url: str,
    ) -> Optional[LogoResult]:
        """
        Analyze an image to detect if it contains a logo.

        Args:
            image_base64: Base64-encoded image data
            image_url: URL where image was found
            page_url: URL of page containing the image

        Returns:
            LogoResult if logo detected, None otherwise
        """
        ...


class LogoExtractor(Protocol):
    """Interface for extracting logo URLs from HTML."""

    async def extract_logo_urls(
        self,
        html: str,
        base_url: str,
    ) -> List[str]:
        """
        Extract potential logo image URLs from HTML.

        Args:
            html: HTML content to parse
            base_url: Base URL for resolving relative URLs

        Returns:
            List of absolute image URLs
        """
        ...


class StorageProvider(Protocol):
    """Interface for storing processed images."""

    async def upload(
        self,
        image_data: bytes,
        filename: str,
    ) -> Optional[str]:
        """
        Upload image to storage and return public URL.

        Args:
            image_data: Raw image bytes
            filename: Desired filename

        Returns:
            Public URL of uploaded image, or None if upload failed
        """
        ...


class CacheProvider(Protocol):
    """Interface for caching analyzed images."""

    def get(self, image_hash: str) -> Optional[LogoResult]:
        """
        Get cached logo result by image hash.

        Args:
            image_hash: MD5 hash of image content

        Returns:
            Cached LogoResult if found and not expired, None otherwise
        """
        ...

    def set(self, image_hash: str, result: LogoResult) -> None:
        """
        Cache a logo analysis result.

        Args:
            image_hash: MD5 hash of image content
            result: LogoResult to cache
        """
        ...

    def clear(self) -> None:
        """Clear all cached results."""
        ...
