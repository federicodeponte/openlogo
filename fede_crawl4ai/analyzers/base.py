"""Base analyzer with common OpenAI logic.

This module contains the shared implementation for both regular OpenAI
and Azure OpenAI analyzers, eliminating code duplication.
"""

import logging
import hashlib
import re
from typing import Optional, Dict, Any
from datetime import datetime
import aiohttp
from ..models import LogoResult

logger = logging.getLogger(__name__)


class BaseOpenAIAnalyzer:
    """Common logic for OpenAI-compatible APIs (regular and Azure).

    This base class contains all the shared code between OpenAI and Azure
    analyzers, eliminating ~100 lines of duplication.
    """

    def __init__(self, api_key: str):
        """
        Initialize base analyzer.

        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key

    def _build_messages(self, image_base64: str) -> list:
        """
        Build OpenAI messages payload (same for Azure and regular).

        Args:
            image_base64: Base64-encoded image data

        Returns:
            List of message dicts for OpenAI API
        """
        return [
            {
                "role": "system",
                "content": (
                    "You are a logo detection assistant. Analyze the image and determine "
                    "if it's a logo. If it is, provide a confidence score (0-1) and description "
                    "in this format: 'Confidence Score: X.XX\\nDescription: ...'. If not, return 'null'."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Is this image a logo? If yes, provide a confidence score (0-1) and "
                            "a brief description of what makes it a logo. Format your response as "
                            "'Confidence Score: X.XX\\nDescription: ...'. If no, return null."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                ],
            },
        ]

    async def _call_api(
        self,
        url: str,
        headers: Dict[str, str],
        data: Dict[str, Any],
    ) -> Optional[dict]:
        """
        Make API request and handle errors (same for both providers).

        Args:
            url: API endpoint URL
            headers: HTTP headers
            data: JSON payload

        Returns:
            Response dict if successful, None otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API Error ({response.status}): {error_text}")
                        return None

                    try:
                        result = await response.json()
                        logger.debug("API Response received")
                        return result
                    except Exception as e:
                        logger.error(f"Error decoding JSON response: {e}")
                        response_text = await response.text()
                        logger.debug(f"Raw response: {response_text}")
                        return None

        except aiohttp.ClientError as e:
            logger.error(f"HTTP Error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in API call: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _extract_confidence_score(self, content: str) -> float:
        """
        Extract confidence score from OpenAI response.

        Tries multiple patterns to find the confidence score in the response text.

        Args:
            content: OpenAI response content

        Returns:
            Confidence score (0.0-1.0), or 0.0 if not found
        """
        patterns = [
            r"confidence score:\s*(\d*\.?\d+)",  # "Confidence Score: 0.9"
            r"confidence:\s*(\d*\.?\d+)",  # "Confidence: 0.9"
            r"^(\d*\.?\d+),\s*",  # "0.9, This image..."
            r"^(\d*\.?\d+)\s*-\s*",  # "0.95 - The image..."
            r"^(\d*\.?\d+)$",  # Just a number
        ]

        # First, try to find confidence in dedicated line
        lines = content.split("\n")
        for line in lines:
            line_lower = line.lower().strip()
            if line_lower.startswith(("confidence:", "confidence score:")):
                try:
                    match = re.search(r"(\d*\.?\d+)", line)
                    if match:
                        return float(match.group(1))
                except (ValueError, AttributeError):
                    continue

        # Try patterns on entire content
        content_lower = content.lower()
        for pattern in patterns:
            match = re.search(pattern, content_lower)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue

        logger.warning(f"Could not extract confidence score from: {content[:100]}")
        return 0.0

    def _extract_description(self, content: str) -> str:
        """
        Extract description from OpenAI response.

        Args:
            content: OpenAI response content

        Returns:
            Logo description (without confidence lines)
        """
        # Try to find description after "Description:" marker
        if "description:" in content.lower():
            parts = re.split(r"description:\s*", content, flags=re.IGNORECASE)
            if len(parts) > 1:
                description = parts[1].strip()
                if description:
                    return description

        # Filter out confidence lines
        lines = content.split("\n")
        filtered_lines = []
        for line in lines:
            if line.lower().strip().startswith(("confidence:", "confidence score:")):
                continue
            filtered_lines.append(line)

        return " ".join(filtered_lines).strip()

    def _get_image_hash(self, image_base64: str) -> str:
        """
        Generate MD5 hash of image for caching.

        Args:
            image_base64: Base64-encoded image data

        Returns:
            MD5 hash hex string
        """
        return hashlib.md5(image_base64.encode()).hexdigest()

    def _parse_response(
        self,
        result: Dict[str, Any],
        image_url: str,
        page_url: str,
        image_base64: str,
    ) -> Optional[LogoResult]:
        """
        Parse OpenAI response into LogoResult (same for both providers).

        Args:
            result: OpenAI API response dict
            image_url: URL of the image
            page_url: URL of the page containing the image
            image_base64: Base64-encoded image data

        Returns:
            LogoResult if logo detected, None otherwise
        """
        # Validate response structure
        if not result.get("choices"):
            logger.warning(f"No 'choices' in API response for {image_url}")
            return None

        if not result["choices"]:
            logger.warning(f"Empty 'choices' array in API response for {image_url}")
            return None

        if not result["choices"][0].get("message"):
            logger.warning(f"No 'message' in first choice for {image_url}")
            return None

        if not result["choices"][0]["message"].get("content"):
            logger.warning(f"No 'content' in message for {image_url}")
            return None

        content = result["choices"][0]["message"]["content"]
        logger.debug(f"Content from API: {content[:100]}...")

        # Check if response is "null" (no logo detected)
        if content.lower().strip() == "null":
            logger.debug(f"Content is 'null', skipping image: {image_url}")
            return None

        # Extract confidence and description
        confidence = self._extract_confidence_score(content)
        description = self._extract_description(content)
        image_hash = self._get_image_hash(image_base64)

        logger.debug(f"Extracted confidence: {confidence}, description: {description[:50]}...")

        # Create LogoResult
        return LogoResult(
            url=image_url,
            confidence=confidence,
            description=description,
            page_url=page_url,
            image_hash=image_hash,
            timestamp=datetime.now(),
            rank_score=confidence,  # Use confidence as initial rank score
            detection_scores={},  # Backward compatibility
        )
