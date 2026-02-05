"""
Wikimedia Commons crawler.

Downloads images from Wikimedia Commons using the MediaWiki API.
Supports searching by keywords and extracting comprehensive metadata.
"""

import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

from .base_crawler import BaseCrawler, CrawlerConfig, ImageMetadata
from pathlib import Path

logger = logging.getLogger(__name__)


class WikimediaCrawler(BaseCrawler):
    """
    Crawler for Wikimedia Commons.

    Uses the MediaWiki API to search for images and download them with metadata.

    Example:
        >>> crawler = WikimediaCrawler()
        >>> images = crawler.crawl("rose window", limit=10)
        >>> print(f"Downloaded {len(images)} images")
    """

    API_URL = "https://commons.wikimedia.org/w/api.php"

    def __init__(self, config: Optional[CrawlerConfig] = None):
        super().__init__(config)

    def get_source_name(self) -> str:
        """Return the name of this crawler's source."""
        return "wikimedia_commons"

    def _build_search_params(self, query: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """
        Build parameters for MediaWiki API search.

        Args:
            query: Search query
            limit: Number of results per request
            offset: Offset for pagination

        Returns:
            Dictionary of API parameters
        """
        return {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f'filetype:bitmap {query}',
            "gsrlimit": min(limit, 50),  # API max is 50
            "gsroffset": offset,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|sha1|extmetadata",
            "iiurlwidth": 2000,  # Request high resolution
        }

    def _extract_metadata(self, page_data: Dict[str, Any], query: str) -> Optional[ImageMetadata]:
        """
        Extract metadata from MediaWiki API response.

        Args:
            page_data: Page data from API response
            query: Original search query (for tagging)

        Returns:
            ImageMetadata object or None if extraction fails
        """
        try:
            title = page_data.get("title", "Unknown")
            imageinfo = page_data.get("imageinfo", [{}])[0]

            if not imageinfo or "url" not in imageinfo:
                return None

            url = imageinfo["url"]
            width = imageinfo.get("width", 0)
            height = imageinfo.get("height", 0)
            sha1 = imageinfo.get("sha1", "")

            # Extract extended metadata
            extmetadata = imageinfo.get("extmetadata", {})

            # License information
            license_short = extmetadata.get("LicenseShortName", {}).get("value", "Unknown")
            license_url = extmetadata.get("LicenseUrl", {}).get("value", "")

            # Author
            artist = extmetadata.get("Artist", {}).get("value", "Unknown")
            # Strip HTML tags if present
            import re
            artist = re.sub('<[^<]+?>', '', artist) if artist else "Unknown"

            # Date
            date_time = extmetadata.get("DateTimeOriginal", {}).get("value", "")
            if not date_time:
                date_time = extmetadata.get("DateTime", {}).get("value", "")

            # Description
            description = extmetadata.get("ImageDescription", {}).get("value", "")
            description = re.sub('<[^<]+?>', '', description) if description else ""

            # Categories and tags
            categories = extmetadata.get("Categories", {}).get("value", "")
            tags = [query]  # Include search query as tag
            if categories:
                tags.extend([cat.strip() for cat in categories.split("|")])

            metadata = ImageMetadata(
                url=url,
                title=title,
                source=self.get_source_name(),
                width=width,
                height=height,
                license=f"{license_short} ({license_url})" if license_url else license_short,
                author=artist,
                date=date_time,
                tags=tags,
                extra={
                    "description": description,
                    "page_url": imageinfo.get("descriptionurl", ""),
                    "wikimedia_sha1": sha1,
                },
            )

            return metadata

        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}", exc_info=True)
            return None

    def _search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Search Wikimedia Commons for images.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of page data dictionaries
        """
        results = []
        offset = 0
        batch_size = min(limit, 50)

        while len(results) < limit:
            self._rate_limit()

            params = self._build_search_params(query, batch_size, offset)
            url = f"{self.API_URL}?{urlencode(params)}"

            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()

                pages = data.get("query", {}).get("pages", {})
                if not pages:
                    logger.info("No more results found")
                    break

                results.extend(pages.values())
                logger.info(f"Retrieved {len(results)} results so far")

                # Check if there are more results
                if "continue" not in data:
                    break

                offset = data["continue"].get("gsroffset", offset + batch_size)

            except Exception as e:
                logger.error(f"Search request failed: {e}", exc_info=True)
                break

        return results[:limit]

    def crawl(self, query: str, limit: Optional[int] = None) -> List[Path]:
        """
        Crawl Wikimedia Commons for images matching a query.

        Args:
            query: Search query (e.g., "rose window", "gothic cathedral")
            limit: Maximum number of images to download (default: 10)

        Returns:
            List of paths to downloaded images

        Example:
            >>> crawler = WikimediaCrawler()
            >>> images = crawler.crawl("rose window chartres", limit=5)
            >>> for img_path in images:
            ...     print(f"Downloaded: {img_path}")
        """
        limit = limit or 10
        logger.info(f"Starting Wikimedia crawl: query='{query}', limit={limit}")

        # Search for images
        search_results = self._search(query, limit)
        logger.info(f"Found {len(search_results)} search results")

        downloaded_images = []

        for page_data in search_results:
            try:
                # Extract metadata
                metadata = self._extract_metadata(page_data, query)
                if metadata is None:
                    continue

                # Process and save image
                filepath = self.process_image(metadata.url, metadata)
                if filepath:
                    downloaded_images.append(filepath)
                    logger.info(f"Successfully processed: {metadata.title}")

            except Exception as e:
                logger.error(f"Failed to process page: {e}", exc_info=True)
                continue

        logger.info(f"Crawl completed: {len(downloaded_images)}/{len(search_results)} images downloaded")
        return downloaded_images


def main():
    """CLI entry point for Wikimedia crawler."""
    import argparse

    parser = argparse.ArgumentParser(description="Crawl Wikimedia Commons for images")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of images")
    parser.add_argument("--min-width", type=int, default=800, help="Minimum image width")
    parser.add_argument("--min-height", type=int, default=800, help="Minimum image height")
    parser.add_argument("--output", type=Path, default=Path("data/raw"), help="Output directory")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create crawler
    config = CrawlerConfig(
        min_width=args.min_width,
        min_height=args.min_height,
        images_store=args.output,
    )
    crawler = WikimediaCrawler(config)

    # Run crawl
    images = crawler.crawl(args.query, limit=args.limit)

    print(f"\n✓ Downloaded {len(images)} images to {args.output}")
    for img_path in images:
        print(f"  - {img_path.name}")


if __name__ == "__main__":
    main()
