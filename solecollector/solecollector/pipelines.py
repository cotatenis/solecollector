from itemadapter import ItemAdapter
from google.cloud import storage
from google.oauth2 import service_account
import datetime
import json
from discord_webhook import DiscordWebhook, DiscordEmbed
from scrapy.exceptions import DropItem
from scrapy.pipelines.images import ImagesPipeline
from scrapy import Request
from io import BytesIO
from scrapy.pipelines.files import FileException

class ImageException(FileException):
    """General image error exception"""

class DiscordMessenger():
    def __init__(self, webwook_url, bot_name, thumbnail) -> None:
        self.webhook = DiscordWebhook(url=webwook_url)
        self.bot_name = bot_name
        self.thumbnail = thumbnail

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            webwook_url=crawler.settings.get("DISCORD_WEBHOOK_URL"),
            thumbnail=crawler.settings.get("DISCORD_THUMBNAIL_URL"),
            bot_name=crawler.settings.get("BOT_NAME"),
        )

    def open_spider(self, spider):
        embed = DiscordEmbed(
            title=f'BOT {self.bot_name}/{spider.name} has started.')
        embed.set_thumbnail(url=self.thumbnail)
        embed.set_timestamp()
        self.webhook.add_embed(embed=embed)
        _ = self.webhook.execute()

    def close_spider(self, spider):
        self.webhook.remove_embeds()
        stats = spider.crawler.stats.get_stats()
        stats_st = stats.get("start_time")
        num_requests = stats.get("downloader/request_count")
        if isinstance(stats_st, str):
            stats_st = datetime.datetime.fromisoformat(stats_st)
        finish_time = datetime.datetime.utcnow()
        elapsed_time_seconds = (finish_time-stats_st)
        rps = str(round(int(num_requests)/elapsed_time_seconds.total_seconds(),2))
        item_scraped_count = stats.get("item_scraped_count")
        embed = DiscordEmbed(
            title=f'BOT {self.bot_name}/{spider.name} has ended.')
        embed.set_thumbnail(url=self.thumbnail)
        embed.set_timestamp()
        # add fields to embed
        embed.add_embed_field(name='Elapsed time', value=str(elapsed_time_seconds))
        embed.add_embed_field(name='Number of products collected', value=item_scraped_count)
        embed.add_embed_field(name='RPS', value=rps, inline=False)
        self.webhook.add_embed(embed=embed)
        _ = self.webhook.execute()

