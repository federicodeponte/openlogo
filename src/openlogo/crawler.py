import asyncio
import os
import csv
from typing import List, Dict, Optional, Set, Tuple
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
from bs4 import BeautifulSoup, Tag
from PIL import Image
from pydantic import BaseModel
import re
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Optional: rembg for background removal
try:
    from rembg import remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    remove = None  # type: ignore

# Optional: supabase for cloud storage
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None  # type: ignore

from .detection import LogoDetectionStrategies, LogoCandidate


async def try_clearbit_logo(domain: str, website_url: str) -> Optional["LogoResult"]:
    """Try to get logo from Clearbit API (free, fast, high quality).
    
    Clearbit provides curated company logos for most established companies.
    Returns None if Clearbit doesn't have the logo (404) or on any error.
    """
    clearbit_url = f"https://logo.clearbit.com/{domain}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(clearbit_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    print(f"✅ Clearbit logo found for {domain}: {clearbit_url}")
                    return LogoResult(
                        url=clearbit_url,
                        confidence=0.95,
                        description="Logo from Clearbit API",
                        page_url=website_url,
                        image_hash=hashlib.md5(clearbit_url.encode()).hexdigest(),
                        timestamp=datetime.now(),
                        is_header=True,
                        rank_score=2.0,
                    )
    except Exception as e:
        print(f"ℹ️  Clearbit unavailable for {domain}: {e}")
    return None


async def try_google_favicon(domain: str, website_url: str, size: int = 128) -> Optional["LogoResult"]:
    """Try to get logo from Google's favicon service (fallback for Clearbit).
    
    Google's favicon service provides favicons for most websites.
    Quality is lower than Clearbit but coverage is much higher.
    Returns None if favicon is not found or is a generic placeholder.
    
    Args:
        domain: The domain to get favicon for (e.g., "example.com")
        website_url: The full website URL for metadata
        size: Icon size (16, 32, 64, 128, 256)
    """
    favicon_url = f"https://www.google.com/s2/favicons?domain={domain}&sz={size}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(favicon_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    # Check if we got actual content (not a generic globe icon)
                    content = await resp.read()
                    content_length = len(content)
                    
                    # Google returns a ~726 byte generic globe icon for unknown domains
                    # Skip if content is too small (likely generic icon)
                    if content_length < 1000:
                        print(f"ℹ️  Google favicon too small for {domain} ({content_length} bytes), likely generic icon")
                        return None
                    
                    print(f"✅ Google favicon found for {domain}: {favicon_url} ({content_length} bytes)")
                    return LogoResult(
                        url=favicon_url,
                        confidence=0.75,  # Lower confidence than Clearbit
                        description="Favicon from Google Favicon Service",
                        page_url=website_url,
                        image_hash=hashlib.md5(content).hexdigest(),
                        timestamp=datetime.now(),
                        is_header=True,
                        rank_score=1.5,  # Lower rank than Clearbit
                    )
    except Exception as e:
        print(f"ℹ️  Google favicon unavailable for {domain}: {e}")
    return None


def extract_meta_refresh_url(html: str, base_url: str) -> Optional[str]:
    """Extract redirect URL from meta http-equiv="refresh" tag.

    Handles patterns like:
    - <meta http-equiv="refresh" content="0; URL=/de-de/">
    - <meta content="0;url=https://example.com" http-equiv="refresh">

    Args:
        html: The HTML content to parse
        base_url: The base URL for resolving relative URLs

    Returns:
        The redirect URL if found, None otherwise
    """
    soup = BeautifulSoup(html, "html.parser")
    meta_refresh = soup.find("meta", attrs={"http-equiv": re.compile(r"refresh", re.I)})

    if meta_refresh:
        content = meta_refresh.get("content", "")
        match = re.search(r"url\s*=\s*([^\s;\"']+)", content, re.IGNORECASE)
        if match:
            redirect_url = match.group(1).strip("'\"")
            if redirect_url.startswith("/"):
                return urljoin(base_url, redirect_url)
            elif not redirect_url.startswith(("http://", "https://")):
                return urljoin(base_url, redirect_url)
            return redirect_url
    return None


# Browser-like headers to avoid 403 blocks from websites
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
}

