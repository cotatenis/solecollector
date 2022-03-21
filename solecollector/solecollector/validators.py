from schematics.models import Model
from schematics.types import URLType, StringType, ListType, FloatType, DateTimeType, BooleanType, ModelType, IntType

class SolecollectorItem(Model):
    brand = StringType(required=True)
    brand_division = StringType(required=True)
    product = StringType(required=True)
    product_first_release_date = DateTimeType()
    image_urls = ListType(URLType)
    image_uris = StringType
    release_date = DateTimeType()
    sku = StringType(required=True)
    release_name = StringType(required=True)
    price = FloatType()
    currency = StringType()
    breadcrumbs = ListType(StringType)
    url = URLType()