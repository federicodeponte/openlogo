# v0.3.0 Refactor Plan - SOLID Architecture

## Goals

**Transform crawl4logo from a 1300-line god class into a clean, testable, SOLID architecture**

- **Iterative**: 5 phases, each independently testable
- **Test-driven**: >80% coverage, tests written FIRST
- **DRY**: Eliminate ~100 lines of Azure/OpenAI duplication
- **SOLID**: Every class has single responsibility
- **KISS**: Simpler code through proper abstractions
- **Modular**: Independent, swappable components

## Current State (v0.2.0)

```
fede_crawl4ai/
├── __init__.py
├── config.py (97 lines)
└── logo_crawler.py (1298 lines) ← GOD CLASS
```

**Problems:**
- ❌ 1298-line LogoCrawler class (23 methods)
- ❌ No dependency injection
- ❌ ~100 lines duplicated (Azure vs OpenAI)
- ❌ 22% test coverage
- ❌ Cannot test without real OpenAI calls
- ❌ Violates all SOLID principles

## Target State (v0.3.0)

```
fede_crawl4ai/
├── __init__.py
├── config.py
├── models.py                     # Data models (LogoResult, etc.)
├── protocols.py                  # Interface definitions
├── analyzers/
│   ├── __init__.py
│   ├── base.py                   # ImageAnalyzer protocol
│   ├── openai_analyzer.py        # Regular OpenAI
│   └── azure_analyzer.py         # Azure OpenAI
├── extractors/
│   ├── __init__.py
│   ├── base.py                   # LogoExtractor protocol
│   └── html_extractor.py         # HTML parsing logic
├── storage/
│   ├── __init__.py
│   ├── base.py                   # StorageProvider protocol
│   ├── cache.py                  # ImageCache
│   └── cloud.py                  # CloudStorage
├── processors/
│   ├── __init__.py
│   ├── crawler.py                # HTTP crawling
│   ├── ranker.py                 # Logo ranking
│   └── csv_processor.py          # Batch CSV processing
└── crawler.py                    # Thin orchestrator (~100 lines)
```

**Benefits:**
- ✅ Each file <300 lines
- ✅ Each class <10 methods
- ✅ Dependency injection everywhere
- ✅ Mock-friendly for testing
- ✅ >80% test coverage
- ✅ Follows all SOLID principles

---

## Phase 1: Extract Models & Protocols

**Goal**: Define interfaces and data structures

### 1.1 Create `fede_crawl4ai/models.py`
```python
"""Data models for crawl4logo."""
from datetime import datetime
from typing import Dict
from pydantic import BaseModel, Field


class LogoResult(BaseModel):
    """Result of logo detection."""
    url: str = Field(..., description="Image URL")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    description: str = Field(..., description="Logo description")
    page_url: str = Field(..., description="Source page URL")
    image_hash: str = Field(..., description="MD5 hash of image")
    timestamp: datetime = Field(default_factory=datetime.now)
    is_header: bool = Field(default=False, description="Found in header")
    rank_score: float = Field(default=0.0, ge=0.0, le=1.0)
    detection_scores: Dict[str, Dict[str, float]] = Field(default_factory=dict)
```

### 1.2 Create `fede_crawl4ai/protocols.py`
```python
"""Protocol definitions (interfaces) for crawl4logo."""
from typing import Protocol, Optional, List
from PIL import Image
from .models import LogoResult


class ImageAnalyzer(Protocol):
    """Interface for image analysis services."""

    async def analyze(
        self,
        image_base64: str,
        image_url: str,
        page_url: str,
    ) -> Optional[LogoResult]:
        """Analyze image and return logo result if detected."""
        ...


class LogoExtractor(Protocol):
    """Interface for extracting logo URLs from HTML."""

    async def extract_logo_urls(
        self,
        html: str,
        base_url: str,
    ) -> List[str]:
        """Extract potential logo URLs from HTML."""
        ...


class StorageProvider(Protocol):
    """Interface for storing images."""

    async def upload(
        self,
        image_data: bytes,
        filename: str,
    ) -> Optional[str]:
        """Upload image and return public URL."""
        ...
```

