import scrapy

class ImageAsset(scrapy.Item):
    source = scrapy.Field()          # e.g., wikimedia_commons
    query = scrapy.Field()           # search keyword that found it
    title = scrapy.Field()           # file title
    page_url = scrapy.Field()        # description page
    image_urls = scrapy.Field()      # required by ImagesPipeline
    images = scrapy.Field()          # filled by pipeline

    width = scrapy.Field()
    height = scrapy.Field()
    mime = scrapy.Field()
    sha1 = scrapy.Field()            # from Commons
    license = scrapy.Field()
    credit = scrapy.Field()
    artist = scrapy.Field()
    date = scrapy.Field()
    institution = scrapy.Field()
    description = scrapy.Field()
    categories = scrapy.Field()
