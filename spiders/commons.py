import scrapy
from urllib.parse import urlencode
from ancientgeo.items import ImageAsset

# Wikimedia Commons API notes:
# - generator=search searches pages (including File: pages)
# - prop=imageinfo with iiprop=url|size|mime|sha1|extmetadata gives direct download URL + licensing metadata

class CommonsSpider(scrapy.Spider):
    name = "commons"
    allowed_domains = ["commons.wikimedia.org"]
    custom_settings = {
        # Keep the crawl lightweight; increase later
        "DOWNLOAD_DELAY": 1.0,
    }

    def start_requests(self):
        # You can grow this list (or load from a file)
        queries = [
            # Windows & tracery
            "rose window",
            "gothic tracery",
            "bar tracery",
            "wheel window",
            "oculus window",
            # Facades & elevations
            "gothic cathedral facade",
            "roman basilica facade",
            "cathedral west front",
            "architectural elevation medieval",
            # Geometric construction / ornament
            "geometric pattern medieval",
            "islamic geometric pattern",
            "muqarnas",
            "girih",
            "zellige",
            "mashrabiya",
            "stereotomy",
            "stone carving pattern",
        ]

        for q in queries:
            yield self._api_request(q, offset=0)

    def _api_request(self, q: str, offset: int):
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            # Focus on file pages by asking for "File:" in the search query; not perfect but helps
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

        for p in pages:
            title = p.get("title")
            ii = (p.get("imageinfo") or [None])[0]
            if not ii:
                continue

            url = ii.get("url")
            if not url:
                continue

            ext = ii.get("extmetadata") or {}

            def ext_val(key):
                v = ext.get(key)
                if isinstance(v, dict):
                    return v.get("value")
                return None

            # Categories returned as list of dicts with 'title'
            cats = [c.get("title") for c in (p.get("categories") or []) if c.get("title")]

            item = ImageAsset(
                source="wikimedia_commons",
                query=q,
                title=title,
                page_url=ii.get("descriptionurl"),
                image_urls=[url],
                width=ii.get("width"),
                height=ii.get("height"),
                mime=ii.get("mime"),
                sha1=ii.get("sha1"),
                license=ext_val("LicenseShortName") or ext_val("License"),
                artist=ext_val("Artist"),
                credit=ext_val("Credit"),
                date=ext_val("DateTimeOriginal") or ext_val("Date"),
                institution=ext_val("Institution"),
                description=ext_val("ImageDescription"),
                categories=cats,
            )
            yield item

        # Pagination
        cont = data.get("continue") or {}
        if "gsroffset" in cont:
            next_offset = int(cont["gsroffset"])
            yield self._api_request(q, offset=next_offset)
