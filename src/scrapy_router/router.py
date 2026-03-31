from collections.abc import Callable
from typing import Any, Concatenate, Protocol, TypeAlias, TypeVar

from url_matcher import Patterns, URLMatcher


class Response(Protocol):
    url: str


Spider: TypeAlias = object
Callback: TypeAlias = Callable[Concatenate[Response, ...], Any]
CallbackT = TypeVar("CallbackT", bound=Callback)


class Router:
    """URL-based router for Scrapy spiders.

    Provides declarative URL routing for spider callbacks using URL patterns.
    Instead of manually specifying callbacks, decorate methods with
    `@router(pattern)` and use `router.dispatcher()` as the spider's `parse()`
    method (Scrapy's default callback for requests without an explicitly
    assigned callback).

    Example:
        ```python
        class ExampleSpider(scrapy.Spider):
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
        ```
    """

    matcher: URLMatcher

    def __init__(self, matcher: URLMatcher | None = None) -> None:
        """Initialize the router.

        Args:
            matcher: Optional `URLMatcher` instance. If omitted, a new
                `URLMatcher` is created.
        """
        self.matcher = URLMatcher() if matcher is None else matcher

    def dispatch(self, response: Response, spider: Spider, **kwargs) -> Any | None:
        """Dispatch a response to the matching callback.

        Matches the response URL against registered patterns and calls the
        resolved callback on the spider. Returns `None` if no match is found or
        the resolved callback is not callable.

        Args:
            response: The Scrapy response object to dispatch.
            spider: The spider instance whose callback should be called.
            **kwargs: Additional keyword arguments passed to the callback.

        Returns:
            The return value of the matched callback, or `None` if no suitable
            callback is found.

        Example:
            ```python
            def parse(self, response, **kwargs):
                return self.router.dispatch(response, spider=self, **kwargs)
            ```

        Note:
            This is typically called indirectly via `dispatcher()`, which
            creates a callback suitable for use as a spider's `parse()` method.
        """
        callback = self.matcher.match(response.url)
        if isinstance(callback, str):
            callback = getattr(spider, callback, None)
        if not callable(callback):
            return None
        return callback(spider, response, **kwargs)

    def dispatcher(self) -> Callback:
        """Create a callback suitable for the spider's `parse()` method.

        Returns a callback function that can be assigned to a spider's `parse()`
        method. The returned callback matches the response URL against
        registered patterns and calls the corresponding callback on the spider.

        Returns:
            A callback function compatible with a spider's `parse()` method.

        Examples:
            ```python
            router = Router()
            parse = router.dispatcher()
            ```

        Note:
            The returned callback is equivalent to:
            ```python
            def parse(self, response, **kwargs):
                return self.router.dispatch(response, spider=self, **kwargs)
            ```
        """

        def callback(spider: Spider, response: Response, **kwargs):
            return self.dispatch(response, spider, **kwargs)

        return callback

    def route(
        self, include: str | list[str], exclude: str | list[str] | None = None
    ) -> Callable[[CallbackT], CallbackT]:
        """Register a callback for URL patterns.

        Decorates a spider method to handle responses matching the given
        URL patterns. The decorated method will be called automatically when
        `dispatcher()` matches a URL.

        Args:
            include: URL pattern(s) to match. Can be a single pattern string
                or a list of patterns. Patterns use url-matcher syntax.
            exclude: Optional URL pattern(s) to exclude. Can be a single
                pattern string or a list of patterns.

        Returns:
            A decorator that registers the callback.

        Example:
            ```python
            router = Router()

            @router("example.com/items/")
            def parse_items(self, response):
                pass

            @router(["example.com/cat/", "example.com/dog/"])
            def parse_pets(self, response):
                pass

            @router("example.com/", exclude="example.com/admin/")
            def parse_public(self, response):
                pass
            ```
        """

        include = [include] if isinstance(include, str) else include
        exclude = [exclude] if isinstance(exclude, str) else exclude

        def wrapper(callback: CallbackT) -> CallbackT:
            patterns = Patterns(include, exclude)
            self.matcher.add_or_update(callback, patterns)
            return callback

        return wrapper

    def __call__(
        self, include: str | list[str], exclude: str | list[str] | None = None
    ) -> Callable[[CallbackT], CallbackT]:
        """Allow using router instance directly as a decorator.

        This is an alias for `route()`, allowing `@router(...)` syntax
        instead of `@router.route(...)`.

        Args:
            include: URL pattern(s) to match.
            exclude: Optional URL pattern(s) to exclude.

        Returns:
            A decorator that registers the callback.

        Example:
            ```python
            router = Router()

            # These are equivalent:
            @router("example.com/")
            def parse(self, response):
                pass

            @router.route("example.com/")
            def parse(self, response):
                pass
            ```
        """
        return self.route(include, exclude)
