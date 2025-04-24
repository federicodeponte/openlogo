# crawl4logo

A web crawler for logo detection using gpt-4o-mini. This tool crawls websites and identifies logos using Azure OpenAI's vision capabilities.

## Features

- Web crawling with async support
- Logo detection using gpt-4o-mini
- SVG to PNG conversion
- Image caching
- Confidence score extraction
- Detailed logo descriptions
- JSON output format

## Installation

### System Dependencies

Before installing the Python package, you need to install some system dependencies:

#### macOS
```bash
brew install cairo
```

#### Ubuntu/Debian
```bash
sudo apt-get install libcairo2-dev
```

#### Windows
Download and install Cairo from: https://www.cairographics.org/download/

### Python Package
```bash
pip install -e .
```

## Usage

```python
from fede_crawl4ai import LogoCrawler

# Create a crawler instance
crawler = LogoCrawler()

# Crawl a website for logos
results = await crawler.crawl_website("https://example.com")

# Results are saved to results.json
```

## Output Format

The tool generates a JSON file containing:
- Image URL
- Confidence score
- Logo description
- Source page URL
- Image hash
- Timestamp
