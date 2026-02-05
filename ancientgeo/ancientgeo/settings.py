# AncientWorld Scrapy Project

BOT_NAME = "ancientgeo"

SPIDER_MODULES = ["ancientgeo.spiders"]
NEWSPIDER_MODULE = "ancientgeo.spiders"

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# Download delay and autothrottle
DOWNLOAD_DELAY = 0.5
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 4.0

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# Timeout
DOWNLOAD_TIMEOUT = 60

# HTTP Cache (helps with restarts)
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = "data/httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 400, 403, 404, 408]
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# User agent
USER_AGENT = "AncientWorld/1.0 (https://github.com/robertwaltos/AncientWorld; research crawler)"

# Item pipelines
ITEM_PIPELINES = {
    "ancientgeo.pipelines.SqlitePipeline": 100,
    "scrapy.pipelines.images.ImagesPipeline": 200,
}

# Images configuration
IMAGES_STORE = "D:/PythonProjects/AncientWorld/data/large/images"  # Large dedicated drive for 500GB corpus
IMAGES_MIN_HEIGHT = 900
IMAGES_MIN_WIDTH = 900
IMAGES_EXPIRES = 365  # days

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"

# Feed exports (optional - for debugging)
FEEDS = {
    "data/items_%(time)s.jsonl": {
        "format": "jsonlines",
        "encoding": "utf8",
        "store_empty": False,
        "indent": None,
    }
}

# Memory limits (important for long-running crawls)
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 2048
MEMUSAGE_WARNING_MB = 1536

# Request fingerprinter
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
