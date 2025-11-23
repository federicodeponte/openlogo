"""Configuration management for crawl4logo."""
import os
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class LogoCrawlerConfig(BaseModel):
    """Configuration for LogoCrawler with sensible defaults."""

    # API Configuration
    api_key: str = Field(..., description="OpenAI API key (Azure or regular)")

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that API key is not empty."""
        if not v or not v.strip():
            raise ValueError(
                "OpenAI API key is required. "
                "Please provide your API key when initializing LogoCrawler."
            )
        return v
    use_azure: bool = Field(default=False, description="Use Azure OpenAI instead of regular OpenAI")
    azure_endpoint: Optional[str] = Field(default=None, description="Azure OpenAI endpoint URL")
    azure_deployment: str = Field(default="gpt-4o-mini", description="Azure OpenAI deployment name")
    api_version: str = Field(default="2024-02-15-preview", description="Azure API version")

    # Image Processing
    min_width: int = Field(default=32, description="Minimum image width in pixels")
    min_height: int = Field(default=32, description="Minimum image height in pixels")

    # Filtering
    confidence_threshold: float = Field(default=0.8, description="Minimum confidence score for logos")

    # Caching
    cache_duration_days: int = Field(default=1, description="Cache duration in days")

    # Cloud Storage (Optional)
    supabase_url: Optional[str] = Field(default=None, description="Supabase project URL")
    supabase_key: Optional[str] = Field(default=None, description="Supabase API key")

    @classmethod
    def from_env(cls, **overrides) -> "LogoCrawlerConfig":
        """
        Load configuration from environment variables.

        Environment variables:
            OPENAI_API_KEY or AZURE_OPENAI_API_KEY
            AZURE_OPENAI_ENDPOINT
            AZURE_OPENAI_DEPLOYMENT
            AZURE_API_VERSION
            MIN_IMAGE_WIDTH
            MIN_IMAGE_HEIGHT
            CONFIDENCE_THRESHOLD
            CACHE_DURATION_DAYS
            SUPABASE_URL
            SUPABASE_KEY

        Args:
            **overrides: Override specific config values

        Returns:
            LogoCrawlerConfig instance
        """
        use_azure = overrides.get("use_azure", False)

        # API key: try Azure first if use_azure=True, otherwise regular OpenAI
        api_key = overrides.get("api_key")
        if not api_key:
            if use_azure:
                api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
            else:
                api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")

        config_dict = {
            "api_key": api_key or "",
            "use_azure": use_azure,
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
            "api_version": os.getenv("AZURE_API_VERSION", "2024-02-15-preview"),
            "min_width": int(os.getenv("MIN_IMAGE_WIDTH", "32")),
            "min_height": int(os.getenv("MIN_IMAGE_HEIGHT", "32")),
            "confidence_threshold": float(os.getenv("CONFIDENCE_THRESHOLD", "0.8")),
            "cache_duration_days": int(os.getenv("CACHE_DURATION_DAYS", "1")),
            "supabase_url": os.getenv("SUPABASE_URL"),
            "supabase_key": os.getenv("SUPABASE_KEY"),
        }

        # Apply overrides
        config_dict.update(overrides)

        return cls(**config_dict)
