"""
Base crawler class for all web scrapers.

Provides common functionality for downloading images, handling rate limiting,
deduplication, and metadata storage.
"""

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import imagehash
import requests
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)


class CrawlerConfig:
    """Configuration for web crawlers."""

    def __init__(
        self,
        download_delay: float = 1.0,
        user_agent: str = "AncientWorld/0.1.0",
        min_width: int = 800,
        min_height: int = 800,
        images_store: Path = Path("data/raw"),
        cache_dir: Path = Path("data/cache"),
        max_retries: int = 3,
    ):
        self.download_delay = download_delay
        self.user_agent = user_agent
        self.min_width = min_width
        self.min_height = min_height
        self.images_store = images_store
        self.cache_dir = cache_dir
        self.max_retries = max_retries

        # Ensure directories exist
        self.images_store.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


class ImageMetadata:
    """Metadata for a downloaded image."""

    def __init__(
        self,
        url: str,
        title: str,
        source: str,
        width: int,
        height: int,
        sha256: Optional[str] = None,
        phash: Optional[str] = None,
        license: Optional[str] = None,
        author: Optional[str] = None,
        date: Optional[str] = None,
        location: Optional[str] = None,
        building: Optional[str] = None,
        tags: Optional[List[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.url = url
        self.title = title
        self.source = source
        self.width = width
        self.height = height
        self.sha256 = sha256
        self.phash = phash
        self.license = license
        self.author = author
        self.date = date
        self.location = location
        self.building = building
        self.tags = tags or []
        self.extra = extra or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "source": self.source,
            "width": self.width,
            "height": self.height,
            "sha256": self.sha256,
            "phash": self.phash,
            "license": self.license,
            "author": self.author,
            "date": self.date,
            "location": self.location,
            "building": self.building,
            "tags": self.tags,
            "extra": self.extra,
        }


class BaseCrawler(ABC):
    """
    Abstract base class for all crawlers.

    Provides common functionality for:
    - Rate limiting
    - Image downloading
    - Deduplication (SHA256 and perceptual hashing)
    - Metadata storage
    - Error handling and retries
    """

    def __init__(self, config: Optional[CrawlerConfig] = None):
        self.config = config or CrawlerConfig()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.config.user_agent})
        self.last_request_time = 0.0
        self.downloaded_hashes = set()
        self.downloaded_phashes = set()

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.config.download_delay:
            time.sleep(self.config.download_delay - elapsed)
        self.last_request_time = time.time()

    def _download_image(self, url: str) -> Optional[Image.Image]:
        """
        Download an image from a URL.

        Args:
            url: Image URL

        Returns:
            PIL Image object or None if download fails
        """
        self._rate_limit()

        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                image = Image.open(BytesIO(response.content))
                logger.info(f"Downloaded image: {url}")
                return image

            except Exception as e:
                logger.warning(f"Download attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

        logger.error(f"Failed to download image after {self.config.max_retries} attempts: {url}")
        return None

    def _compute_hashes(self, image: Image.Image) -> tuple[str, str]:
        """
        Compute SHA256 and perceptual hash for an image.

        Args:
            image: PIL Image object

        Returns:
            Tuple of (sha256_hex, phash_hex)
        """
        # SHA256 hash of image bytes
        img_bytes = BytesIO()
        image.save(img_bytes, format=image.format or "PNG")
        sha256 = hashlib.sha256(img_bytes.getvalue()).hexdigest()

        # Perceptual hash
        phash = str(imagehash.phash(image))

        return sha256, phash

    def _is_duplicate(self, sha256: str, phash: str) -> bool:
        """
        Check if an image is a duplicate based on hashes.

        Args:
            sha256: SHA256 hash
            phash: Perceptual hash

        Returns:
            True if duplicate, False otherwise
        """
        if sha256 in self.downloaded_hashes:
            logger.info(f"Duplicate detected (exact): {sha256}")
            return True

        if phash in self.downloaded_phashes:
            logger.info(f"Duplicate detected (perceptual): {phash}")
            return True

        return False

    def _save_image(self, image: Image.Image, metadata: ImageMetadata) -> Path:
        """
        Save an image to disk with metadata.

        Args:
            image: PIL Image object
            metadata: Image metadata

        Returns:
            Path to saved image
        """
        # Generate filename from hash
        filename = f"{metadata.sha256}.jpg"
        filepath = self.config.images_store / filename

        # Save image
        image.convert("RGB").save(filepath, "JPEG", quality=95)
        logger.info(f"Saved image: {filepath}")

        # Save metadata as JSON sidecar
        import json
        metadata_path = filepath.with_suffix(".json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

        return filepath

    def _filter_image(self, image: Image.Image) -> bool:
        """
        Check if an image meets minimum quality requirements.

        Args:
            image: PIL Image object

        Returns:
            True if image passes filters, False otherwise
        """
        width, height = image.size

        if width < self.config.min_width or height < self.config.min_height:
            logger.debug(f"Image too small: {width}x{height}")
            return False

        return True

    def process_image(self, url: str, metadata: ImageMetadata) -> Optional[Path]:
        """
        Download, process, and save an image.

        Args:
            url: Image URL
            metadata: Image metadata

        Returns:
            Path to saved image or None if processing failed
        """
        # Download image
        image = self._download_image(url)
        if image is None:
            return None

        # Filter by size
        if not self._filter_image(image):
            return None

        # Compute hashes
        sha256, phash = self._compute_hashes(image)
        metadata.sha256 = sha256
        metadata.phash = phash

        # Check for duplicates
        if self._is_duplicate(sha256, phash):
            return None

        # Save image
        filepath = self._save_image(image, metadata)

        # Update tracking sets
        self.downloaded_hashes.add(sha256)
        self.downloaded_phashes.add(phash)

        return filepath

    @abstractmethod
    def crawl(self, query: str, limit: Optional[int] = None) -> List[Path]:
        """
        Crawl a source for images matching a query.

        Args:
            query: Search query
            limit: Maximum number of images to download

        Returns:
            List of paths to downloaded images
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of this crawler's source."""
        pass
