import asyncio
import os
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
import hashlib
from datetime import datetime, timedelta
import urllib.request
import json
import ssl
import base64
import cairosvg
import io
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup
from PIL import Image
from pydantic import BaseModel
import re
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

def allowSelfSignedHttps(allowed):
    if allowed and not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):
        ssl._create_default_https_context = ssl._create_unverified_context

allowSelfSignedHttps(True)

class LogoResult(BaseModel):
    url: str
    confidence: float
    description: str
    page_url: str
    image_hash: str
    timestamp: datetime
    is_header: bool = False  # New field to track if logo is from header/nav
    rank_score: float = 0.0  # New field for the ranking score

class ImageCache:
    def __init__(self, cache_duration: timedelta = timedelta(days=1)):
        self.cache: Dict[str, LogoResult] = {}
        self.cache_duration = cache_duration

    def get(self, image_hash: str) -> Optional[LogoResult]:
        if image_hash in self.cache:
            result = self.cache[image_hash]
            if datetime.now() - result.timestamp < self.cache_duration:
                return result
        return None

    def set(self, image_hash: str, result: LogoResult):
        self.cache[image_hash] = result

class LogoCrawler:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or "COIEsidMCl1pXiM33rWGJTNeF2fyheRJXc9FaYFqCEidCYwQPGaHJQQJ99BAACPV0roXJ3w3AAABACOGB3cH"
        if not self.api_key:
            raise ValueError("API key is required")
        
        # Initialize image cache
        self.image_cache = ImageCache()
        
        # Minimum image dimensions
        self.min_width = 32
        self.min_height = 32
        
    def get_image_hash(self, image_data: bytes) -> str:
        """Generate a hash for an image to use as cache key."""
        return hashlib.md5(image_data).hexdigest()
        
    def is_valid_image_size(self, image: Image.Image) -> bool:
        """Check if image dimensions are suitable for logo detection."""
        width, height = image.size
        return width >= self.min_width and height >= self.min_height

    def extract_confidence_score(self, content: str) -> float:
        """Extract confidence score from gpt-4o-mini response using various patterns."""
        # Try different patterns to find confidence score
        patterns = [
            r"confidence score:\s*(\d*\.?\d+)",  # "Confidence Score: 0.9"
            r"confidence:\s*(\d*\.?\d+)",        # "Confidence: 0.9"
            r"^(\d*\.?\d+),\s*",                # "0.9, This image..."
            r"^(\d*\.?\d+)\s*-\s*",             # "0.95 - The image..."
            r"^(\d*\.?\d+)$",                    # Just a number
        ]
        
        # First, try to find the confidence score in a dedicated line
        lines = content.split('\n')
        for line in lines:
            line = line.lower().strip()
            if line.startswith(('confidence:', 'confidence score:')):
                try:
                    score = float(re.search(r"(\d*\.?\d+)", line).group(1))
                    return score
                except (ValueError, AttributeError):
                    continue
        
        # Then try the patterns on the entire content
        content_lower = content.lower()
        for pattern in patterns:
            match = re.search(pattern, content_lower)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return 0.0

    def extract_description(self, content: str) -> str:
        """Extract description from gpt-4o-mini response."""
        # Try to find description after "Description:" marker
        if "description:" in content.lower():
            parts = content.split("Description:", 1)
            if len(parts) > 1:
                return parts[1].strip()
        
        # If no description marker found, remove confidence score if present
        lines = content.split('\n')
        filtered_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith(('confidence:', 'confidence score:')):
                continue
            filtered_lines.append(line)
        
        return ' '.join(filtered_lines)

    async def analyze_image_with_azure(self, image_base64: str, image_url: str, page_url: str) -> Optional[LogoResult]:
        """Analyze an image using Azure OpenAI gpt-4o-mini."""
        url = "https://scailetech.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions?api-version=2023-03-15-preview"
        
        messages = [
            {"role": "system", "content": "You are a logo detection assistant. Analyze the image and determine if it's a logo. If it is, provide a confidence score (0-1) and description in this format: 'Confidence Score: X.XX\nDescription: ...'. If not, return 'null'."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Is this image a logo? If yes, provide a confidence score (0-1) and a brief description of what makes it a logo. Format your response as 'Confidence Score: X.XX\nDescription: ...'. If no, return null."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]

        data = {
            "messages": messages,
            "max_tokens": 300
        }

        headers = {
            'Content-Type': 'application/json',
            'api-key': self.api_key
        }

        try:
            print(f"\nAnalyzing image: {image_url}")
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"API Error ({response.status}): {error_text}")
                        return None
                    
                    try:
                        result = await response.json()
                        print(f"API Response: {json.dumps(result, indent=2)}")
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON response: {e}")
                        response_text = await response.text()
                        print(f"Raw response: {response_text}")
                        return None
                    
                    if not result.get('choices'):
                        print(f"Warning: No 'choices' in API response")
                        return None
                    
                    if not result['choices']:
                        print(f"Warning: Empty 'choices' array in API response")
                        return None
                    
                    if not result['choices'][0].get('message'):
                        print(f"Warning: No 'message' in first choice")
                        return None
                    
                    if not result['choices'][0]['message'].get('content'):
                        print(f"Warning: No 'content' in message")
                        return None
                    
                    content = result['choices'][0]['message']['content']
                    print(f"Content from API: {content}")
                    
                    if content.lower() == "null":
                        print("Content is 'null', skipping image")
                        return None
                    
                    # Extract confidence score using the new method
                    confidence = self.extract_confidence_score(content)
                    print(f"Extracted confidence score: {confidence}")
                    
                    # Extract description using the new method
                    description = self.extract_description(content)
                    print(f"Extracted description: {description}")
                    
                    return LogoResult(
                        url=image_url,
                        confidence=confidence,
                        description=description,
                        page_url=page_url,
                        image_hash=self.get_image_hash(image_base64.encode()),
                        timestamp=datetime.now()
                    )
            
        except aiohttp.ClientError as e:
            print(f"HTTP Error analyzing image {image_url}: {e}")
            return None
        except Exception as e:
            print(f"Error analyzing image {image_url}: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            return None
        
    async def analyze_image(self, image_url: str, page_url: str) -> Optional[LogoResult]:
        """Analyze an image using gpt-4o-mini to determine if it's a logo."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        return None
                    
                    image_data = await response.read()
                    image_hash = self.get_image_hash(image_data)
                    
                    # Check cache first
                    cached_result = self.image_cache.get(image_hash)
                    if cached_result:
                        return cached_result
                    
                    # Handle SVG files
                    if image_url.lower().endswith('.svg'):
                        try:
                            # Convert SVG to PNG using cairosvg
                            png_data = cairosvg.svg2png(bytestring=image_data)
                            image = Image.open(io.BytesIO(png_data))
                        except Exception as e:
                            print(f"Error converting SVG {image_url}: {e}")
                            return None
                    else:
                        image = Image.open(io.BytesIO(image_data))
                    
                    # Skip if image is too small
                    if not self.is_valid_image_size(image):
                        return None
                    
                    buffered = io.BytesIO()
                    image.save(buffered, format="PNG")
                    image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    # Analyze with Azure OpenAI
                    result = await self.analyze_image_with_azure(image_base64, image_url, page_url)
                    
                    if result:
                        # Cache the result
                        self.image_cache.set(image_hash, result)
                    
                    return result
                        
        except Exception as e:
            print(f"Error analyzing image {image_url}: {e}")
            return None
    
    def extract_background_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract background images from CSS."""
        background_images = []
        
        # Look for style attributes
        for element in soup.find_all(style=True):
            style = element['style']
            matches = re.findall(r"background-image:\s*url\((.*?)\)", style)
            background_images.extend(matches)
            
        # Look for background-image in style tags
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                matches = re.findall(r"background-image:\s*url\((.*?)\)", style_tag.string)
                background_images.extend(matches)
                
        return background_images
    
    async def crawl_for_logos(self, start_url: str, max_pages: int = 10, output_file: Optional[str] = None) -> List[LogoResult]:
        """Crawl a website and analyze images to find logos."""
        logo_results = []
        processed_images = set()
        processed_urls = set()
        
        async def process_page(url: str):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            return
                        
                        content = await response.text()
                        
                        # Parse HTML
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Find all images
                        images = soup.find_all('img')
                        
                        # Get background images
                        background_images = self.extract_background_images(soup)
                        
                        # Combine all image URLs
                        all_image_urls = []
                        
                        # Add img tag sources
                        for img in images:
                            img_url = img.get('src')
                            if img_url:
                                all_image_urls.append(urljoin(url, img_url))
                        
                        # Add background images
                        for bg_url in background_images:
                            all_image_urls.append(urljoin(url, bg_url))
                        
                        # Analyze each image
                        for img_url in all_image_urls:
                            if img_url in processed_images:
                                continue
                                
                            processed_images.add(img_url)
                            
                            # Skip non-image URLs
                            if not any(img_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg']):
                                continue
                            
                            # Analyze image
                            result = await self.analyze_image(img_url, url)
                            if result:
                                logo_results.append(result)
                        
                        # Find all links for further crawling
                        links = soup.find_all('a')
                        base_domain = urlparse(start_url).netloc
                        
                        for link in links:
                            href = link.get('href')
                            if href:
                                absolute_url = urljoin(url, href)
                                if (
                                    urlparse(absolute_url).netloc == base_domain
                                    and absolute_url not in processed_urls
                                    and len(processed_urls) < max_pages
                                ):
                                    processed_urls.add(absolute_url)
                                    await process_page(absolute_url)
                
            except Exception as e:
                print(f"Error processing page {url}: {e}")
        
        # Start crawling from the initial URL
        processed_urls.add(start_url)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task("Crawling pages...", total=max_pages)
            await process_page(start_url)
            progress.update(task, completed=len(processed_urls))
        
        # Sort results by confidence
        logo_results.sort(key=lambda x: x.confidence, reverse=True)
        
        # Save results to file if output_file is specified
        if output_file:
            try:
                print(f"\nPreparing to save results...")
                print(f"Output file path: {output_file}")
                
                # Convert results to dict format
                results_dict = []
                for result in logo_results:
                    result_dict = {
                        "url": result.url,
                        "confidence": result.confidence,
                        "description": result.description,
                        "page_url": result.page_url,
                        "image_hash": result.image_hash,
                        "timestamp": result.timestamp.isoformat()
                    }
                    results_dict.append(result_dict)
                
                print(f"Converted {len(results_dict)} results to JSON format")
                
                # Create output directory if needed
                output_path = Path(output_file)
                if output_path.parent != Path('.'):
                    print(f"Creating directory: {output_path.parent}")
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save to file
                print(f"Writing results to file: {output_path}")
                json_data = json.dumps(results_dict, indent=2)
                print(f"JSON data length: {len(json_data)} bytes")
                
                with open(output_path, 'w') as f:
                    f.write(json_data)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data is written to disk
                
                # Verify file was written
                if output_path.exists():
                    print(f"File exists after writing: {output_path}")
                    print(f"File size: {output_path.stat().st_size} bytes")
                else:
                    print(f"Warning: File does not exist after writing: {output_path}")
                
            except Exception as e:
                print(f"Error saving results to file: {e}")
                import traceback
                traceback.print_exc()
        
        return logo_results 

    async def analyze_header_nav_elements(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract image URLs from header and navigation elements."""
        header_selectors = [
            'header', 
            'nav',
            '[role="banner"]',
            '.header',
            '.nav',
            '#header',
            '#nav',
            '.navbar',
            '.site-header',
            '.main-header'
        ]
        
        header_images = set()
        for selector in header_selectors:
            elements = soup.select(selector)
            for element in elements:
                # Find all images in this header/nav element
                for img in element.find_all('img'):
                    src = img.get('src')
                    if src:
                        full_url = urljoin(base_url, src)
                        header_images.add(full_url)
                        
                # Find all SVG elements
                for svg in element.find_all('svg'):
                    # If SVG has an image
                    for image in svg.find_all('image'):
                        href = image.get('href') or image.get('xlink:href')
                        if href:
                            full_url = urljoin(base_url, href)
                            header_images.add(full_url)
        
        return list(header_images)

    async def rank_logos(self, logos: List[LogoResult]) -> List[LogoResult]:
        """Use gpt-4o-mini to rank logos based on confidence and description."""
        if not logos:
            return []

        url = "https://scailetech.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions?api-version=2023-03-15-preview"
        
        # Prepare the prompt with all logo information
        logo_descriptions = []
        for i, logo in enumerate(logos, 1):
            location = "header/navigation" if logo.is_header else "main content"
            logo_descriptions.append(f"Logo {i}:\n- Location: {location}\n- Confidence: {logo.confidence}\n- Description: {logo.description}")
        
        messages = [
            {
                "role": "system",
                "content": "You are a logo ranking assistant. Analyze the provided logos and rank them based on their likelihood of being the main company logo. Consider:\n1. Location (header/nav logos are more likely)\n2. Confidence score\n3. Description (looking for company name, branding elements)\n4. Professional design indicators"
            },
            {
                "role": "user",
                "content": f"Rank these logos from most to least likely to be the main company logo. For each logo, provide a score from 0-1 and brief explanation:\n\n{chr(10).join(logo_descriptions)}"
            }
        ]

        data = {
            "messages": messages,
            "max_tokens": 500
        }

        headers = {
            'Content-Type': 'application/json',
            'api-key': self.api_key
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status != 200:
                        print(f"Error ranking logos: {await response.text()}")
                        return logos

                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    # Extract ranking scores using regex
                    for i, logo in enumerate(logos, 1):
                        pattern = f"Logo {i}.*?score:?\s*(\d*\.?\d+)"
                        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                        if match:
                            try:
                                logo.rank_score = float(match.group(1))
                            except ValueError:
                                logo.rank_score = 0.0
                        
                    # Sort logos by rank_score in descending order
                    return sorted(logos, key=lambda x: x.rank_score, reverse=True)

        except Exception as e:
            print(f"Error during logo ranking: {e}")
            return logos

    async def crawl_website(self, url: str) -> List[LogoResult]:
        """Crawl a website and find logos."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # First, get header/nav images
                    header_images = await self.analyze_header_nav_elements(soup, url)
                    
                    # Then get all other images
                    all_images = set()
                    for img in soup.find_all('img'):
                        src = img.get('src')
                        if src:
                            full_url = urljoin(url, src)
                            all_images.add(full_url)
                    
                    for svg in soup.find_all('svg'):
                        for image in svg.find_all('image'):
                            href = image.get('href') or image.get('xlink:href')
                            if href:
                                full_url = urljoin(url, href)
                                all_images.add(full_url)
                    
                    # Analyze all images
                    results = []
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TaskProgressColumn()
                    ) as progress:
                        task = progress.add_task("Crawling pages...", total=len(all_images))
                        
                        for image_url in all_images:
                            result = await self.analyze_image(image_url, url)
                            if result:
                                # Mark if image is from header/nav
                                result.is_header = image_url in header_images
                                results.append(result)
                            progress.advance(task)
                    
                    print(f"Crawl completed. Found {len(results)} results\n")
                    
                    if results:
                        # Rank the logos
                        ranked_results = await self.rank_logos(results)
                        
                        print("\nFound logos (ranked by likelihood of being main company logo):\n")
                        for result in ranked_results:
                            location = "header/navigation" if result.is_header else "main content"
                            print(f"URL: {result.url}")
                            print(f"Location: {location}")
                            print(f"Confidence: {result.confidence}")
                            print(f"Rank Score: {result.rank_score}")
                            print(f"Description: {result.description}")
                            print(f"Page URL: {result.page_url}")
                            print("-" * 50 + "\n")
                        
                        return ranked_results
                    
                    return []
                    
        except aiohttp.ClientError as e:
            print(f"Error crawling website: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error: {e}")
            return [] 