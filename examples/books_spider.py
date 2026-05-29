from collections.abc import Iterator

from scrapy import Spider
from scrapy.http import HtmlResponse, Request

from scrapy_router import Router


class BooksSpider(Spider):
    name = "books"
    start_urls = ["http://books.toscrape.com/"]

    router = Router()
    parse = router.dispatcher()

    @router("books.toscrape.com/|")
    def parse_home(self, response: HtmlResponse) -> Iterator[Request]:
        yield from response.follow_all(css=".side_categories a[href*='/books/']")

    @router("books.toscrape.com/catalogue/category/books/")
    def parse_category(self, response: HtmlResponse) -> Iterator[Request]:
        yield from response.follow_all(css=".product_pod a")
        yield from response.follow_all(css=".next a")

    @router("books.toscrape.com/catalogue/")
    def parse_book(self, response: HtmlResponse) -> Iterator:
        yield {
            "title": response.css("h1::text").get(),
            "price": response.css(".price_color::text").get(),
        }
