import os
import re
from typing import List, Dict, Set, Optional, Tuple
from urllib.parse import urljoin, urlparse
import json
import magic
import cv2
import numpy as np
from bs4 import BeautifulSoup, Tag
import extcolors
from PIL import Image
import pytesseract
import imagehash
import tweepy
from jsonschema import validate
import aiohttp
from dataclasses import dataclass
from sklearn.ensemble import RandomForestClassifier
import logging

@dataclass
class LogoCandidate:
    url: str
    score: float
    features: Dict[str, float]
    metadata: Dict[str, any]

class LogoDetectionStrategies:
    def __init__(self, twitter_api_key: Optional[str] = None):
        self.twitter_api_key = twitter_api_key
        self.twitter_client = self._setup_twitter_client() if twitter_api_key else None
        self.logger = logging.getLogger(__name__)

    def _setup_twitter_client(self) -> Optional[tweepy.Client]:
        try:
            return tweepy.Client(bearer_token=self.twitter_api_key)
        except Exception as e:
            self.logger.warning(f"Failed to initialize Twitter client: {e}")
            return None

    async def analyze_html_context(self, element: Tag, base_url: str) -> Dict[str, float]:
        """Analyze HTML context for logo indicators."""
        scores = {
            'class_score': 0.0,
            'alt_text_score': 0.0,
            'homepage_link_score': 0.0,
            'brand_proximity_score': 0.0
        }

        # Check class names and IDs
        classes = element.get('class', [])
        element_id = element.get('id', '')
        logo_terms = {'logo', 'brand', 'site-logo', 'company-logo', 'header-logo'}
        scores['class_score'] = any(term in str(classes).lower() or term in str(element_id).lower() 
                                  for term in logo_terms)

        # Check alt text and title
        alt_text = element.get('alt', '').lower()
        title = element.get('title', '').lower()
        scores['alt_text_score'] = any(term in alt_text or term in title for term in logo_terms)

        # Check if image links to homepage
        parent_a = element.find_parent('a')
        if parent_a and parent_a.get('href'):
            href = urljoin(base_url, parent_a['href'])
            parsed_href = urlparse(href)
            parsed_base = urlparse(base_url)
            scores['homepage_link_score'] = parsed_href.netloc == parsed_base.netloc and parsed_href.path in ['/', '/home']

        # Check proximity to brand name/company name
        surrounding_text = ''.join(s.string for s in element.find_all_previous(string=True, limit=5))
        scores['brand_proximity_score'] = any(term in surrounding_text.lower() for term in logo_terms)

        return scores

    async def analyze_structural_position(self, element: Tag, all_pages_elements: List[Tag]) -> Dict[str, float]:
        """Analyze structural position in the DOM."""
        scores = {
            'dom_depth_score': 0.0,
            'position_score': 0.0,
            'consistency_score': 0.0
        }

        # Calculate DOM depth (normalize between 0 and 1)
        depth = len(list(element.parents))
        scores['dom_depth_score'] = 1.0 / (1.0 + depth)  # Higher score for elements closer to root

        # Analyze position
        if element.parent:
            parent_box = element.parent.get('style', '')
            scores['position_score'] = any(pos in parent_box.lower() for pos in ['top', 'left: 0', 'margin-left: auto'])

        # Check consistency across pages
        if all_pages_elements:
            element_path = self._get_element_path(element)
            matching_elements = sum(1 for e in all_pages_elements if self._get_element_path(e) == element_path)
            scores['consistency_score'] = matching_elements / len(all_pages_elements)

        return scores

    async def analyze_image_technical(self, image_url: str, image_data: bytes) -> Dict[str, float]:
        """Analyze technical aspects of the image."""
        scores = {
            'aspect_ratio_score': 0.0,
            'transparency_score': 0.0,
            'format_score': 0.0,
            'filename_score': 0.0,
            'size_score': 0.0
        }

        try:
            # Check file format
            mime = magic.from_buffer(image_data, mime=True)
            scores['format_score'] = 1.0 if mime in ['image/svg+xml', 'image/png'] else 0.5

            # Analyze filename
            filename = os.path.basename(urlparse(image_url).path).lower()
            scores['filename_score'] = any(term in filename for term in ['logo', 'brand', 'icon'])

            # Image analysis
            img = Image.open(io.BytesIO(image_data))
            width, height = img.size

            # Aspect ratio analysis (prefer ratios between 0.5 and 2.0)
            aspect_ratio = width / height
            scores['aspect_ratio_score'] = 1.0 if 0.5 <= aspect_ratio <= 2.0 else 0.0

            # Check for transparency
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                scores['transparency_score'] = 1.0

            # Size analysis (prefer medium-sized images)
            area = width * height
            scores['size_score'] = 1.0 if 5000 <= area <= 100000 else 0.0

        except Exception as e:
            self.logger.error(f"Error analyzing image technical aspects: {e}")

        return scores

    async def analyze_visual_characteristics(self, image_data: bytes) -> Dict[str, float]:
        """Analyze visual characteristics of the image."""
        scores = {
            'text_presence_score': 0.0,
            'color_palette_score': 0.0,
            'geometric_score': 0.0,
            'whitespace_score': 0.0
        }

        try:
            # Convert to OpenCV format
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Text detection using OCR
            text = pytesseract.image_to_string(img)
            scores['text_presence_score'] = 1.0 if text.strip() else 0.0

            # Color palette analysis
            colors = extcolors.extract_from_image(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
            scores['color_palette_score'] = 1.0 if len(colors[0]) <= 5 else 0.0  # Prefer limited color palettes

            # Geometric shape detection
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            scores['geometric_score'] = 1.0 if len(contours) < 20 else 0.0  # Prefer simpler shapes

            # White space analysis
            white_pixels = np.sum(gray > 240)
            total_pixels = gray.size
            scores['whitespace_score'] = white_pixels / total_pixels

        except Exception as e:
            self.logger.error(f"Error analyzing visual characteristics: {e}")

        return scores

    async def analyze_multi_page_consistency(self, image_url: str, all_pages_images: List[Dict]) -> Dict[str, float]:
        """Analyze image consistency across multiple pages."""
        scores = {
            'appearance_score': 0.0,
            'position_consistency_score': 0.0,
            'size_consistency_score': 0.0,
            'template_score': 0.0
        }

        try:
            # Count appearances
            appearances = sum(1 for img in all_pages_images if img['url'] == image_url)
            scores['appearance_score'] = appearances / len(all_pages_images)

            # Position consistency
            positions = [img['position'] for img in all_pages_images if img['url'] == image_url]
            scores['position_consistency_score'] = len(set(positions)) == 1

            # Size consistency
            sizes = [img['size'] for img in all_pages_images if img['url'] == image_url]
            scores['size_consistency_score'] = len(set(sizes)) == 1

            # Template analysis (check if image appears in header/footer)
            template_positions = [img['in_template'] for img in all_pages_images if img['url'] == image_url]
            scores['template_score'] = all(template_positions)

        except Exception as e:
            self.logger.error(f"Error analyzing multi-page consistency: {e}")

        return scores

    async def analyze_url_semantics(self, image_url: str) -> Dict[str, float]:
        """Analyze URL patterns and semantics."""
        scores = {
            'path_score': 0.0,
            'cdn_score': 0.0,
            'versioning_score': 0.0
        }

        parsed_url = urlparse(image_url)
        path = parsed_url.path.lower()

        # Check path for logo-related terms
        scores['path_score'] = any(term in path for term in ['logo', 'brand', 'header', 'site-id'])

        # Check for CDN patterns
        cdn_patterns = ['assets', 'static', 'media', 'images', 'cdn']
        scores['cdn_score'] = any(pattern in parsed_url.netloc or pattern in path for pattern in cdn_patterns)

        # Check for versioning
        scores['versioning_score'] = bool(re.search(r'v\d+|version-\d+', path))

        return scores

    async def analyze_metadata(self, image_data: bytes) -> Dict[str, float]:
        """Analyze image metadata."""
        scores = {
            'copyright_score': 0.0,
            'software_score': 0.0,
            'date_score': 0.0,
            'guidelines_score': 0.0
        }

        try:
            img = Image.open(io.BytesIO(image_data))
            metadata = img.info

            # Check for copyright information
            scores['copyright_score'] = 'copyright' in str(metadata).lower()

            # Check for design software signatures
            design_software = ['adobe', 'sketch', 'figma', 'illustrator']
            scores['software_score'] = any(sw in str(metadata).lower() for sw in design_software)

            # Check creation date (prefer recent files)
            if 'creation_date' in metadata:
                creation_year = int(metadata['creation_date'][:4])
                scores['date_score'] = 1.0 if creation_year >= 2020 else 0.5

            # Check for brand guidelines references
            scores['guidelines_score'] = 'brand' in str(metadata).lower() or 'guidelines' in str(metadata).lower()

        except Exception as e:
            self.logger.error(f"Error analyzing metadata: {e}")

        return scores

    async def analyze_social_media(self, domain: str) -> Dict[str, float]:
        """Analyze social media presence and cross-reference logos."""
        scores = {
            'twitter_match_score': 0.0,
            'og_image_score': 0.0,
            'favicon_score': 0.0
        }

        try:
            # Check Twitter profile image
            if self.twitter_client:
                try:
                    # Search for the company's Twitter account
                    query = f"url:{domain}"
                    response = self.twitter_client.search_recent_tweets(query=query, max_results=10)
                    if response.data:
                        for tweet in response.data:
                            if domain in tweet.text.lower():
                                author_id = tweet.author_id
                                user = self.twitter_client.get_user(id=author_id)
                                if user.data:
                                    profile_image_url = user.data.profile_image_url
                                    scores['twitter_match_score'] = 1.0
                except Exception as e:
                    self.logger.warning(f"Twitter API error: {e}")

            # Check OpenGraph and Twitter Card images
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://{domain}") as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        og_image = soup.find('meta', property='og:image')
                        twitter_image = soup.find('meta', name='twitter:image')
                        
                        scores['og_image_score'] = 1.0 if og_image or twitter_image else 0.0

                        # Check favicon
                        favicon = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
                        scores['favicon_score'] = 1.0 if favicon else 0.0

        except Exception as e:
            self.logger.error(f"Error analyzing social media: {e}")

        return scores

    async def analyze_schema_markup(self, html: str) -> Dict[str, float]:
        """Analyze schema.org and SEO markup."""
        scores = {
            'schema_score': 0.0,
            'json_ld_score': 0.0,
            'meta_score': 0.0
        }

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Check JSON-LD
            json_ld = soup.find('script', type='application/ld+json')
            if json_ld:
                try:
                    data = json.loads(json_ld.string)
                    if isinstance(data, dict):
                        scores['json_ld_score'] = 'logo' in str(data)
                except json.JSONDecodeError:
                    pass

            # Check schema.org markup
            schema_elements = soup.find_all(attrs={'itemtype': re.compile(r'schema.org')})
            for element in schema_elements:
                if 'logo' in str(element):
                    scores['schema_score'] = 1.0
                    break

            # Check meta tags
            meta_tags = soup.find_all('meta')
            for tag in meta_tags:
                if 'logo' in str(tag) or 'brand' in str(tag):
                    scores['meta_score'] = 1.0
                    break

        except Exception as e:
            self.logger.error(f"Error analyzing schema markup: {e}")

        return scores

    def _get_element_path(self, element: Tag) -> str:
        """Get a unique path for an element in the DOM."""
        path = []
        for parent in element.parents:
            siblings = parent.find_all(parent.name, recursive=False)
            path.append(f"{parent.name}[{list(siblings).index(parent)}]")
        return ' > '.join(reversed(path))

    async def get_final_score(self, all_scores: Dict[str, Dict[str, float]]) -> float:
        """Calculate final score using weighted average of all strategies."""
        weights = {
            'html_context': 0.15,
            'structural_position': 0.15,
            'technical': 0.10,
            'visual': 0.15,
            'multi_page': 0.15,
            'url_semantics': 0.05,
            'metadata': 0.05,
            'social_media': 0.10,
            'schema_markup': 0.10
        }

        final_score = 0.0
        for category, scores in all_scores.items():
            category_score = sum(scores.values()) / len(scores)
            final_score += category_score * weights.get(category, 0)

        return final_score 