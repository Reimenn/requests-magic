from typing import Callable
from .logger import Logger
from .middleware import *

import threading
import time
import hashlib
from .tags import Tags

default_headers: dict = {}


class Request(threading.Thread):

    def __init__(self, url: str, callback: Callable,
                 data: dict = None, method: str = 'GET', headers: dict = None,
                 time_out: int = 10, time_out_wait: int = 5, time_out_retry: int = 3,
                 tags: dict = None,
                 downloader: Callable = requests_downloader,
                 downloader_filter: Callable = requests_downloader_filter,
                 preparse: Callable = None,
                 **kwargs):
        """
        :param headers: request headers, use default_headers if is None
        :param method: http method, default is GET or POST by data
        :param downloader: download function
        :param downloader_filter: call on downloader after
        :param time_out: request max wait time(s)
        :param time_out_wait: retry wait time if time out
        :param time_out_retry: frequency of retry if time out
        :param kwargs: Passed to requests.request by default
        """
        super().__init__()

        if tags is None:
            tags = {}
        if data is None:
            data = {}
        if headers is None:
            headers = default_headers.copy()

        self.url: str = url
        self.data: dict = data
        self.method: str = method
        self.headers: dict = headers

        self.callback: Callable = callback
        self.downloader = downloader
        self.downloader_filter = downloader_filter
        self.tags: dict = tags
        self.scheduler = None

        self.spider = callback.__self__
        from .spider import Spider
        if not isinstance(self.spider, Spider):
            raise MagicError('callback must be a method in spider')

        self.preparse = preparse
        if self.preparse is None:
            self.preparse = self.spider.preparse

        self.start_time: float = -1
        self.total_time: float = -1
        self.time_out: float = time_out
        self.time_out_wait: float = time_out_wait
        self.time_out_retry: int = time_out_retry

        self.kwargs = kwargs

        self.result = None
        self.show_url = self.url if len(self.url) < 40 else '...' + self.url[-37:-1]

    def __str__(self):
        return f"[{self.method}] {self.url}"

    def run(self) -> None:
        self.result = None
        self._call_downloader()
        if self.result is not None:
            self.scheduler.downloader_over(self.result, self)
        else:
            self.scheduler.downloader_abandon(self)

    def md5(self) -> str:
        return hashlib.md5(
            f'{self};{self.data}'.encode('utf-8')
        ).hexdigest()

    def _call_downloader(self) -> None:
        """
        Call downloader and return result, auto retry if time out
        """
        try:
            Logger.info(f"[START {self.method} {len(self.scheduler.link_requests)}] {self.show_url}")
            self.start_time = time.time()
            result = self.downloader(self)
            self.total_time = time.time() - self.start_time
            Logger.info(f"[OVER {self.method} {round(self.total_time, 2)}s] {self.show_url}")
            self.downloader_filter(result, self)
            self.result = result
        except Exception as e:
            self._parse_downloader_exception(e)

    def _parse_downloader_exception(self, e: Exception) -> None:
        """
        parse downloader exception, auto call self._call_downloader()
        """
        if isinstance(e, RequestCanRetryError):
            if isinstance(e, RequestTimeoutError):
                # time out retry
                message = f'Request is time out to {self.url}. '
                if self.time_out_retry > 0:
                    message += \
                        f'Try again in {self.time_out_wait} seconds. ({self.time_out_retry - 1} remaining)'
                else:
                    message += 'Gave up the request'
                Logger.warning(message)

                if self.time_out_retry > 0:
                    self.time_out_retry -= 1
                    time.sleep(self.time_out_wait)
                    self._call_downloader()
            else:
                Logger.warning(f'Retry {self}')
                self._call_downloader()
        elif isinstance(e, RequestHttpError):
            Logger.error(e)
        else:
            Logger.error(e)