### 1.3 Tests
```bash
# tests/unit/test_models.py
- test_logo_result_validation
- test_logo_result_confidence_bounds
- test_logo_result_defaults
```

**Lines changed**: ~150 (new)
**Tests**: 3 new tests

---

## Phase 2: Extract Analyzers (Unify Azure/OpenAI)

**Goal**: Eliminate ~100 lines of duplication

### 2.1 Create `fede_crawl4ai/analyzers/base.py`
```python
"""Base analyzer with common OpenAI logic."""
import logging
from typing import Optional
import aiohttp
from ..models import LogoResult
from ..protocols import ImageAnalyzer

logger = logging.getLogger(__name__)


class BaseOpenAIAnalyzer:
    """Common logic for OpenAI-compatible APIs."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _build_messages(self, image_base64: str) -> list:
        """Build OpenAI messages payload (same for Azure and regular)."""
        return [
            {
                "role": "system",
                "content": "You are a logo detection assistant...",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Is this image a logo?...",
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
        headers: dict,
        data: dict,
    ) -> Optional[dict]:
        """Make API request and handle errors (same for both)."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API Error ({response.status}): {error_text}")
                        return None

                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"HTTP Error: {e}")
            return None

    def _parse_response(
        self,
        result: dict,
        image_url: str,
        page_url: str,
        image_hash: str,
    ) -> Optional[LogoResult]:
        """Parse OpenAI response into LogoResult (same for both)."""
        # Validation and extraction logic (currently duplicated)
        ...
```

### 2.2 Create `fede_crawl4ai/analyzers/openai_analyzer.py`
```python
"""Regular OpenAI analyzer."""
from typing import Optional
from .base import BaseOpenAIAnalyzer
from ..models import LogoResult


class OpenAIAnalyzer(BaseOpenAIAnalyzer):
    """Analyze images using regular OpenAI API."""

    async def analyze(
        self,
        image_base64: str,
        image_url: str,
        page_url: str,
    ) -> Optional[LogoResult]:
        """Analyze image using regular OpenAI."""
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

        result = await self._call_api(url, headers, data)
        if not result:
            return None

        return self._parse_response(result, image_url, page_url, image_hash)
```

### 2.3 Create `fede_crawl4ai/analyzers/azure_analyzer.py`
```python
"""Azure OpenAI analyzer."""
from typing import Optional
from .base import BaseOpenAIAnalyzer
from ..models import LogoResult


class AzureOpenAIAnalyzer(BaseOpenAIAnalyzer):
    """Analyze images using Azure OpenAI API."""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment: str = "gpt-4o-mini",
        api_version: str = "2024-02-15-preview",
    ):
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
        """Analyze image using Azure OpenAI."""
        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }
        data = {
            "messages": self._build_messages(image_base64),
            "max_tokens": 300,
        }

        result = await self._call_api(url, headers, data)
        if not result:
            return None

        return self._parse_response(result, image_url, page_url, image_hash)
```

### 2.4 Tests
```bash
# tests/unit/analyzers/test_openai_analyzer.py
- test_analyze_success
- test_analyze_api_error
- test_analyze_invalid_response
- test_analyze_null_response

# tests/unit/analyzers/test_azure_analyzer.py
- test_analyze_success
- test_analyze_with_custom_deployment
- test_analyze_api_error

# tests/unit/analyzers/test_base.py
- test_build_messages
- test_call_api_success
- test_call_api_network_error
- test_parse_response_valid
- test_parse_response_missing_fields
```

**Lines removed**: ~100 (duplication eliminated)
**Lines added**: ~200 (but cleaner, testable)
**Tests**: 11 new tests

---

## Phase 3: Extract Storage & Cache

