from scrapy import Spider

from scrapy_router import Router


class ExampleSpider(Spider):
    name = "example"
    start_urls = ["http://www.example.com/catalogue"]

    router = Router()
    parse = router.dispatcher()

    @router("example.com/catalogue|")
    def parse_catalogue(self, response):
        # implies `callback=self.parse_category`
        yield from response.follow_all(css=".category-link")

    @router("example.com/category/")
    def parse_category(self, response):
        # implies `callback=self.parse_item`
        yield from response.follow_all(css=".item-link")

    @router("example.com/item/")
    def parse_item(self, response):
        yield {"title": response.css("h1::text").get()}
