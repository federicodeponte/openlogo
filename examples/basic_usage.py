"""
Basic usage example for openlogo.

Prerequisites:
1. Install: pip install -e .
2. Set environment variable: export OPENAI_API_KEY="your_key"
3. System dep: brew install cairo (macOS) or apt install libcairo2-dev (Linux)
"""

import asyncio
import os
from openlogo import LogoCrawler


async def main():
    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: Set OPENAI_API_KEY environment variable")
        return

    # Create crawler
    crawler = LogoCrawler(api_key=api_key)

    # Crawl a website
    url = "https://stripe.com"
    print(f"Crawling {url} for logos...")
    
    results = await crawler.crawl_website(url)

    # Print results
    print(f"\nFound {len(results)} logo(s):\n")
    for i, logo in enumerate(results, 1):
        print(f"{i}. {logo.url}")
        print(f"   Confidence: {logo.confidence:.0f}%")
        print(f"   Description: {logo.description[:80]}...")
        print()


if __name__ == "__main__":
    asyncio.run(main())