# Use secure SSL context by default - removed insecure SSL bypass
# If you need to handle self-signed certificates, use proper certificate validation
def create_secure_ssl_context():
    """Create a secure SSL context with proper certificate verification."""
    return ssl.create_default_context()

class LogoResult(BaseModel):
    url: str
    confidence: float
    description: str
    page_url: str
    image_hash: str
    timestamp: datetime
    is_header: bool = False
    rank_score: float = 0.0
    detection_scores: Dict[str, Dict[str, float]] = {}

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

class CloudStorage:
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        """Initialize cloud storage for uploading background-removed images."""
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.client: Optional[Client] = None
        
        if SUPABASE_AVAILABLE and supabase_url and supabase_key:
            try:
                self.client = create_client(supabase_url, supabase_key)
                print("✅ Supabase cloud storage initialized")
            except Exception as e:
                print(f"⚠️  Failed to initialize Supabase: {e}")
                self.client = None
        else:
            print("⚠️  Supabase not configured - images will be stored locally only")
    
    async def upload_image(self, image_data: bytes, filename: str) -> Optional[str]:
        """Upload image to cloud storage and return public URL."""
        if not self.client:
            return None
            
        try:
            # Upload to Supabase storage
            bucket_name = "logo-images"
            file_path = f"background-removed/{filename}"
            
            # Ensure bucket exists (this would need to be created manually in Supabase dashboard)
            result = self.client.storage.from_(bucket_name).upload(
                path=file_path,
                file=image_data,
                file_options={"content-type": "image/png"}
            )
            
            # Get public URL
            public_url = self.client.storage.from_(bucket_name).get_public_url(file_path)
            return public_url
            
        except Exception as e:
            print(f"⚠️  Failed to upload to cloud storage: {e}")
            return None

