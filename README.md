# openlogo

A web crawler for logo detection using GPT-4o-mini vision. Uses a **three-tier fallback system**: Clearbit API → Google Favicon → AI-powered crawling.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- ⚡ **Clearbit API priority** - Instant high-quality logos for established companies (free, ~100ms)
- 🔄 **Google Favicon fallback** - Good coverage for sites not in Clearbit (~100ms)
- 🤖 **AI-powered crawling** - GPT-4o-mini vision for complete coverage (slower)
- 🔍 Async web crawling with browser-like headers (avoids 403 blocks)
- 🔄 Meta refresh redirect support (follows `<meta http-equiv="refresh">` redirects)
- 🖼️ SVG to PNG conversion
- 📊 Confidence scores and descriptions
- 💾 Image caching
- 🎯 Header/nav logo prioritization

## Logo Resolution Order

1. **Clearbit** (confidence: 0.95) - Best quality, ~100ms, covers most established companies
2. **Google Favicon** (confidence: 0.75) - Good coverage, ~100ms, 128px icons
3. **AI Crawler** (confidence: varies) - Complete coverage, slower, uses GPT-4o-mini

## Installation

### System Dependencies

```bash
# macOS
brew install cairo tesseract

# Ubuntu/Debian
sudo apt-get install libcairo2-dev tesseract-ocr libmagic1
```

### Python Package

```bash
# From PyPI
pip install openlogo

# Basic install (from source)
pip install -e .

# With AI client (OpenAI)
pip install -e ".[ai]"

# With all optional deps
pip install -e ".[all]"

# For development
pip install -e ".[dev]"
```

## Quick Start

```python
import asyncio
import os
from openlogo import LogoCrawler

async def main():
    crawler = LogoCrawler(api_key=os.environ["OPENAI_API_KEY"])
    results = await crawler.crawl_website("https://stripe.com")

    for logo in results:
        print(f"{logo.url} - {logo.confidence:.0f}% confidence")

asyncio.run(main())
```

See `examples/basic_usage.py` for a complete example.

## Project Structure

```
openlogo/
├── src/
│   └── openlogo/
│       ├── __init__.py
│       ├── crawler.py      # Main LogoCrawler class
│       └── detection.py    # Logo detection strategies
├── tests/
│   ├── conftest.py
│   └── test_logo_crawler.py
├── examples/
│   └── basic_usage.py
├── pyproject.toml
└── README.md
```

## Environment Variables

```bash
# Required
export OPENAI_API_KEY="your_api_key"

# Optional: Azure OpenAI
export AZURE_OPENAI_API_KEY="your_api_key"

# Optional: Custom tesseract path
export TESSERACT_CMD="/path/to/tesseract"
```

## Output Format

```python
LogoResult(
    url="https://example.com/logo.png",
    confidence=95.0,
    description="Company logo with blue text",
    page_url="https://example.com",
    image_hash="abc123...",
    timestamp=datetime(...),
    is_header=True,
    rank_score=0.95,
    detection_scores={...}
)
```

## Changelog

### v0.5.0
- **Google Favicon fallback** - Added `try_google_favicon()` as middle-tier between Clearbit and AI crawler
- Three-tier resolution: Clearbit → Google Favicon → AI Crawler
- Added `skip_google_favicon` parameter to `crawl_website()`
- Exported `try_google_favicon()` for direct use
- Skips generic Google globe icons (< 1KB)

### v0.4.0
- **Clearbit API priority** - Now tries Clearbit first for instant logos (~100ms, free)
- Falls back to GPT-4o-mini crawler only when Clearbit returns 404
- Added `skip_clearbit` parameter to `crawl_website()` for forcing crawler mode
- Exported `try_clearbit_logo()` for direct use

### v0.3.0
- Renamed package from `crawl4logo` to `openlogo`
- Added meta refresh redirect support (handles sites that use `<meta http-equiv="refresh">` instead of HTTP redirects)

### v0.2.0
- Initial public release

## License

MIT License - see [LICENSE](LICENSE)
