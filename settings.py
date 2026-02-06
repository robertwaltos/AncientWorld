BOT_NAME = "ancientgeo"

ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 1.0
CONCURRENT_REQUESTS_PER_DOMAIN = 2

ITEM_PIPELINES = {
    "ancientgeo.pipelines.SqlitePipeline": 100,
    "scrapy.pipelines.images.ImagesPipeline": 200,
}

# Where images are saved
IMAGES_STORE = "data/images"

# Filter tiny images
IMAGES_MIN_HEIGHT = 900
IMAGES_MIN_WIDTH = 900

# Optional: reduce over-fetching
LOG_LEVEL = "INFO"
