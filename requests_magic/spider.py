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

    def request(self, url: str, callback: Callable, data: dict = None,
                meta: dict = None, headers: dict = None) -> Request:
        """
        Create a request
        (it is not recommended to instantiate the Request class directly, Using this method is the best)
        :param headers:  headers
        :param data: data
        :param url: url
        :param callback: parse function
        :param meta: extra information
        """
        warnings.warn("Recommend direct instantiation Request", DeprecationWarning)
        if meta is None:
            meta = {}
        if headers is None:
            headers = {}
        return Request(url=url,
                       callback=callback if callback else self.parse,
                       data=data, meta=meta, headers=headers)

    def item(self, data: dict, meta: dict = None) -> Item:
        """
        Create a item
        (it is not recommended to instantiate the Item class directly, Using this method is the best)
        :param data: data
        :param meta: extra information
        """
        warnings.warn("Recommend direct instantiation Item", DeprecationWarning)
        if meta is None:
            meta = {}
        return Item(data, meta=meta)
