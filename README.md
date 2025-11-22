# crawl4logo

A web crawler for logo detection using gpt-4o-mini. This tool crawls websites and identifies logos using Azure OpenAI's vision capabilities.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/federicodeponte/crawl4logo/workflows/Tests/badge.svg)](https://github.com/federicodeponte/crawl4logo/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

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

## Prerequisites

Before using this tool, you need:

1. **OpenAI API Key**: Get your API key from:
   - **Regular OpenAI**: [OpenAI Platform](https://platform.openai.com/) (recommended for most users)
   - **Azure OpenAI**: [Azure Portal](https://portal.azure.com/)
2. **System Dependencies**: Install Cairo as described in the Installation section above

## Usage

```python
from fede_crawl4ai import LogoCrawler

# Create a crawler instance with your OpenAI API key
crawler = LogoCrawler(api_key="your_openai_api_key_here")

# For Azure OpenAI, use:
# crawler = LogoCrawler(api_key="your_azure_api_key_here", use_azure=True)

# Crawl a website for logos
results = await crawler.crawl_website("https://example.com")

# Results are saved to results.json
```

**Important**: You must provide your own OpenAI API key. The tool will not work without it.

## Configuration

### Environment Variables (Optional)
You can also set your API key as an environment variable:
```bash
# For regular OpenAI
export OPENAI_API_KEY="your_api_key_here"

# For Azure OpenAI
export AZURE_OPENAI_API_KEY="your_api_key_here"
```

Then use it in your code:
```python
import os

# For regular OpenAI (default)
crawler = LogoCrawler(api_key=os.getenv("OPENAI_API_KEY"))

# For Azure OpenAI
crawler = LogoCrawler(api_key=os.getenv("AZURE_OPENAI_API_KEY"), use_azure=True)
```

## Output Format

The tool generates a JSON file containing:
- Image URL
- Confidence score
- Logo description
- Source page URL
- Image hash
- Timestamp
- Rank score
- Detection scores (if available)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
