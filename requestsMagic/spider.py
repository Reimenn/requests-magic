from requestsMagic.request import Request
from requestsMagic.Item import Item
import requests
from typing import Callable


class Spider:
    def start(self):
        """
        Start the first request from here, Can return/yield requests/items, or lists containing them
        """
        pass

    def parse(self, result: requests.Response, request: Request):
        """
        Default parse function, Can return/yield requests/items, or lists containing them
        """
        pass

    def request(self, url: str, data: dict = None, callback: Callable = None,
                meta: dict = {}, headers: dict = {}) -> Request:
        """
        Create a request
        (it is not recommended to instantiate the Request class directly, Using this method is the best)
        :param callback: parse function
        :param meta: extra information
        """
        return Request(url=url, spider=self,
                       callback=callback if callback else self.parse,
                       data=data, meta=meta, headers=headers)

    def item(self, data: dict, meta: dict = {}) -> Item:
        """
        Create a item
        (it is not recommended to instantiate the Item class directly, Using this method is the best)
        :param meta: extra information
        """
        return Item(data, spider=self, meta=meta)
