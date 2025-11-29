# crawl4logo

A web crawler for logo detection using GPT-4o-mini vision. Crawls websites and identifies logos with confidence scores.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔍 Async web crawling with browser-like headers
- 🤖 Logo detection using GPT-4o-mini vision
- 🖼️ SVG to PNG conversion
- 📊 Confidence scores and descriptions
- 💾 Image caching

## Installation

### System Dependencies

```bash
# macOS
brew install cairo

# Ubuntu/Debian
sudo apt-get install libcairo2-dev
```

### Python Package

```bash
pip install -e .

# With optional dependencies
pip install -e ".[ai]"      # OpenAI client
pip install -e ".[all]"     # All optional deps
```

## Quick Start

```python
import asyncio
from crawl4logo import LogoCrawler

async def main():
    crawler = LogoCrawler(api_key="your_openai_api_key")
    results = await crawler.crawl_website("https://example.com")
    
    for logo in results:
        print(f"{logo.url} - {logo.confidence}% confidence")

asyncio.run(main())
```

## Project Structure

```
crawl4logo/
├── src/
│   └── crawl4logo/
│       ├── __init__.py
│       ├── crawler.py      # Main LogoCrawler class
│       └── detection.py    # Logo detection strategies
├── tests/
├── examples/
├── pyproject.toml
└── README.md
```

## Environment Variables

```bash
export OPENAI_API_KEY="your_api_key"

# For Azure OpenAI
export AZURE_OPENAI_API_KEY="your_api_key"
```

## Output Format

```json
{
  "url": "https://example.com/logo.png",
  "confidence": 95,
  "description": "Company logo with blue text",
  "source_page": "https://example.com",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## License

MIT License - see [LICENSE](LICENSE)
