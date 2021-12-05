from typing import Callable
from .request import Request
from .item import Item
import requests
import warnings


class Spider:
    def start(self):
        """
        Start the first request from here, Can return/yield requests/items, or lists containing them
        """
        pass

    def parse(self, result: requests.Response, request: Request):
        """
        example to parse function, Can return/yield requests/items, or lists containing them
        """
        pass

    def preparse(self, result: requests.Response, request: Request) -> requests.Response:
        """
        call when callback before, return to callback result
        """
        return result

    def request(self, url: str, callback: Callable, data: dict = None,
                tags: dict = None, headers: dict = None, **kwargs) -> Request:
        """
        Create a request
        (it is not recommended to instantiate the Request class directly, Using this method is the best)
        :param headers:  headers
        :param data: data
        :param url: url
        :param callback: parse function
        :param tags: extra information
        """
        warnings.warn("Recommend direct instantiation Request", DeprecationWarning)
        if tags is None:
            tags = {}
        if headers is None:
            headers = {}
        return Request(url=url,
                       callback=callback if callback else self.parse,
                       data=data, tags=tags, headers=headers, **kwargs)

    def item(self, data: dict, tags: dict = None, **kwargs) -> Item:
        """
        Create a item
        (it is not recommended to instantiate the Item class directly, Using this method is the best)
        :param data: data
        :param tags: extra information
        """
        warnings.warn("Recommend direct instantiation Item", DeprecationWarning)
        if tags is None:
            tags = {}
        return Item(data, tags=tags, **kwargs)
