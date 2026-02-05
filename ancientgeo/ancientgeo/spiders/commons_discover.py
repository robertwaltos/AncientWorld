"""
Discovery spider for Wikimedia Commons.

Only discovers and catalogs images - does not download yet.
This allows building a large candidate pool before downloading.
"""

import json
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlencode

import scrapy

# Add parent directories to path to find config
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config.storage_config import DB_PATH

SEED_QUERIES = [
    # Rose windows & tracery
    "rose window", "wheel window", "oculus window",
    "gothic tracery", "bar tracery", "plate tracery",
    "flamboyant tracery", "perpendicular tracery",

    # Facades & elevations    "gothic cathedral facade", "cathedral west front",
    "romanesque facade", "byzantine facade",
    "church facade medieval", "basilica facade",
    "architectural elevation gothic",

    # Geometric construction
    "sacred geometry architecture", "geometric construction medieval",
    "stereotomy", "stonecutting geometry",
    "vault construction", "rib vault",

    # Islamic geometry
    "islamic geometric pattern", "girih", "muqarnas",
    "zellige", "mashrabiya", "arabesques architecture",

    # Greek/Roman
    "greek temple facade", "roman temple",
    "corinthian capital", "ionic capital",

    # Architectural drawings
    "architectural drawing medieval", "architectural plan gothic",
    "elevation drawing cathedral",

    # Specific buildings
    "chartres cathedral", "reims cathedral",
    "notre dame paris", "salisbury cathedral",
    "alhambra granada", "hagia sophia",
]


class CommonsDiscoverSpider(scrapy.Spider):
    """
    Wikimedia Commons discovery spider.

    Usage:
        scrapy crawl commons_discover
    """

    name = "commons_discover"
    allowed_domains = ["commons.wikimedia.org"]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,  # API endpoint - designed for programmatic access
        "DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 3,
        "AUTOTHROTTLE_ENABLED": True,
        "LOG_LEVEL": "INFO",
    }

    def __init__(self, *args, **kwargs):
        """Initialize spider and database connection."""
        super().__init__(*args, **kwargs)

        db_path = Path(DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.con = sqlite3.connect(db_path)
        self.con.execute("PRAGMA journal_mode=WAL;")
        self.con.execute("PRAGMA synchronous=NORMAL;")

        self.logger.info(f"Connected to database: {db_path}")

    def closed(self, reason):
        """Close database and show statistics."""
        self.con.commit()

        # Get stats
        stats = dict(self.con.execute("SELECT k, v FROM stats").fetchall())
        total = self.con.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]

        self.con.close()

        self.logger.info("="*60)
        self.logger.info("Discovery phase complete!")
        self.logger.info(f"Total candidates discovered: {total}")
        self.logger.info(f"Pending download: {stats.get('total_candidates', 0)}")
        self.logger.info("="*60)

    def start_requests(self):
        """Start discovery for all queries."""
        for query in SEED_QUERIES:
            yield self._api_request(query, offset=0)

    def _api_request(self, query: str, offset: int):
        """Build MediaWiki API request."""
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f'intitle:"File:" {query}',
            "gsrlimit": "50",
            "gsroffset": str(offset),
            "prop": "imageinfo|categories",
            "cllimit": "50",
            "iiprop": "url|size|mime|sha1|extmetadata",
        }
        url = "https://commons.wikimedia.org/w/api.php?" + urlencode(params)
        return scrapy.Request(
            url,
            callback=self.parse_api,
            meta={"query": query, "offset": offset}
        )

    def parse_api(self, response):
        """Parse MediaWiki API response and store candidates."""
        query = response.meta["query"]
        data = response.json()

        pages = (data.get("query", {}).get("pages", {}) or {}).values()

        def ext_val(ext, key):
            """Extract value from extmetadata."""
            v = (ext or {}).get(key)
            if isinstance(v, dict):
                return v.get("value")
            return None

        rows_inserted = 0
        for page in pages:
            imageinfo = (page.get("imageinfo") or [None])[0]
            if not imageinfo:
                continue

            image_url = imageinfo.get("url")
            if not image_url:
                continue

            ext = imageinfo.get("extmetadata") or {}
            cats = [c.get("title") for c in (page.get("categories") or []) if c.get("title")]

            record = (
                "wikimedia_commons",
                query,
                page.get("title"),
                imageinfo.get("descriptionurl"),
                image_url,
                imageinfo.get("width"),
                imageinfo.get("height"),
                imageinfo.get("mime"),
                imageinfo.get("sha1"),
                ext_val(ext, "LicenseShortName") or ext_val(ext, "License"),
                ext_val(ext, "Artist"),
                ext_val(ext, "Credit"),
                ext_val(ext, "DateTimeOriginal") or ext_val(ext, "Date"),
                ext_val(ext, "Institution"),
                ext_val(ext, "ImageDescription"),
                json.dumps(cats, ensure_ascii=False) if cats else None,
            )

            try:
                self.con.execute("""
                    INSERT OR IGNORE INTO candidates(
                        source, query, title, page_url, image_url,
                        width, height, mime, sha1,
                        license, artist, credit, date, institution, description,
                        categories_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, record)
                rows_inserted += 1
            except sqlite3.Error as e:
                self.logger.error(f"Database error: {e}")

        self.con.commit()

        # Update stats
        self.con.execute("""
            UPDATE stats SET v = v + ?
            WHERE k = 'total_candidates'
        """, (rows_inserted,))
        self.con.commit()

        self.logger.info(
            f"[{query}] +{rows_inserted} candidates "
            f"(offset={response.meta['offset']})"
        )

        # Check for continuation
        cont = data.get("continue") or {}
        if "gsroffset" in cont:
            next_offset = int(cont["gsroffset"])
            yield self._api_request(query, offset=next_offset)