**Goal**: Make storage and caching mockable

### 3.1 Move `fede_crawl4ai/storage/cache.py`
```python
"""Image caching."""
from typing import Optional, Dict
from datetime import datetime, timedelta
from ..models import LogoResult


class ImageCache:
    """In-memory cache for analyzed images."""

    def __init__(self, ttl: timedelta = timedelta(days=1)):
        self._cache: Dict[str, LogoResult] = {}
        self._ttl = ttl

    def get(self, image_hash: str) -> Optional[LogoResult]:
        """Get cached result if not expired."""
        if image_hash not in self._cache:
            return None

        result = self._cache[image_hash]
        if datetime.now() - result.timestamp > self._ttl:
            del self._cache[image_hash]
            return None

        return result

    def set(self, image_hash: str, result: LogoResult) -> None:
        """Cache a result."""
        self._cache[image_hash] = result

    def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()
```

### 3.2 Move `fede_crawl4ai/storage/cloud.py`
```python
"""Cloud storage for images."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


class CloudStorage:
    """Upload images to cloud storage."""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self._client: Optional[Client] = None

        if SUPABASE_AVAILABLE and url and key:
            try:
                self._client = create_client(url, key)
                logger.info("Cloud storage initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize cloud storage: {e}")

    async def upload(
        self,
        image_data: bytes,
        filename: str,
    ) -> Optional[str]:
        """Upload image and return public URL."""
        if not self._client:
            return None

        try:
            bucket_name = "logo-images"
            file_path = f"background-removed/{filename}"

            response = self._client.storage.from_(bucket_name).upload(
                file_path,
                image_data,
                {"content-type": "image/png"},
            )

            if response.error:
                logger.error(f"Upload error: {response.error}")
                return None

            public_url = self._client.storage.from_(bucket_name).get_public_url(file_path)
            logger.info(f"Uploaded to cloud: {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"Cloud upload failed: {e}")
            return None
```

### 3.3 Tests
```bash
# tests/unit/storage/test_cache.py
- test_cache_get_miss
- test_cache_get_hit
- test_cache_expiration
- test_cache_set
- test_cache_clear

# tests/unit/storage/test_cloud.py
- test_upload_no_client
- test_upload_success (mocked)
- test_upload_error (mocked)
```

**Lines moved**: ~150 (extracted from god class)
**Tests**: 8 new tests

---

## Phase 4: Extract Processors

**Goal**: Separate crawling, ranking, CSV logic

### 4.1 Create `fede_crawl4ai/processors/crawler.py`
```python
"""HTTP crawling and image extraction."""
import logging
from typing import List, Optional
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CrawlerEngine:
    """Crawl websites and extract image URLs."""

    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML from URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        return await response.text()
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def extract_images(self, html: str, base_url: str) -> List[str]:
        """Extract all image URLs from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        images = []

        # <img> tags
        for img in soup.find_all("img"):
            if src := img.get("src"):
                images.append(urljoin(base_url, src))

        # <svg> tags
        # Background images
        # etc.

        return images

    def extract_header_images(self, html: str, base_url: str) -> List[str]:
        """Extract images from header/nav elements."""
        soup = BeautifulSoup(html, "html.parser")
        header_images = []

        for element in soup.find_all(["header", "nav"]):
            for img in element.find_all("img"):
                if src := img.get("src"):
                    header_images.append(urljoin(base_url, src))

        return header_images
```

### 4.2 Create `fede_crawl4ai/processors/ranker.py`
```python
"""Logo ranking logic."""
from typing import List
from ..models import LogoResult


class LogoRanker:
    """Rank and filter logo results."""

    def __init__(self, confidence_threshold: float = 0.8):
        self._threshold = confidence_threshold

    def filter_by_confidence(self, logos: List[LogoResult]) -> List[LogoResult]:
        """Filter logos below confidence threshold."""
        return [logo for logo in logos if logo.confidence >= self._threshold]

    def rank(self, logos: List[LogoResult]) -> List[LogoResult]:
        """Rank logos by score (header > confidence)."""
        def score_logo(logo: LogoResult) -> float:
            score = logo.rank_score
            if logo.is_header:
                score += 0.2  # Boost header logos
            return score

        return sorted(logos, key=score_logo, reverse=True)
```