class GCSPipeline:
    def __init__(
        self,
        bucket_name,
        bucket_name_stats,
        project_name,
        credentials,
        bot_name,
        webwook_url,
        thumbnail
    ):
        self.bucket_name = bucket_name
        self.bucket_name_stats = bucket_name_stats
        self.project_name = project_name
        self.credentials = credentials
        self.bot_name = bot_name
        self.thumbnail = thumbnail
        self.webhook_url = webwook_url

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            project_name=crawler.settings.get("GCS_PROJECT_ID"),
            credentials=crawler.settings.get("GCP_CREDENTIALS"),
            bucket_name=crawler.settings.get("GCP_STORAGE"),
            bucket_name_stats=crawler.settings.get("GCP_STORAGE_CRAWLER_STATS"),
            bot_name=crawler.settings.get("BOT_NAME"),
            thumbnail=crawler.settings.get("DISCORD_THUMBNAIL_URL"),
            webwook_url=crawler.settings.get("SPIDERMON_DISCORD_WEBHOOK_URL")
        )

    def open_spider(self, spider):
        self.bucket = self.connect(
            self.project_name, self.bucket_name, self.credentials
        )
        self.bucket_stats = self.connect(
            self.project_name, self.bucket_name_stats, self.credentials
        )
        self.discord = DiscordWebhook(url=self.webhook_url)

    def close_spider(self, spider):
        year = datetime.datetime.now().year
        day = datetime.datetime.now().isoformat().split("T")[0]
        timestamp_fmt = datetime.datetime.now().isoformat().replace("-", "").replace(":", "").split(".")[0]
        stats = spider.crawler.stats.get_stats()
        stats['spider'] = spider.name
        stats_st = stats.get("start_time").isoformat()
        stats['start_time'] = stats_st
        stats['finish_time'] = datetime.datetime.utcnow().isoformat()
        filename = f"{year}/{day}/{self.bot_name}/{timestamp_fmt}_{spider.name}_stats.json"
        blob = self.bucket_stats.blob(filename)
        blob.upload_from_string(json.dumps(stats), content_type="application/json")

    def connect(self, project_name, bucket_name, credentials):
        credentials_obj = service_account.Credentials.from_service_account_file(
            credentials
        )
        client = storage.Client(credentials=credentials_obj, project=project_name)
        return client.get_bucket(bucket_name)

    def upload(self, content: str, filename: str) -> str:
        blob = self.bucket.blob(filename)
        blob.upload_from_string(content, content_type="application/json")
        return None

    def process_item(self, item, spider):
        item_name = type(item).__name__
        raw_item = ItemAdapter(item)
        sku = item['sku']
        if not sku:
            self.missing_sku_field_message(url=raw_item['url'], spider=spider)
            raise DropItem()
        timestamp_fmt = (
            raw_item.get("timestamp", "")
            .replace("-", "")
            .replace(":", "")
            .split(".")[0]
        )
        year = datetime.datetime.now().year
        day = datetime.datetime.now().isoformat().split("T")[0]
        filename = f"{year}/{day}/{self.bot_name}/{timestamp_fmt}_{spider.name}_{raw_item.get('spider_version', '')}_{item_name}_{raw_item.get('sku')}.json"
        self.upload(content=json.dumps(dict(raw_item)), filename=filename)
        return dict(raw_item)

    def missing_sku_field_message(self, url: str, spider) -> None:
        embed = DiscordEmbed(
            title=f'BOT {self.bot_name}/{spider.name} 💀 Missing SKU notifier.')
        embed.set_thumbnail(url=self.thumbnail)
        embed.set_timestamp()
        # add fields to embed
        embed.add_embed_field(name='url', value=url)
        self.discord.add_embed(embed=embed)
        _ = self.discord.execute(remove_embeds=True)

class SoleCollectorImagePipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        if 'image_urls' in item and 'sku' in item:
            sku = item['sku']
            check_image_url = item['image_urls'][0]
            if sku and check_image_url != '':
                for image_url in item['image_urls']:
                    request = Request(url=image_url)
                    request.meta['sku'] = sku
                    yield request
    #FOR THUMBNAIL
    def get_images(self, response, request, info, *, item=None):
        path = self.file_path(request, response=response, info=info, item=item)
        orig_image = self._Image.open(BytesIO(response.body))

        width, height = orig_image.size
        if width < self.min_width or height < self.min_height:
            raise ImageException("Image too small "
                                 f"({width}x{height} < "
                                 f"{self.min_width}x{self.min_height})")

        image, buf = self.convert_image(orig_image)
        yield path, image, buf
        #RETRIEVE SKU INFORMATION
        request.meta['sku'] = item['sku']
        for thumb_id, size in self.thumbs.items():
            thumb_path = self.thumb_path(request, thumb_id, response=response, info=info)
            thumb_image, thumb_buf = self.convert_image(image, size)
            yield thumb_path, thumb_image, thumb_buf

    def thumb_path(self, request, thumb_id, response=None, info=None):
        sku = request.meta['sku']
        thumb_filename = f"{sku}_{request.url.split('/')[-1]}"
        return f'thumbs/{thumb_id}/{thumb_filename}'

    def file_path(self, request, response=None, info=None, *, item=None):
        sku = request.meta['sku']
        return f"{sku}_{request.url.split('/')[-1]}"