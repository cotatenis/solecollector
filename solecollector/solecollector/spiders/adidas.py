
from scrapy import Request, Spider
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver import Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from urllib.parse import urljoin
import re
import dateparser
from price_parser import Price
from typing import Tuple
from selenium.webdriver.chrome.options import Options
from typing import List
from solecollector.items import SolecollectorItem
from scrapy.utils.project import get_project_settings

class AdidasSpider(Spider):
    
    name = 'adidas'
    settings = get_project_settings()
    version = settings.get("VERSION")
    allowed_domains = ['solecollector.com']
    start_urls = ['https://solecollector.com/api/sneaker-api/lines?brand_id=130&get=22']
    BASE_URL = "https://solecollector.com/"
    BTN_LOCATOR_MODELS = By.XPATH, "//button[contains(text(), 'View More Models')]"
    BTN_LOCATOR_RELEASES = By.XPATH, "//button[contains(text(), 'View More Releases')]"
    PRODUCT_LIST = "//div[contains(@class, 'sd-node__preview-item')]"
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    browser = Chrome(options=chrome_options)

    wdw = WebDriverWait(browser, 5)
    
    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, method='GET', callback=self.parse)

    def parse(self, response):
        r = response.json()
        for data in r:
            partial = data.get("url") 
            url = urljoin(self.BASE_URL, partial)
            self.browser.get(url)
            self.load_more_products(self.BTN_LOCATOR_MODELS)
            href = self.browser.find_elements_by_xpath("//div[contains(@class, 'sd-node__preview-item')]/a")
            href = [d.get_attribute("href") for d in href]
            ######################
            #       MODELS      ##
            ######################
            for partial in href:
                product_url = urljoin(self.BASE_URL, partial)
                self.browser.get(product_url)
                try:
                    product, _, _, product_first_release_date = self.fetch_product_data(url=product_url)
                except TimeoutException:
                    continue
                else:
                    #CHECK FOR MORE RELEASES
                    self.load_more_products(self.BTN_LOCATOR_RELEASES)
                    href_inner = self.fetch_release_href()
                    ######################
                    #       RELEASE     #
                    ######################
                    for partial_inner in href_inner:
                        image_uris = ""
                        release_url = urljoin(self.BASE_URL, partial_inner)
                        self.browser.get(release_url)
                        sku, release_name, _, release_date, price, currency, img_release, breadcrumbs = self.fetch_release_data()
                        if img_release != "":
                            image_uris = f"{self.settings.get('IMAGES_STORE')}{sku}_{img_release.split('/')[-1]}"
                        if len(breadcrumbs) >= 5:
                            brand_division = breadcrumbs[-3]
                        else:
                            brand_division = breadcrumbs[-2]
                        item = SolecollectorItem(**{
                                'brand' : self.name.capitalize(),
                                'brand_division' : brand_division,
                                'product' : product,
                                'product_first_release_date' : product_first_release_date,
                                'image_urls' : [img_release],
                                'image_uris' : image_uris,
                                'release_date' : release_date,
                                'sku' : sku,
                                'release_name' : release_name,
                                'price' : price, 
                                'currency' : currency,
                                'breadcrumbs' : breadcrumbs,
                                'url' : release_url,
                                'spider' : self.name,
                                'spider_version' : self.version
                            })
                        yield item


    def load_more_products(self, locator: Tuple):
        while_exists_btn = True
        while while_exists_btn:
            try:
                btn = self.wdw.until(EC.element_to_be_clickable(locator))
            except (TimeoutException, StaleElementReferenceException):
                while_exists_btn = False
            else:
                self.browser.execute_script("arguments[0].click();", btn)

    def fetch_brand_data(self):
        brand = self.browser.find_element_by_xpath("//div[contains(@class, 'featured-breadcrumb__wrap-container')]/span").text
        raw_brand_num_of_models, raw_brand_num_of_releases = self.browser.find_elements_by_xpath("//div[@class='sd-brand-info__value']") #number of models and releases
        brand_num_of_models = re.search(r"\d+", raw_brand_num_of_models.text).group(0)
        brand_num_of_releases = re.search(r"\d+", raw_brand_num_of_releases.text).group(0)
        return brand, brand_num_of_models, brand_num_of_releases

    def fetch_product_data(self, url):
        product_first_release_date = None
        product_year_release = None
        product_num_releases = None
        try:
            _ = self.wdw.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'sd-brand-info__value')]")))
        except TimeoutException:
            self.logger.warning(f"Something went wrong with {url}.")
            raise TimeoutException
        else:
            product = self.browser.find_element_by_xpath("//div[contains(@class, 'featured-breadcrumb__wrap-container')]/span").text
            try:
                product_year_release = self.browser.find_element_by_xpath("//div[contains(text(), 'Introduced In') and contains(@class, 'sd-brand-info__title')]/..//div[2]")
            except NoSuchElementException:
                pass
            else:
                product_year_release = product_year_release.text
            try:
                product_num_releases = self.browser.find_element_by_xpath("//div[contains(text(), 'Releases Covered') and contains(@class, 'sd-brand-info__title')]/..//div[2]")
            except NoSuchElementException:
                pass
            else:
                product_num_releases = product_num_releases.text
            try:
                product_first_release_date = self.browser.find_element_by_xpath("//div[contains(text(), 'First Release Covered') and contains(@class, 'sd-brand-info__title')]/..//div[2]")
            except NoSuchElementException:
                pass
            else:
                product_first_release_date = product_first_release_date.text
                if product_first_release_date:
                    product_first_release_date = dateparser.parse(product_first_release_date).strftime("%Y-%m-%d")
        return product, product_year_release, product_num_releases, product_first_release_date
    
    def fetch_release_data(self):
        sku = None
        product_release_name = None
        first_release_covered = None
        release_date = None
        price = None
        currency = None
        breadcrumbs = []
        img_release = self.browser.find_element_by_xpath("//div[contains(@class, 'hero__img-container')]/img")
        img_release = img_release.get_attribute("src")
        if 'urcggx.svg' in img_release:
            img_release = ""
        try:
            release_date = self.browser.find_element_by_xpath("//div[contains(text(), 'Release Date') and contains(@class, 'sd-brand-info__title')]/..//div[2]").text
        except NoSuchElementException:
            try:
                first_release_covered = self.browser.find_element_by_xpath("//div[contains(text(), 'First Release Covered') and contains(@class, 'sd-brand-info__title')]/..//div[2]").text
            except NoSuchElementException:
                raise NoSuchElementException
            else:
                first_release_covered = dateparser.parse(first_release_covered).strftime("%Y-%m-%d")
        finally:
                try:
                    sku = self.browser.find_element_by_xpath("//div[contains(text(), 'Style Code') and contains(@class, 'sd-brand-info__title')]/..//div[2]").text
                except NoSuchElementException:
                    pass
                else:
                    if sku == "TBA":
                        sku = None
                try:
                    product_release_name = self.browser.find_element_by_xpath("//div[contains(text(), 'Official Name') and contains(@class, 'sd-brand-info__title')]/..//div[2]").text
                except NoSuchElementException:
                    pass
                try:
                    price = self.browser.find_element_by_xpath("//div[contains(text(), 'Original Sales Price') and contains(@class, 'sd-brand-info__title')]/..//div[2]").text
                except NoSuchElementException:
                    pass
                try:
                    breadcrumbs = self.browser.find_elements_by_xpath("//div[@class='featured-breadcrumb__piece--arrow']//span")
                except NoSuchElementException:
                    pass
                if release_date:
                    release_date = dateparser.parse(release_date).strftime("%Y-%m-%d")
                if breadcrumbs:
                    breadcrumbs = [cat.text for cat in breadcrumbs]
                if isinstance(price, str):
                    rprice = Price.fromstring(price)
                    try:
                        price = float(rprice.amount)
                        currency = rprice.currency
                    except TypeError:
                        pass
        return sku, product_release_name, first_release_covered, release_date, price, currency, img_release, breadcrumbs

    def fetch_release_href(self)-> List[str]:
        href_inner = self.browser.find_elements_by_xpath("//div[contains(@class, 'sd-node__preview-item')]/a")
        href_inner = [d.get_attribute("href") for d in href_inner]
        return href_inner
    
    def fetch_release_results_imgs(self) -> List[str]:
        imgs_inner = self.browser.find_elements_by_xpath("//div[contains(@class, 'sd-node__preview-item')]//img")
        imgs_inner = [d.get_attribute("src") for d in imgs_inner]
        return imgs_inner