### 4.3 Tests
```bash
# tests/unit/processors/test_crawler.py
- test_fetch_page_success
- test_fetch_page_404
- test_fetch_page_timeout
- test_extract_images_from_img_tags
- test_extract_images_from_svg
- test_extract_header_images

# tests/unit/processors/test_ranker.py
- test_filter_by_confidence
- test_rank_by_score
- test_rank_header_boost
```

**Lines extracted**: ~300 (from god class)
**Tests**: 9 new tests

---

## Phase 5: Refactor LogoCrawler (Orchestrator)

**Goal**: Reduce LogoCrawler from 1298 lines → ~150 lines

### 5.1 New `fede_crawl4ai/crawler.py`
```python
"""Main LogoCrawler orchestrator (thin wrapper)."""
import logging
from typing import List, Optional
from .config import LogoCrawlerConfig
from .models import LogoResult
from .analyzers.openai_analyzer import OpenAIAnalyzer
from .analyzers.azure_analyzer import AzureOpenAIAnalyzer
from .storage.cache import ImageCache
from .storage.cloud import CloudStorage
from .processors.crawler import CrawlerEngine
from .processors.ranker import LogoRanker
from datetime import timedelta

logger = logging.getLogger(__name__)


class LogoCrawler:
    """Logo detection crawler (orchestrates components)."""

    def __init__(
        self,
        config: Optional[LogoCrawlerConfig] = None,
        analyzer: Optional[ImageAnalyzer] = None,
        cache: Optional[ImageCache] = None,
        storage: Optional[CloudStorage] = None,
        crawler: Optional[CrawlerEngine] = None,
        ranker: Optional[LogoRanker] = None,
        **kwargs,
    ):
        """
        Initialize LogoCrawler with dependency injection.

        Args:
            config: Configuration object (or pass kwargs)
            analyzer: Image analyzer (auto-created if None)
            cache: Cache implementation (auto-created if None)
            storage: Storage provider (auto-created if None)
            crawler: Crawler engine (auto-created if None)
            ranker: Logo ranker (auto-created if None)
            **kwargs: Config parameters (if config is None)
        """
        # Load config
        if config is None:
            config = LogoCrawlerConfig(**kwargs)
        self.config = config

        # Inject or create analyzer
        if analyzer is None:
            if config.use_azure:
                if not config.azure_endpoint:
                    raise ValueError("Azure endpoint required")
                analyzer = AzureOpenAIAnalyzer(
                    api_key=config.api_key,
                    endpoint=config.azure_endpoint,
                    deployment=config.azure_deployment,
                    api_version=config.api_version,
                )
            else:
                analyzer = OpenAIAnalyzer(api_key=config.api_key)
        self._analyzer = analyzer

        # Inject or create other components
        self._cache = cache or ImageCache(ttl=timedelta(days=config.cache_duration_days))
        self._storage = storage or CloudStorage(config.supabase_url, config.supabase_key)
        self._crawler = crawler or CrawlerEngine()
        self._ranker = ranker or LogoRanker(confidence_threshold=config.confidence_threshold)

    async def crawl_website(self, url: str) -> List[LogoResult]:
        """
        Crawl website and detect logos.

        Args:
            url: Website URL to crawl

        Returns:
            List of detected logos, ranked by confidence
        """
        # 1. Fetch page
        html = await self._crawler.fetch_page(url)
        if not html:
            logger.error(f"Failed to fetch {url}")
            return []

        # 2. Extract image URLs
        image_urls = self._crawler.extract_images(html, url)
        header_urls = self._crawler.extract_header_images(html, url)

        logger.info(f"Found {len(image_urls)} images ({len(header_urls)} in header)")

        # 3. Analyze images
        results = []
        for img_url in image_urls:
            # Check cache
            # Download image
            # Analyze with AI
            # Store result
            ...

        # 4. Rank and filter
        filtered = self._ranker.filter_by_confidence(results)
        ranked = self._ranker.rank(filtered)

        return ranked
```

