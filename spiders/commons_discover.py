import json
import sqlite3
from urllib.parse import urlencode
import scrapy

DB_PATH = r"E:\ancientgeo\db\assets.sqlite3"

SEED_QUERIES = [
    # Windows / tracery
    "rose window", "wheel window", "oculus window",
    "gothic tracery", "bar tracery", "stone tracery",
    # Facades / elevations
    "gothic cathedral facade", "cathedral west front",
    "roman basilica facade", "church facade medieval",
    "architectural elevation medieval", "architectural drawing gothic",
    # Geometric construction / ornament
    "geometric construction", "sacred geometry architecture",
    "stereotomy", "stonecutting geometry",
    "islamic geometric pattern", "girih", "muqarnas", "zellige", "mashrabiya",
    "ornament geometric medieval",
]

class CommonsDiscoverSpider(scrapy.Spider):
    name = "commons_discover"
    allowed_domains = ["commons.wikimedia.org"]

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 0.4,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "AUTOTHROTTLE_ENABLED": True,
        "LOG_LEVEL": "INFO",
    }

    def open_spider(self, spider):
        self.con = sqlite3.connect(DB_PATH)
        self.con.execute("PRAGMA journal_mode=WAL;")
        self.con.execute("PRAGMA synchronous=NORMAL;")

    def close_spider(self, spider):
        self.con.commit()
        self.con.close()

    def start_requests(self):
        for q in SEED_QUERIES:
            yield self._api_request(q, offset=0)

    def _api_request(self, q: str, offset: int):
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            # bias toward File pages
            "gsrsearch": f'intitle:"File:" {q}',
            "gsrlimit": "50",
            "gsroffset": str(offset),
            "prop": "imageinfo|categories",
            "cllimit": "50",
            "iiprop": "url|size|mime|sha1|extmetadata",
        }
        url = "https://commons.wikimedia.org/w/api.php?" + urlencode(params)
        return scrapy.Request(url, callback=self.parse_api, meta={"query": q, "offset": offset})

    def parse_api(self, response):
        q = response.meta["query"]
        data = response.json()

        pages = (data.get("query", {}).get("pages", {}) or {}).values()

        def ext_val(ext, key):
            v = (ext or {}).get(key)
            if isinstance(v, dict):
                return v.get("value")
            return None

        rows = 0
        for p in pages:
            ii = (p.get("imageinfo") or [None])[0]
            if not ii:
                continue
            image_url = ii.get("url")
            if not image_url:
                continue

            ext = ii.get("extmetadata") or {}
            cats = [c.get("title") for c in (p.get("categories") or []) if c.get("title")]

            rec = (
                "wikimedia_commons",
                q,
                p.get("title"),
                ii.get("descriptionurl"),
                image_url,
                ii.get("width"),
                ii.get("height"),
                ii.get("mime"),
                ii.get("sha1"),
                ext_val(ext, "LicenseShortName") or ext_val(ext, "License"),
                ext_val(ext, "Artist"),
                ext_val(ext, "Credit"),
                ext_val(ext, "DateTimeOriginal") or ext_val(ext, "Date"),
                ext_val(ext, "Institution"),
                ext_val(ext, "ImageDescription"),
                json.dumps(cats, ensure_ascii=False),
            )

            self.con.execute("""
                INSERT OR IGNORE INTO candidates(
                    source, query, title, page_url, image_url,
                    width, height, mime, sha1,
                    license, artist, credit, date, institution, description,
                    categories_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rec)
            rows += 1

        self.con.commit()
        self.logger.info(f"[{q}] inserted {rows} candidates (offset={response.meta['offset']})")

        cont = data.get("continue") or {}
        if "gsroffset" in cont:
            next_offset = int(cont["gsroffset"])
            yield self._api_request(q, offset=next_offset)
