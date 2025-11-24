"""Regular OpenAI analyzer implementation."""

import logging
from typing import Optional
from .base import BaseOpenAIAnalyzer
from ..models import LogoResult

logger = logging.getLogger(__name__)


class OpenAIAnalyzer(BaseOpenAIAnalyzer):
    """Analyze images using regular OpenAI API (gpt-4o-mini)."""

    async def analyze(
        self,
        image_base64: str,
        image_url: str,
        page_url: str,
    ) -> Optional[LogoResult]:
        """
        Analyze image using regular OpenAI API.

        Args:
            image_base64: Base64-encoded image data
            image_url: URL of the image
            page_url: URL of the page containing the image

        Returns:
            LogoResult if logo detected, None otherwise
        """
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": self._build_messages(image_base64),
            "max_tokens": 300,
        }

        logger.debug(f"Analyzing image with OpenAI: {image_url}")

        # Make API call using base class method
        result = await self._call_api(url, headers, data)
        if not result:
            return None

        # Parse response using base class method
        return self._parse_response(result, image_url, page_url, image_base64)
