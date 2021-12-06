"""
请求类和请求线程类
"""

from typing import Callable
from .logger import Logger
from .middleware import *
import threading
import time
import hashlib

default_headers: dict = {}


class Request:
    """
    表示一个请求，这里会自动创建 RequestThread
    """

    def __init__(self, url: str, callback: Callable,
                 data: dict = None, method: str = 'GET', headers: dict = None,
                 time_out: int = 10, time_out_wait: int = 15, time_out_retry: int = 3,
                 tags: dict = None,
                 downloader: Callable = requests_downloader,
                 downloader_filter: Callable = requests_downloader_filter,
                 preparse: Callable = None,
                 name: str = '',
                 **kwargs):
        """
        表示一个请求，这里会自动创建 RequestThread
        Parameters
        ----------
        url
            请求的目标地址
        callback
            回调解析函数，这必须是爬虫类中的方法
        data
            请求数据
        method
            请求方法，默认：GET
        headers
            请求头，如果为空，则从 requests_magic.request.default_headers copy一份
        time_out
            超时时限，默认：10秒
        time_out_wait
            超时后重试前的等待时间，默认：15秒
        time_out_retry
            超时重试次数，默认：3次
        tags
            标签，用来记录一些额外内容，可以用来在解析函数、下载中间件等东西之间传递信息
        downloader
            下载器，这个方法需要有一个参数表示 Request 并返回请求结果，默认使用基于 requests 实现
        downloader_filter
            下载过滤器，这个方法需要有两个参数分别表示 请求结果 和 Request，默认使用基于 requests 实现
        preparse
            预解析器，默认使用解析函数所在爬虫类的 parparse 方法
        name
            请求的名字，希望能帮助 debug
        kwargs
            直接记录在自己的 kwargs 属性上，默认的 requests 下载器会把这里的值添加到 requests.request 方法的参数上
        """
        super().__init__()

        self.name = name
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
            raise RequestError('callback must be a method in spider')

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

        self.thread: RequestThread = None

    def __str__(self) -> str:
        return f"[Request - {self.name}]" if self.name else ''

    def start(self):
        """
        开始下载，自动创建 RequestThread，下载完成后会自动调用调度器的方法
        """
        if self.thread:
            Logger.error(f"{self} downloading, dont start")
        self.thread = RequestThread(self)
        self.thread.start()

    def md5(self) -> str:
        """
        根据某些属性计算自己的md5，用于url去重，默认时使用 请求方法、url、data、time_out_retry 按照 utf-8 编码计算
        Returns
        -------
        md5字符串
        """
        return hashlib.md5(
            f'{self.method};{self.url};{self.data};{self.time_out_retry}'.encode('utf-8')
        ).hexdigest()

    def retry(self) -> None:
        """
        重新请求
        """
        if not self.scheduler:
            Logger.error(f'{self} Requests that have not been requested cannot be retry')
            return
        self.start_time = -1
        self.total_time = -1
        self.result = None
        self.stop_thread()
        self.scheduler.downloader_retry(self)

    def abandon(self) -> None:
        """
        放弃请求
        """
        self.stop_thread()
        self.scheduler.downloader_abandon(self)

    def finish(self) -> None:
        """
        完成请求
        """
        self.stop_thread()
        self.scheduler.downloader_finish(self)

    def stop_thread(self) -> None:
        """
        终止请求线程
        """
        del self.thread
        self.thread = None


class RequestThread(threading.Thread):
    """
    请求的下载线程
    """

    def __init__(self, request: Request):
        """
        请求的下载线程
        Parameters
        ----------
        request
            请求本地
        """
        super(RequestThread, self).__init__()
        self.request = request

    def run(self) -> None:
        """
        开始下载
        """
        self.request.result = None
        self.call_downloader()
        if self.request.result is None:
            return
        if self.request.thread != self:
            return
        self.request.finish()

    def call_downloader(self) -> None:
        """
        调用下载器并纪录结果到 Request，可能会触发重试、放弃等操作
        """
        try:
            Logger.info(
                f"{self.request} [START] {self.request.show_url}")
            self.request.start_time = time.time()
            result = self.request.downloader(self.request)
            self.request.total_time = time.time() - self.request.start_time
            Logger.info(f"{self.request} [OVER {round(self.request.total_time, 2)}s] {self.request.show_url}")
            self.request.downloader_filter(result, self.request)
            self.request.result = result
        except Exception as e:
            self.parse_downloader_exception(e)

    def parse_downloader_exception(self, e: Exception) -> None:
        """
        解析调用下载器时得到的错误，用来判断是否要重试、放弃等
        """
        retry = False

        if isinstance(e, RequestCanRetryError):
            # to retry
            retry = True
            if isinstance(e, RequestTimeoutError):
                # retry by time_out_retry count
                message = f'{self.request} Request is time out to {self.request.url}. '
                if self.request.time_out_retry > 0:
                    message += \
                        f'Try again in {self.request.time_out_wait} seconds. ({self.request.time_out_retry - 1} remaining)'
                else:
                    message += 'Gave up the request'
                Logger.warning(message)

                if self.request.time_out_retry > 0:
                    self.request.time_out_retry -= 1
                    time.sleep(self.request.time_out_wait)
                else:
                    retry = False
            else:
                Logger.warning(f'{self.request} Retry {self.request}')
                retry = True
        else:
            Logger.error(f'{self.request} {e}')

        if self.request.thread != self:
            return

        if retry:
            self.request.retry()
        else:
            self.request.abandon()
