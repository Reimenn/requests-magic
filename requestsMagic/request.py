from typing import Callable
from requestsMagic.logger import logger
import requests
import threading
import time


def requests_download(request) -> requests.Response:
    """
    Default download function (downloader)
    """
    request: Request
    return requests.request(request.method, request.url, data=request.data, headers=request.headers)


class Request(threading.Thread):
    def __init__(self, url: str, callback: Callable, spider=None, data: dict = {}, headers: dict = {}, method: str = '',
                 downloader: Callable = requests_download, meta: dict = {}):
        """
        :param downloader: download function
        """
        super().__init__()
        self.url: str = url
        self.data: dict = data
        self.callback: Callable = callback
        self.spider = spider
        self.headers: dict = headers
        self.method: str = 'POST' if self.data else 'GET'
        if method:
            self.method = method
        self.downloader = downloader
        self.meta: dict = meta
        self.scheduler = None
        self.start_time: float = -1
        self.time: float = -1

    def __getitem__(self, item):
        return self.meta[item]

    def __setitem__(self, key, value):
        self.meta[key] = value

    def has_key(self, key) -> bool:
        """
        KEY exist in META
        """
        return key in self.meta.keys()

    def __str__(self):
        return f"[{self.method}] {self.url}"

    def run(self) -> None:
        show_url = self.url if len(self.url) < 40 else '...' + self.url[-37:-1]
        logger.info(f"[START {self.method} {len(self.scheduler.link_requests)}] {show_url}")
        self.start_time = time.time()
        result = self.downloader(self)
        self.time = time.time() - self.start_time
        logger.info(f"[OVER {self.method} {round(self.time, 2)}s] {show_url}")
        self.scheduler.downloader_over(result, self)