class LogoCrawler:
    def __init__(self, api_key: Optional[str] = None, twitter_api_key: Optional[str] = None, 
                 use_azure: bool = False, supabase_url: Optional[str] = None, 
                 supabase_key: Optional[str] = None):
        """
        Initialize the LogoCrawler.
        
        Args:
            api_key: OpenAI API key (Azure or regular). Required for logo detection.
                     - For Azure OpenAI: Get your API key from https://portal.azure.com/
                     - For regular OpenAI: Get your API key from https://platform.openai.com/
            twitter_api_key: Optional Twitter API key for social media analysis
            use_azure: Set to True if using Azure OpenAI, False for regular OpenAI (default: False)
            supabase_url: Optional Supabase URL for cloud storage of background-removed images
            supabase_key: Optional Supabase key for cloud storage
        """
        if not api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Please provide your API key when initializing LogoCrawler. "
                "Get your API key from: https://platform.openai.com/ (regular) or https://portal.azure.com/ (Azure)"
            )
        self.api_key = api_key
        self.use_azure = use_azure
        
        # Initialize image cache, detection strategies, and cloud storage
        self.image_cache = ImageCache()
        self.detection_strategies = LogoDetectionStrategies(twitter_api_key)
        self.cloud_storage = CloudStorage(supabase_url, supabase_key)
        
        # Minimum image dimensions
        self.min_width = 32
        self.min_height = 32
        
        # Keywords that indicate non-company logos (social media, generic icons, etc.)
        self.non_company_logo_keywords = [
            'facebook', 'twitter', 'x.com', 'instagram', 'linkedin', 'youtube', 'tiktok',
            'social media', 'share', 'like', 'follow', 'icon', 'button', 'arrow',
            'menu', 'hamburger', 'search', 'magnifying glass', 'close', 'x mark',
            'play', 'pause', 'stop', 'volume', 'mute', 'settings', 'gear',
            'user', 'profile', 'account', 'login', 'logout', 'sign in', 'sign up',
            'cart', 'shopping', 'bag', 'heart', 'favorite', 'star', 'rating',
            'tag', 'price', 'discount', 'sale', 'new', 'hot', 'trending'
        ]
        
    def get_image_hash(self, image_data: bytes) -> str:
        """Generate a hash for an image to use as cache key."""
        return hashlib.md5(image_data).hexdigest()
        
    def is_valid_image_size(self, image: Image.Image) -> bool:
        """Check if image dimensions are suitable for logo detection."""
        width, height = image.size
        return width >= self.min_width and height >= self.min_height
    
    def is_company_logo(self, description: str, url: str) -> bool:
        """Check if the logo is likely a company logo (not social media, generic icons, etc.)."""
        if not description:
            return True  # If no description, assume it's a company logo
        
        description_lower = description.lower()
        url_lower = url.lower()
        
        # Check for non-company logo keywords
        for keyword in self.non_company_logo_keywords:
            if keyword in description_lower or keyword in url_lower:
                return False
        
        # Check for social media domains in URL
        social_domains = ['facebook.com', 'twitter.com', 'x.com', 'instagram.com', 
                         'linkedin.com', 'youtube.com', 'tiktok.com']
        for domain in social_domains:
            if domain in url_lower:
                return False
        
        return True

    def remove_background(self, image: Image.Image) -> Image.Image:
        """Remove background from image using rembg."""
        if not REMBG_AVAILABLE:
            return image
        
        try:
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Remove background
            output = remove(img_byte_arr)
            
            # Convert back to PIL image
            return Image.open(io.BytesIO(output))
        except Exception as e:
            print(f"Background removal failed: {e}")
            return image

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

    async def analyze_image_with_openai(self, image_base64: str, image_url: str, page_url: str, html_element: Optional[Tag] = None, page_html: Optional[str] = None) -> Optional[LogoResult]:
        """Analyze an image using OpenAI API (regular or Azure) and additional detection strategies."""
        if self.use_azure:
            return await self._analyze_image_with_azure(image_base64, image_url, page_url, html_element, page_html)
        else:
            return await self._analyze_image_with_regular_openai(image_base64, image_url, page_url, html_element, page_html)

    async def _analyze_image_with_azure(self, image_base64: str, image_url: str, page_url: str, html_element: Optional[Tag] = None, page_html: Optional[str] = None) -> Optional[LogoResult]:
        """Analyze an image using Azure OpenAI gpt-4o-mini and additional detection strategies."""
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
                    
                    # Get additional detection scores
                    detection_scores = {}
                    if html_element and page_html:
                        image_data = base64.b64decode(image_base64)
                        domain = urlparse(page_url).netloc
                        
                        detection_scores['html_context'] = await self.detection_strategies.analyze_html_context(html_element, page_url)
                        detection_scores['structural_position'] = await self.detection_strategies.analyze_structural_position(html_element, [])
                        detection_scores['technical'] = await self.detection_strategies.analyze_image_technical(image_url, image_data)
                        detection_scores['visual'] = await self.detection_strategies.analyze_visual_characteristics(image_data)
                        detection_scores['url_semantics'] = await self.detection_strategies.analyze_url_semantics(image_url)
                        detection_scores['metadata'] = await self.detection_strategies.analyze_metadata(image_data)
                        detection_scores['social_media'] = await self.detection_strategies.analyze_social_media(domain)
                        detection_scores['schema_markup'] = await self.detection_strategies.analyze_schema_markup(page_html)
                        
                        # Calculate rank score
                        rank_score = await self.detection_strategies.get_final_score(detection_scores)
                    else:
                        rank_score = confidence
                    
                    return LogoResult(
                        url=image_url,
                        confidence=confidence,
                        description=description,
                        page_url=page_url,
                        image_hash=self.get_image_hash(image_base64.encode()),
                        timestamp=datetime.now(),
                        rank_score=rank_score,
                        detection_scores=detection_scores
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

    async def _analyze_image_with_regular_openai(self, image_base64: str, image_url: str, page_url: str, html_element: Optional[Tag] = None, page_html: Optional[str] = None) -> Optional[LogoResult]:
        """Analyze an image using regular OpenAI API and additional detection strategies."""
        url = "https://api.openai.com/v1/chat/completions"
        
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
            "model": "gpt-4o-mini",
            "messages": messages,
            "max_tokens": 300
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
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
                    
                    # Get additional detection scores
                    detection_scores = {}
                    if html_element and page_html:
                        image_data = base64.b64decode(image_base64)
                        domain = urlparse(page_url).netloc
                        
                        detection_scores['html_context'] = await self.detection_strategies.analyze_html_context(html_element, page_url)
                        detection_scores['structural_position'] = await self.detection_strategies.analyze_structural_position(html_element, [])
                        detection_scores['technical'] = await self.detection_strategies.analyze_image_technical(image_url, image_data)
                        detection_scores['visual'] = await self.detection_strategies.analyze_visual_characteristics(image_data)
                        detection_scores['url_semantics'] = await self.detection_strategies.analyze_url_semantics(image_url)
                        detection_scores['metadata'] = await self.detection_strategies.analyze_metadata(image_data)
                        detection_scores['social_media'] = await self.detection_strategies.analyze_social_media(domain)
                        detection_scores['schema_markup'] = await self.detection_strategies.analyze_schema_markup(page_html)
                        
                        # Calculate rank score
                        rank_score = await self.detection_strategies.get_final_score(detection_scores)
                    else:
                        rank_score = confidence
                    
                    return LogoResult(
                        url=image_url,
                        confidence=confidence,
                        description=description,
                        page_url=page_url,
                        image_hash=self.get_image_hash(image_base64.encode()),
                        timestamp=datetime.now(),
                        rank_score=rank_score,
                        detection_scores=detection_scores
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
                async with session.get(image_url, headers=BROWSER_HEADERS) as response:
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
                    
                    # Remove background by default
                    image = self.remove_background(image)
                    
                    buffered = io.BytesIO()
                    image.save(buffered, format="PNG")
                    image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    # Analyze with OpenAI (Azure or regular)
                    result = await self.analyze_image_with_openai(image_base64, image_url, page_url)
                    
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
                    async with session.get(url, headers=BROWSER_HEADERS) as response:
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
                        "timestamp": result.timestamp.isoformat(),
                        "rank_score": result.rank_score,
                        "detection_scores": result.detection_scores
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
                        pattern = rf"Logo {i}.*?score:?\s*(\d*\.?\d+)"
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

    async def crawl_website(self, url: str, skip_clearbit: bool = False, skip_google_favicon: bool = False) -> List[LogoResult]:
        """Crawl a website and find logos.
        
        Args:
            url: Website URL to crawl
            skip_clearbit: If True, skip Clearbit API
            skip_google_favicon: If True, skip Google Favicon fallback
        """
        # Extract domain for logo lookup
        domain = urlparse(url).netloc.replace("www.", "")
        
        # Try Clearbit first (free, fast, reliable for established companies)
        if not skip_clearbit:
            clearbit_result = await try_clearbit_logo(domain, url)
            if clearbit_result:
                print(f"🚀 Using Clearbit logo for {domain} (skipping crawl)")
                return [clearbit_result]
            print(f"ℹ️  Clearbit unavailable for {domain}")
        
        # Try Google Favicon as fallback (good coverage, lower quality)
        if not skip_google_favicon:
            favicon_result = await try_google_favicon(domain, url)
            if favicon_result:
                print(f"🔄 Using Google favicon for {domain} (skipping crawl)")
                return [favicon_result]
            print(f"ℹ️  Google favicon unavailable for {domain}, falling back to crawler...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=BROWSER_HEADERS) as response:
                    if response.status != 200:
                        return []

                    html = await response.text()

                    # Check for meta refresh redirect (not followed by aiohttp)
                    # This handles sites like helpify.net that use <meta http-equiv="refresh">
                    if len(html) < 500:  # Only check short pages that might be redirect stubs
                        meta_refresh_url = extract_meta_refresh_url(html, url)
                        if meta_refresh_url:
                            print(f"Found meta refresh redirect to: {meta_refresh_url}")
                            async with session.get(meta_refresh_url, headers=BROWSER_HEADERS) as redirect_response:
                                if redirect_response.status == 200:
                                    html = await redirect_response.text()
                                    url = str(redirect_response.url)
                                    print(f"Followed meta refresh to: {url}")

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
                    for image_url in all_images:
                        result = await self.analyze_image(image_url, url)
                        if result:
                            # Mark if image is from header/nav
                            result.is_header = image_url in header_images
                            results.append(result)
                    
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

    def detect_url_column(self, csv_file_path: str) -> Tuple[str, List[str]]:
        """
        Automatically detect the URL column in a CSV file.
        
        Args:
            csv_file_path: Path to the CSV file
            
        Returns:
            Tuple of (column_name, list_of_urls)
        """
        possible_url_headers = [
            'url', 'website', 'site', 'link', 'domain', 'company url', 
            'website url', 'site url', 'company website', 'company site',
            'web', 'webpage', 'page', 'address', 'homepage'
        ]
        
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            headers = reader.fieldnames
            
            if not headers:
                raise ValueError("CSV file has no headers")
            
            # Find the URL column
            url_column = None
            for header in headers:
                if header.lower().strip() in possible_url_headers:
                    url_column = header
                    break
            
            if not url_column:
                # If no exact match, try partial matches
                for header in headers:
                    header_lower = header.lower().strip()
                    for possible in possible_url_headers:
                        if possible in header_lower or header_lower in possible:
                            url_column = header
                            break
                    if url_column:
                        break
            
            if not url_column:
                raise ValueError(
                    f"Could not detect URL column. Available columns: {headers}. "
                    f"Please ensure one of these columns contains URLs: {possible_url_headers}"
                )
            
            # Extract URLs from the detected column
            urls = []
            for row in reader:
                url = row[url_column].strip()
                if url and url.lower() not in ['', 'nan', 'none', 'null']:
                    # Ensure URL has protocol
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    urls.append(url)
            
            return url_column, urls

    async def process_csv_batch(self, csv_file_path: str, output_dir: str = "results", confirm_header: bool = True) -> Dict[str, List[LogoResult]]:
        """
        Process a CSV file containing URLs and crawl each website for logos.
        
        Args:
            csv_file_path: Path to the CSV file containing URLs
            output_dir: Directory to save individual results
            confirm_header: Whether to confirm the detected URL column with user
            
        Returns:
            Dictionary mapping URLs to their logo results
        """
        print(f"Processing CSV file: {csv_file_path}")
        
        # Detect URL column
        url_column, urls = self.detect_url_column(csv_file_path)
        
        if confirm_header:
            print(f"\nDetected URL column: '{url_column}'")
            print(f"Found {len(urls)} URLs to process:")
            for i, url in enumerate(urls[:5], 1):  # Show first 5 URLs
                print(f"  {i}. {url}")
            if len(urls) > 5:
                print(f"  ... and {len(urls) - 5} more")
            
            response = input("\nProceed with this column? (y/n): ").lower().strip()
            if response not in ['y', 'yes']:
                print("Processing cancelled.")
                return {}
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Process each URL
        all_results = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%")
        ) as progress:
            task = progress.add_task("Processing websites...", total=len(urls))
            
            for url in urls:
                try:
                    progress.update(task, description=f"Processing {url}")
                    
                    # Crawl the website
                    results = await self.crawl_website(url)
                    
                    # Save individual results
                    if results:
                        # Create filename from URL
                        domain = urlparse(url).netloc.replace('.', '_')
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{domain}_{timestamp}.json"
                        filepath = output_path / filename
                        
                        # Create images subdirectory for background-removed logos
                        images_dir = output_path / f"{domain}_{timestamp}_images"
                        images_dir.mkdir(exist_ok=True)
                        
                        # Convert results to JSON format and save background-removed images
                        results_dict = []
                        for i, result in enumerate(results):
                            # Only process images with confidence score > 0.8
                            if result.confidence <= 0.8:
                                print(f"Skipping logo with low confidence ({result.confidence}): {result.url}")
                                continue
                            
                            # Only process company logos (not social media, generic icons, etc.)
                            if not self.is_company_logo(result.description, result.url):
                                print(f"Skipping non-company logo: {result.url} - {result.description}")
                                continue
                            
                            # Save background-removed image
                            try:
                                # Download the original image
                                async with aiohttp.ClientSession() as session:
                                    async with session.get(result.url, headers=BROWSER_HEADERS) as response:
                                        if response.status == 200:
                                            image_data = await response.read()
                                            image = Image.open(io.BytesIO(image_data))
                                            
                                            # Remove background
                                            image_no_bg = self.remove_background(image)
                                            
                                            # Save background-removed image locally
                                            image_filename = f"logo_{i+1}_{result.confidence:.2f}.png"
                                            image_path = images_dir / image_filename
                                            image_no_bg.save(image_path, "PNG")
                                            
                                            # Convert to bytes for cloud upload
                                            img_byte_arr = io.BytesIO()
                                            image_no_bg.save(img_byte_arr, format='PNG')
                                            img_bytes = img_byte_arr.getvalue()
                                            
                                            # Upload to cloud storage
                                            cloud_url = await self.cloud_storage.upload_image(img_bytes, image_filename)
                                            
                                            # Create local file URL
                                            local_file_url = f"file://{image_path.absolute()}"
                                            
                                            # Add image paths and URLs to result
                                            result_dict = {
                                                "url": result.url,
                                                "confidence": result.confidence,
                                                "description": result.description,
                                                "page_url": result.page_url,
                                                "image_hash": result.image_hash,
                                                "timestamp": result.timestamp.isoformat(),
                                                "rank_score": result.rank_score,
                                                "detection_scores": result.detection_scores,
                                                "is_header": result.is_header,
                                                "background_removed_image_path": str(image_path),
                                                "background_removed_image_url": cloud_url if cloud_url else local_file_url,
                                                "cloud_storage_url": cloud_url
                                            }
                                        else:
                                            # If image download fails, save without background-removed image
                                            result_dict = {
                                                "url": result.url,
                                                "confidence": result.confidence,
                                                "description": result.description,
                                                "page_url": result.page_url,
                                                "image_hash": result.image_hash,
                                                "timestamp": result.timestamp.isoformat(),
                                                "rank_score": result.rank_score,
                                                "detection_scores": result.detection_scores,
                                                "is_header": result.is_header,
                                                "background_removed_image_path": None,
                                                "background_removed_image_url": None,
                                                "cloud_storage_url": None
                                            }
                            except Exception as e:
                                print(f"Warning: Could not save background-removed image for {result.url}: {e}")
                                result_dict = {
                                    "url": result.url,
                                    "confidence": result.confidence,
                                    "description": result.description,
                                    "page_url": result.page_url,
                                    "image_hash": result.image_hash,
                                    "timestamp": result.timestamp.isoformat(),
                                    "rank_score": result.rank_score,
                                    "detection_scores": result.detection_scores,
                                    "is_header": result.is_header,
                                    "background_removed_image_path": None,
                                    "background_removed_image_url": None,
                                    "cloud_storage_url": None
                                }
                            
                            results_dict.append(result_dict)
                        
                        # Save to file
                        with open(filepath, 'w') as f:
                            json.dump(results_dict, f, indent=2)
                        
                        print(f"\n✅ {url}: Found {len(results)} logos, saved {len(results_dict)} company logos (>0.8 confidence) to {filepath}")
                        if results_dict:
                            print(f"📁 Background-removed images saved to: {images_dir}")
                            if any(r.get('cloud_storage_url') for r in results_dict):
                                print(f"☁️  Images uploaded to cloud storage")
                        else:
                            print(f"⚠️  No company logos found (all below 0.8 threshold or non-company logos)")
                    else:
                        print(f"\n❌ {url}: No logos found")
                    
                    all_results[url] = results
                    
                except Exception as e:
                    print(f"\n❌ {url}: Error - {e}")
                    all_results[url] = []
                
                progress.advance(task)
        
        # Create summary report
        summary_file = output_path / "batch_summary.json"
        summary = {
            "processed_at": datetime.now().isoformat(),
            "csv_file": csv_file_path,
            "url_column": url_column,
            "total_urls": len(urls),
            "successful_crawls": sum(1 for results in all_results.values() if results),
            "total_logos_found": sum(len(results) for results in all_results.values()),
            "results": {
                url: {
                    "logo_count": len(results),
                    "all_logos": [
                        {
                            "url": result.url,
                            "confidence": result.confidence,
                            "rank_score": result.rank_score,
                            "description": result.description,
                            "is_header": result.is_header
                        }
                        for result in results
                    ] if results else []
                }
                for url, results in all_results.items()
            }
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n🎉 Batch processing complete!")
        print(f"📊 Summary: {summary['successful_crawls']}/{summary['total_urls']} websites processed successfully")
        print(f"📁 Results saved to: {output_path}")
        print(f"📋 Summary report: {summary_file}")
        print(f"📸 Background-removed images saved in subdirectories")
        
        return all_results 