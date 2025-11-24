"""Azure OpenAI analyzer implementation."""

import logging
from typing import Optional
from .base import BaseOpenAIAnalyzer
from ..models import LogoResult

logger = logging.getLogger(__name__)


class AzureOpenAIAnalyzer(BaseOpenAIAnalyzer):
    """Analyze images using Azure OpenAI API."""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment: str = "gpt-4o-mini",
        api_version: str = "2024-02-15-preview",
    ):
        """
        Initialize Azure OpenAI analyzer.

        Args:
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL (e.g., https://yourcompany.openai.azure.com)
            deployment: Deployment name (default: gpt-4o-mini)
            api_version: API version (default: 2024-02-15-preview)
        """
        super().__init__(api_key)
        self.endpoint = endpoint
        self.deployment = deployment
        self.api_version = api_version

    async def analyze(
        self,
        image_base64: str,
        image_url: str,
        page_url: str,
    ) -> Optional[LogoResult]:
        """
        Analyze image using Azure OpenAI API.

        Args:
            image_base64: Base64-encoded image data
            image_url: URL of the image
            page_url: URL of the page containing the image

        Returns:
            LogoResult if logo detected, None otherwise
        """
        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }
        data = {
            "messages": self._build_messages(image_base64),
            "max_tokens": 300,
        }

        logger.debug(f"Analyzing image with Azure OpenAI: {image_url}")

        # Make API call using base class method
        result = await self._call_api(url, headers, data)
        if not result:
            return None

        # Parse response using base class method
        return self._parse_response(result, image_url, page_url, image_base64)