### 5.2 Tests
```bash
# tests/unit/test_crawler.py
- test_init_with_config
- test_init_with_kwargs
- test_init_azure_no_endpoint_raises
- test_dependency_injection_analyzer
- test_dependency_injection_cache
- test_dependency_injection_storage
- test_crawl_website_integration (with mocks)

# tests/integration/test_crawler_e2e.py
- test_crawl_real_website (with mocked OpenAI)
- test_crawl_caching
- test_crawl_ranking
```

**Lines in crawler.py**: ~150 (down from 1298)
**Tests**: 10 new tests

---

## Summary

### Before (v0.2.0)
- 1 god class: 1298 lines, 23 methods
- Test coverage: 22%
- No dependency injection
- ~100 lines duplicated
- Violates SOLID

### After (v0.3.0)
- 12 focused modules: <300 lines each
- Test coverage: >80%
- Full dependency injection
- Zero duplication
- Follows SOLID

### Migration Path

**Breaking Changes:**
```python
# v0.2.0
from fede_crawl4ai import LogoCrawler
crawler = LogoCrawler(api_key="...")

# v0.3.0 - SAME API (backward compatible)
from fede_crawl4ai import LogoCrawler
crawler = LogoCrawler(api_key="...")

# v0.3.0 - Advanced (with DI)
from fede_crawl4ai import LogoCrawler
from fede_crawl4ai.analyzers import OpenAIAnalyzer
from fede_crawl4ai.storage import ImageCache

analyzer = OpenAIAnalyzer(api_key="...")
cache = ImageCache(ttl=timedelta(hours=1))
crawler = LogoCrawler(analyzer=analyzer, cache=cache)
```

**Backward Compatibility:**
- Public API unchanged (crawl_website, etc.)
- Old imports still work
- Config params identical

---

## Execution Plan

### Iteration 1: Models & Protocols (1 day)
- Create models.py
- Create protocols.py
- Write tests
- **Deliverable**: Type-safe interfaces

### Iteration 2: Analyzers (2 days)
- Extract BaseOpenAIAnalyzer
- Create OpenAIAnalyzer
- Create AzureOpenAIAnalyzer
- Write 11 tests
- **Deliverable**: DRY, testable analyzers

### Iteration 3: Storage (1 day)
- Extract ImageCache
- Extract CloudStorage
- Write 8 tests
- **Deliverable**: Mockable storage

### Iteration 4: Processors (2 days)
- Extract CrawlerEngine
- Extract LogoRanker
- Create CSVProcessor
- Write 9 tests
- **Deliverable**: Independent processors

### Iteration 5: Refactor LogoCrawler (2 days)
- Add dependency injection
- Reduce to thin orchestrator
- Write integration tests
- Update documentation
- **Deliverable**: Clean architecture

**Total**: ~8 days of focused work

---

## Success Metrics

- [ ] Test coverage >80%
- [ ] All files <300 lines
- [ ] All classes <10 methods
- [ ] Zero code duplication
- [ ] All SOLID principles followed
- [ ] Backward compatible API
- [ ] CI passes (lint, format, tests)
- [ ] Documentation updated

---

## Risk Mitigation

**Risk**: Breaking existing code
**Mitigation**: Keep old API, add new exports gradually

**Risk**: Tests take too long
**Mitigation**: Write unit tests first (fast), integration tests last

**Risk**: Over-engineering
**Mitigation**: Stick to KISS, only extract what's necessary

**Risk**: Losing functionality
**Mitigation**: Every extracted method gets a test proving it works
