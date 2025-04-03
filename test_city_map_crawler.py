import asyncio
import os
import sys
import json
import ssl
import aiohttp
import chardet
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import random
import time
from typing import List, Optional, Dict, Set
from pydantic import BaseModel
import re

print("Script started")  # Debug output

# Add the current directory to the Python path
current_dir = Path(__file__).parent.absolute()
print(f"Current directory: {current_dir}")
print(f"Current working directory: {os.getcwd()}")
sys.path.append(str(current_dir))

# Configure SSL context to be more permissive
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Browser-like headers with German language preference
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1'
}

class LogoResult(BaseModel):
    url: str
    alt_text: str
    title: str
    class_name: str
    id: str
    src_attribute: str
    dimensions: Dict[str, int]
    location: str
    page_url: str
    parent_classes: List[str] = []
    parent_ids: List[str] = []

def print_element_tree(element, indent=0):
    """Print the HTML element tree structure."""
    if hasattr(element, 'name') and element.name:
        attrs = []
        if element.get('class'):
            attrs.append(f"class='{' '.join(element.get('class'))}'")
        if element.get('id'):
            attrs.append(f"id='{element.get('id')}'")
        if element.name == 'img':
            if element.get('src'):
                attrs.append(f"src='{element.get('src')}'")
            if element.get('alt'):
                attrs.append(f"alt='{element.get('alt')}'")
        
        attr_str = ' ' + ' '.join(attrs) if attrs else ''
        print('  ' * indent + f"<{element.name}{attr_str}>")
        
        for child in element.children:
            if not isinstance(child, str) or child.strip():
                print_element_tree(child, indent + 1)

async def decode_response(response: aiohttp.ClientResponse) -> str:
    """Decode response content using appropriate encoding."""
    content = await response.read()
    encoding_result = chardet.detect(content)
    print(f"Detected encoding: {encoding_result}")
    
    encodings = [
        encoding_result['encoding'],
        'iso-8859-1',
        'windows-1252',
        'utf-8',
        'latin1'
    ]
    
    for encoding in encodings:
        if not encoding:
            continue
        try:
            text = content.decode(encoding)
            print(f"Successfully decoded content using {encoding} encoding")
            return text
        except UnicodeDecodeError:
            print(f"Failed to decode with {encoding}")
            continue
    
    raise UnicodeDecodeError("Failed to decode content with any encoding")

async def get_page_with_retry(session: aiohttp.ClientSession, url: str, max_retries: int = 3) -> Optional[str]:
    """Get page content with retry logic and random delays."""
    for attempt in range(max_retries):
        try:
            # Add random delay between attempts
            if attempt > 0:
                delay = random.uniform(2, 5)
                print(f"Waiting {delay:.2f} seconds before retry...")
                await asyncio.sleep(delay)
            
            print(f"Attempting to fetch {url} (attempt {attempt + 1}/{max_retries})...")
            async with session.get(url) as response:
                print(f"Response status: {response.status}")
                if response.status == 200:
                    return await decode_response(response)
                elif response.status == 429:  # Too Many Requests
                    print("Rate limited, waiting longer...")
                    await asyncio.sleep(10)  # Wait longer for rate limit
                else:
                    print(f"Unexpected status code: {response.status}")
        except Exception as e:
            print(f"Error during fetch: {str(e)}")
            if attempt == max_retries - 1:
                raise
    return None

def get_parent_info(element) -> tuple[List[str], List[str]]:
    """Get class and id information from parent elements."""
    parent_classes = []
    parent_ids = []
    parent = element.parent
    
    while parent and parent.name:
        if parent.get('class'):
            parent_classes.extend(parent.get('class'))
        if parent.get('id'):
            parent_ids.append(parent.get('id'))
        parent = parent.parent
    
    return parent_classes, parent_ids

def parse_dimension(value: str) -> int:
    """Parse dimension value that might include CSS units."""
    if not value:
        return 0
    try:
        # Try to convert directly to int first
        return int(value)
    except (ValueError, TypeError):
        # If that fails, try to extract the number from strings like '16px'
        match = re.search(r'(\d+)', str(value))
        if match:
            return int(match.group(1))
        return 0

def extract_logo_info(img_tag, page_url: str, location: str = "unknown") -> LogoResult:
    """Extract relevant information from an image tag."""
    parent_classes, parent_ids = get_parent_info(img_tag)
    
    # Parse dimensions, handling CSS units
    width = parse_dimension(img_tag.get('width', 0))
    height = parse_dimension(img_tag.get('height', 0))
    
    # If dimensions are not in attributes, try to get from style
    if not (width and height) and img_tag.get('style'):
        style = img_tag.get('style', '')
        width_match = re.search(r'width:\s*(\d+)px', style)
        height_match = re.search(r'height:\s*(\d+)px', style)
        if width_match:
            width = int(width_match.group(1))
        if height_match:
            height = int(height_match.group(1))
    
    return LogoResult(
        url=urljoin(page_url, img_tag.get('src', '')),
        alt_text=img_tag.get('alt', ''),
        title=img_tag.get('title', ''),
        class_name=str(img_tag.get('class', [])),
        id=img_tag.get('id', ''),
        src_attribute=img_tag.get('src', ''),
        dimensions={
            'width': width,
            'height': height
        },
        location=location,
        page_url=page_url,
        parent_classes=parent_classes,
        parent_ids=parent_ids
    )

