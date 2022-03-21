# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from scrapy import Field
from scrapy.item import Item


class SolecollectorItem(Item):
    brand = Field()
    brand_division = Field()
    product = Field()
    product_first_release_date = Field()
    image_urls = Field()
    image_uris = Field()
    release_date = Field()
    sku = Field()
    release_name = Field()
    price = Field()
    currency = Field()
    breadcrumbs = Field()
    url = Field()
    spider = Field()
    spider_version = Field()
    timestamp = Field()

