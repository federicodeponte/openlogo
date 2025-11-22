"""Pytest configuration and shared fixtures for crawl4logo tests."""

import os
import pytest
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_api_key():
    """Provide a mock API key for testing."""
    return "test-api-key-mock-12345"


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for logo detection."""
    return {
        "choices": [
            {
                "message": {
                    "content": '{"is_logo": true, "confidence": 0.95, "description": "A stylized logo with distinctive branding elements"}'
                }
            }
        ]
    }


@pytest.fixture
def sample_image_url():
    """Sample image URL for testing."""
    return "https://example.com/logo.png"


@pytest.fixture
def sample_page_url():
    """Sample page URL for testing."""
    return "https://example.com"


@pytest.fixture
def mock_html_content():
    """Mock HTML content with images."""
    return """
    <html>
        <body>
            <header>
                <img src="/logo.png" alt="Company Logo" class="site-logo">
            </header>
            <main>
                <img src="/icon.svg" alt="Icon">
            </main>
        </body>
    </html>
    """


@pytest.fixture
def set_env_vars(monkeypatch):
    """Set environment variables for testing."""

    def _set_env(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key, value)

    return _set_env


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession."""
    session = AsyncMock()
    response = AsyncMock()
    response.status = 200
    response.read = AsyncMock(return_value=b"fake image data")
    session.get = AsyncMock(return_value=response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session
