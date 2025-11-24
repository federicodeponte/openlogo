"""crawl4logo - Web crawler for logo detection using GPT-4o-mini.

Main exports:
    LogoCrawler: Main crawler class for logo detection

Advanced exports (optional):
    Models: LogoResult
    Config: LogoCrawlerConfig
    Analyzers: OpenAIAnalyzer, AzureOpenAIAnalyzer
    Storage: ImageCache, CloudStorage
    Processors: CrawlerEngine, LogoRanker
"""

from .logo_crawler import LogoCrawler
from .models import LogoResult
from .config import LogoCrawlerConfig

# Advanced imports (for power users who want dependency injection)
from .analyzers import OpenAIAnalyzer, AzureOpenAIAnalyzer
from .storage import ImageCache, CloudStorage
from .processors import CrawlerEngine, LogoRanker

__version__ = "0.3.0"

__all__ = [
    # Main API (most users need only this)
    "LogoCrawler",
    # Data models
    "LogoResult",
    "LogoCrawlerConfig",
    # Advanced (for dependency injection)
    "OpenAIAnalyzer",
    "AzureOpenAIAnalyzer",
    "ImageCache",
    "CloudStorage",
    "CrawlerEngine",
    "LogoRanker",
]
