from typing import Callable
from .logger import Logger
from .exceptions import *
import requests
import threading
import time
import hashlib

default_headers: dict = {}


def requests_download(request) -> requests.Response:
    """
    Default download function (downloader)
    """
    request: Request
    response: requests.Response
    try:
        response = requests.request(
            request.method, request.url,
            data=request.data, headers=request.headers,
            timeout=request.time_out
        )
    except requests.Timeout as timeoutError:
        raise RequestTimeoutError(request)
    if response.status_code >= 400:
        raise RequestHttpError(request, response.status_code)
    return response


class Request(threading.Thread):

    def __init__(self, url: str, callback: Callable,
                 data: dict = None, meta: dict = None,
                 method: str = None, headers: dict = None,
                 time_out: int = 10, time_out_wait: int = 5, time_out_retry: int = 3,
                 downloader: Callable = requests_download):
        """
        :param headers: request headers, use default_headers if is None
        :param method: http method, default is GET or POST by data
        :param downloader: download function
        :param time_out: request max wait time(s)
        :param time_out_wait: retry wait time if time out
        :param time_out_retry: frequency of retry if time out
        """
        super().__init__()

        if meta is None:
            meta = {}
        if data is None:
            data = {}
        if headers is None:
            headers = default_headers.copy()
        self.url: str = url
        self.data: dict = data
        self.callback: Callable = callback
        self.headers: dict = headers
        if method:
            self.method: str = method
        else:
            self.method: str = 'POST' if self.data else 'GET'

        self.scheduler = None

        self.downloader = downloader
        self.meta: dict = meta
        self.start_time: float = -1
        self.time: float = -1

        self.time_out_wait = time_out_wait
        self.time_out_retry = time_out_retry
        self.time_out = time_out

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
        result = None
        # Break when the request is complete
        while True:
            try:
                Logger.info(f"[START {self.method} {len(self.scheduler.link_requests)}] {show_url}")
                self.start_time = time.time()
                result = self.downloader(self)
                self.time = time.time() - self.start_time
                Logger.info(f"[OVER {self.method} {round(self.time, 2)}s] {show_url}")
                # complete
                break
            except RequestCanRetryError as e:
                if isinstance(e, RequestTimeoutError):
                    # time out retry
                    e: RequestTimeoutError
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
                        continue  # retry
                    else:
                        self.scheduler.downloader_abandon(self)
                        return
                else:
                    Logger.warning(f'Retry {self}')
                    continue
            except RequestHttpError as e:
                Logger.error(e)
                self.scheduler.downloader_abandon(self)
                return
            except Exception as e:
                Logger.error(e)
                self.scheduler.downloader_abandon(self)
                return

        if result is None:
            self.scheduler.downloader_abandon(self)
            raise Exception('result is None, This is an unknown error')
        self.scheduler.downloader_over(result, self)

    def md5(self) -> str:
        return hashlib.md5(
            f'{self};{self.data}'.encode('utf-8')
        ).hexdigest()