async def find_logos(html_content: str, page_url: str) -> List[LogoResult]:
    """Find potential logos in the HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    logos = []
    
    print("\nAnalyzing HTML structure:")
    print_element_tree(soup.body if soup.body else soup)
    
    # Look for images in the header or elements with header-like classes
    header_elements = []
    header = soup.find('header')
    if header:
        header_elements.append(('header', header))
    
    # Find elements with header-like classes or IDs
    header_classes = soup.find_all(class_=lambda x: x and any(term in x.lower() for term in ['header', 'top', 'nav', 'logo']))
    for elem in header_classes:
        header_elements.append(('header-class', elem))
    
    # Process header elements
    for location_type, elem in header_elements:
        print(f"\nChecking {location_type} element:")
        print_element_tree(elem)
        for img in elem.find_all('img'):
            print(f"\nFound image in {location_type}:")
            print(f"src: {img.get('src')}")
            print(f"alt: {img.get('alt')}")
            print(f"class: {img.get('class')}")
            logos.append(extract_logo_info(img, page_url, location_type))
    
    # Look for images with logo-related attributes
    logo_keywords = ['logo', 'brand', 'city-map', 'citymap']
    for img in soup.find_all('img'):
        # Check various attributes for logo keywords
        img_text = ' '.join([
            str(img.get('class', '')),
            str(img.get('id', '')),
            str(img.get('alt', '')),
            str(img.get('src', '')),
            str(img.get('title', ''))
        ]).lower()
        
        if any(keyword in img_text for keyword in logo_keywords):
            print(f"\nFound potential logo image:")
            print(f"src: {img.get('src')}")
            print(f"alt: {img.get('alt')}")
            print(f"class: {img.get('class')}")
            logos.append(extract_logo_info(img, page_url, "content"))
    
    # Look for SVG elements that might be logos
    for svg in soup.find_all('svg'):
        svg_text = ' '.join([
            str(svg.get('class', '')),
            str(svg.get('id', '')),
            str(svg.get('aria-label', ''))
        ]).lower()
        
        if any(keyword in svg_text for keyword in logo_keywords):
            print(f"\nFound potential SVG logo:")
            print_element_tree(svg)
    
    return logos

async def main():
    print("Script started")
    print(f"Current directory: {os.getcwd()}")
    
    # URLs to try
    urls = [
        "https://city-map.de",
        "http://city-map.de",
        "https://www.city-map.de",
        "http://www.city-map.de"
    ]
    
    timeout = aiohttp.ClientTimeout(total=30)
    conn = aiohttp.TCPConnector(ssl=ssl_context, force_close=True)
    
    async with aiohttp.ClientSession(headers=headers, timeout=timeout, connector=conn) as session:
        all_logos = []
        
        for url in urls:
            try:
                print(f"\nTrying URL: {url}")
                html_content = await get_page_with_retry(session, url)
                if html_content:
                    print("Successfully retrieved page content")
                    logos = await find_logos(html_content, url)
                    print(f"Found {len(logos)} potential logos")
                    all_logos.extend(logos)
                    break  # Stop if we successfully process one URL
            except Exception as e:
                print(f"Error processing {url}: {str(e)}")
                continue
        
        if not all_logos:
            print("\nNo logos found on any URL variant")
            return
        
        # Convert results to JSON-compatible format
        results = []
        for logo in all_logos:
            result = logo.dict()
            result['timestamp'] = datetime.now().isoformat()
            results.append(result)
        
        # Save results
        print("\nPreparing to save results...")
        json_data = json.dumps(results, indent=2, ensure_ascii=False)
        print(f"JSON data length: {len(json_data)} bytes")
        
        print("Writing to file: results_city_map.json")
        try:
            with open("results_city_map.json", "w", encoding='utf-8') as f:
                f.write(json_data)
            print("Results saved successfully to results_city_map.json")
        except Exception as e:
            print(f"Error saving results: {str(e)}")
        
        # Print summary
        print("\nResults Summary:")
        print(f"Total potential logos found: {len(results)}")
        print("\nLogo details:")
        for i, logo in enumerate(results, 1):
            print(f"\n{i}. Logo in {logo['location']}")
            print(f"URL: {logo['url']}")
            print(f"Alt text: {logo['alt_text']}")
            print(f"Title: {logo['title']}")
            print(f"Dimensions: {logo['dimensions']}")
            print(f"Parent classes: {logo['parent_classes']}")
            print(f"Parent IDs: {logo['parent_ids']}")
            print("-" * 50)
    
    print("\nScript completed")

if __name__ == "__main__":
    print("Starting main...")  # Debug output
    asyncio.run(main())
    print("Script completed")  # Debug output 