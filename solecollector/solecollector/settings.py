BOT_NAME = 'solecollector'
SPIDER_MODULES = ['solecollector.spiders']
NEWSPIDER_MODULE = 'solecollector.spiders'

LOG_LEVEL = "INFO"
VERSION = "0-1-1"
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36'

ROBOTSTXT_OBEY = False

MAGIC_FIELDS = {
    "timestamp": "$isotime",
    "spider": "$spider:name",
    "url": "$response:url",
}
SPIDER_MIDDLEWARES = {
    "scrapy_magicfields.MagicFieldsMiddleware": 100,
}
SPIDERMON_ENABLED = True
EXTENSIONS = {
    'solecollector.extensions.SentryLogging' : -1,
    'spidermon.contrib.scrapy.extensions.Spidermon': 500,
}
ITEM_PIPELINES = {
    "solecollector.pipelines.DiscordMessenger" : 100,
    "solecollector.pipelines.SoleCollectorImagePipeline" : 200,
    "solecollector.pipelines.GCSPipeline": 300,
}
SPIDERMON_VALIDATION_MODELS = (
    'solecollector.validators.SolecollectorItem',
)
SPIDERMON_SPIDER_CLOSE_MONITORS = (
'solecollector.monitors.SpiderCloseMonitorSuite',
)
SPIDERMON_PERIODIC_MONITORS = {
'solecollector.monitors.PeriodicMonitorSuite': 30, # time in seconds
}
SPIDERMON_VALIDATION_DROP_ITEMS_WITH_ERRORS = False
SPIDERMON_MIN_ITEMS = 2000
SPIDERMON_SENTRY_DSN = ""
SPIDERMON_SENTRY_PROJECT_NAME = ""
SPIDERMON_SENTRY_ENVIRONMENT_TYPE = ""

#GCP
GCS_PROJECT_ID = ""
GCP_CREDENTIALS = ""
GCP_STORAGE = ""
GCP_STORAGE_CRAWLER_STATS = ""
#FOR IMAGE UPLOAD
IMAGES_STORE = f''
IMAGES_THUMBS = {
    '400_400': (400, 400),
}
#DISCORD
DISCORD_WEBHOOK_URL = ""
DISCORD_THUMBNAIL_URL = ""
SPIDERMON_DISCORD_WEBHOOK_URL = ""