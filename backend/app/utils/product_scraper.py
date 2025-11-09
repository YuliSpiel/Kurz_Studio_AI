"""
Product information scraper for ad mode.
Extracts product details from e-commerce URLs.
"""
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ProductScraper:
    """Scrapes product information from e-commerce websites."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def scrape(self, url: str) -> Dict:
        """
        Scrape product information from URL.

        Args:
            url: Product page URL

        Returns:
            Dictionary with product info:
            - name: Product name
            - description: Product description
            - features: List of key features
            - price: Product price (optional)
            - images: List of image URLs
            - category: Product category (optional)
        """
        logger.info(f"Scraping product from URL: {url}")

        try:
            # Fetch the page
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding

            soup = BeautifulSoup(response.text, 'html.parser')

            # Parse domain to determine scraping strategy
            domain = urlparse(url).netloc.lower()

            if 'coupang.com' in domain:
                return self._scrape_coupang(soup, url)
            elif 'naver.com' in domain:
                return self._scrape_naver(soup, url)
            else:
                # Generic scraper for other sites
                return self._scrape_generic(soup, url)

        except Exception as e:
            logger.error(f"Failed to scrape URL {url}: {e}")
            # Return minimal data structure
            return {
                'name': '제품',
                'description': f'URL: {url}',
                'features': [],
                'images': [],
                'price': None,
                'category': None,
                'error': str(e)
            }

    def _scrape_coupang(self, soup: BeautifulSoup, url: str) -> Dict:
        """Scrape Coupang product page."""
        logger.info("Using Coupang scraping strategy")

        product_data = {
            'name': '',
            'description': '',
            'features': [],
            'images': [],
            'price': None,
            'category': None
        }

        # Product name
        name_tag = soup.find('h1', class_='prod-buy-header__title')
        if not name_tag:
            name_tag = soup.find('h2', class_='prod-buy-header__title')
        if name_tag:
            product_data['name'] = name_tag.get_text(strip=True)

        # Product description
        desc_tag = soup.find('div', class_='prod-description')
        if desc_tag:
            product_data['description'] = desc_tag.get_text(strip=True)

        # Product features (from bullet points)
        features = []
        feature_list = soup.find('ul', class_='prod-description-attribute')
        if feature_list:
            for li in feature_list.find_all('li'):
                features.append(li.get_text(strip=True))
        product_data['features'] = features[:5]  # Limit to top 5 features

        # Price
        price_tag = soup.find('span', class_='total-price')
        if price_tag:
            product_data['price'] = price_tag.get_text(strip=True)

        # Images
        images = []
        img_container = soup.find('div', class_='prod-image__detail')
        if img_container:
            for img in img_container.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src and src.startswith('http'):
                    images.append(src)
        product_data['images'] = images[:3]  # Limit to top 3 images

        return product_data

    def _scrape_naver(self, soup: BeautifulSoup, url: str) -> Dict:
        """Scrape Naver Shopping product page."""
        logger.info("Using Naver Shopping scraping strategy")

        product_data = {
            'name': '',
            'description': '',
            'features': [],
            'images': [],
            'price': None,
            'category': None
        }

        # Product name
        name_tag = soup.find('h2', class_='_22kNQuEXmb _copyable')
        if not name_tag:
            name_tag = soup.find('h3', class_='_itemSection_title')
        if name_tag:
            product_data['name'] = name_tag.get_text(strip=True)

        # Description
        desc_tag = soup.find('div', class_='_22kNQuEXmb_description')
        if desc_tag:
            product_data['description'] = desc_tag.get_text(strip=True)

        # Price
        price_tag = soup.find('span', class_='_1LY7DqCnwR')
        if price_tag:
            product_data['price'] = price_tag.get_text(strip=True)

        # Images
        images = []
        img_tags = soup.find_all('img', class_='_25CKxIKjAk')
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src and src.startswith('http'):
                images.append(src)
        product_data['images'] = images[:3]

        return product_data

    def _scrape_generic(self, soup: BeautifulSoup, url: str) -> Dict:
        """Generic scraper for unknown sites."""
        logger.info("Using generic scraping strategy")

        product_data = {
            'name': '',
            'description': '',
            'features': [],
            'images': [],
            'price': None,
            'category': None
        }

        # Try common patterns for product name
        name_tag = (
            soup.find('h1', class_=re.compile(r'product|title|name', re.I)) or
            soup.find('h2', class_=re.compile(r'product|title|name', re.I)) or
            soup.find('h1') or
            soup.find('title')
        )
        if name_tag:
            product_data['name'] = name_tag.get_text(strip=True)

        # Try common patterns for description
        desc_tag = (
            soup.find('div', class_=re.compile(r'description|detail|summary', re.I)) or
            soup.find('meta', {'name': 'description'}) or
            soup.find('meta', {'property': 'og:description'})
        )
        if desc_tag:
            if desc_tag.name == 'meta':
                product_data['description'] = desc_tag.get('content', '')
            else:
                product_data['description'] = desc_tag.get_text(strip=True)[:500]

        # Try common patterns for price
        price_tag = (
            soup.find('span', class_=re.compile(r'price', re.I)) or
            soup.find('div', class_=re.compile(r'price', re.I))
        )
        if price_tag:
            product_data['price'] = price_tag.get_text(strip=True)

        # Collect images
        images = []
        # Try og:image first
        og_img = soup.find('meta', {'property': 'og:image'})
        if og_img:
            images.append(og_img.get('content'))

        # Then look for product images
        for img in soup.find_all('img', class_=re.compile(r'product|main|detail', re.I)):
            src = img.get('src') or img.get('data-src')
            if src:
                if not src.startswith('http'):
                    # Handle relative URLs
                    from urllib.parse import urljoin
                    src = urljoin(url, src)
                if src not in images:
                    images.append(src)
                if len(images) >= 3:
                    break

        product_data['images'] = images

        # Extract bullet points as features
        features = []
        for ul in soup.find_all('ul', class_=re.compile(r'feature|spec|detail', re.I)):
            for li in ul.find_all('li')[:5]:
                features.append(li.get_text(strip=True))
        product_data['features'] = features[:5]

        return product_data


def scrape_product(url: str) -> Dict:
    """
    Convenience function to scrape product information.

    Args:
        url: Product page URL

    Returns:
        Dictionary with product information
    """
    scraper = ProductScraper()
    return scraper.scrape(url)


def download_product_images(image_urls: List[str], output_dir: str) -> List[str]:
    """
    Download product images and save them to output directory.

    Args:
        image_urls: List of image URLs to download
        output_dir: Directory to save images

    Returns:
        List of saved file paths
    """
    from pathlib import Path
    import requests
    from urllib.parse import urlparse

    logger.info(f"Downloading {len(image_urls)} product images...")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_files = []

    for idx, img_url in enumerate(image_urls):
        try:
            # Download image
            response = requests.get(img_url, timeout=10)
            response.raise_for_status()

            # Determine file extension from URL or content-type
            ext = '.jpg'  # default
            parsed_url = urlparse(img_url)
            url_path = parsed_url.path.lower()

            if url_path.endswith('.png'):
                ext = '.png'
            elif url_path.endswith('.webp'):
                ext = '.webp'
            elif url_path.endswith('.gif'):
                ext = '.gif'
            elif 'content-type' in response.headers:
                content_type = response.headers['content-type'].lower()
                if 'png' in content_type:
                    ext = '.png'
                elif 'webp' in content_type:
                    ext = '.webp'
                elif 'gif' in content_type:
                    ext = '.gif'

            # Save file
            filename = f"product_image_{idx+1}{ext}"
            file_path = output_path / filename

            with open(file_path, 'wb') as f:
                f.write(response.content)

            saved_files.append(str(file_path))
            logger.info(f"Downloaded: {filename}")

        except Exception as e:
            logger.warning(f"Failed to download image {img_url}: {e}")
            continue

    logger.info(f"Successfully downloaded {len(saved_files)} images")
    return saved_files
