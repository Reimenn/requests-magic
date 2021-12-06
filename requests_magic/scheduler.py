from typing import List, Iterable, Union
from .request import Request
from .item import Item
from .pipeline import Pipeline
from .logger import Logger
from .exceptions import *
import threading
import time


class Scheduler(threading.Thread):
    """
    调度器，核心组件，负责请求管理与 item 转发
    """

    def __init__(self, pipelines: Union[Pipeline, List[Pipeline]], max_link: int = 12,
                 request_interval: float = 0, distinct: bool = True):
        """
        调度器，核心组件，负责请求管理与 item 转发
        Parameters
        ----------
        pipelines
            管道们
        max_link
            最大连接数，默认：12
        request_interval
            请求间隔时间，默认：0秒
        distinct
            是否开启去重，默认开启
        """
        super().__init__()
        self.distinct = distinct
        if isinstance(pipelines, list):
            self.pipeline_list: List[Pipeline] = pipelines
        elif isinstance(pipelines, Pipeline):
            self.pipeline_list: List[Pipeline] = [pipelines]
        else:
            raise SchedulerError('pipeline must be a Pipeline or Pipeline list')
        self.max_link: int = max_link
        self.request_interval: float = request_interval
        self.requests: List[Request] = []
        self.link_requests: List[Request] = []
        self.requests_md5: List[str] = []
        for pl in self.pipeline_list:
            if not pl.daemon:
                pl.start()

    def add_request(self, request: Request) -> None:
        """
        添加一个新的请求（不会立刻执行）
        Parameters
        ----------
        request
            请求
        """
        Logger.debug(f"Add new request {request}, list requests len:{len(self.requests)}")
        md5: str = request.md5()
        if self.distinct and md5 in self.requests_md5:
            Logger.warning(f'Repeated request: {request}')
            return
        request.scheduler = self
        self.requests.append(request)
        self.requests_md5.append(md5)

    def add_item(self, item: Item, from_spider=None) -> None:
        """
        添加一个新的 Item，这会转发给每个管道
        Parameters
        ----------
        item
            Item
        from_spider
            产生这个 Item 的爬虫，可以为空，空了也没啥问题
        """
        Logger.debug(f"Add new item {item}")
        item.scheduler = self
        item.spider = from_spider
        for pl in self.pipeline_list:
            if pl.acceptable(item):
                pl.add_item(item)

    def add_callback_result(self, result_ite, from_spider=None) -> None:
        """
        自动解析解析函数返回的结果，会自动迭代、添加请求或转发 Item
        Parameters
        ----------
        result_ite
            结果
        from_spider
            产生结果的爬虫
        """
        if result_ite is None:
            return
        if not isinstance(result_ite, Iterable):
            result_ite = [result_ite]
        for result in result_ite:
            if isinstance(result, Request):
                self.add_request(result)
            elif isinstance(result, Item):
                self.add_item(result, from_spider=from_spider)
            else:
                Logger.error(
                    f"Cannot handle {str(type(result))}, " +
                    f"Please do not generate it in spider methods.")

    def run(self) -> None:
        """
        开始处理请求队列
        """
        while True:
            try:
                if len(self.link_requests) < self.max_link and self.requests:
                    request = self.requests[0]
                    del self.requests[0]
                    request.start()
                    self.link_requests.append(request)
                    # rest
                    if self.request_interval > 0:
                        time.sleep(self.request_interval)
            except Exception as e:
                Logger.error(e)

    def downloader_finish(self, result, request: Request) -> None:
        """
        当下载完成时，由 Request 调用。
        这会在请求队列中移除这个请求并自动调用解析函数
        """
        Logger.debug(f"Over a request {request}")
        if request not in self.link_requests:
            Logger.error(f"The completed download is not in link_request list. {request}")
            return
        self.link_requests.remove(request)
        result = request.preparse(result, request)
        call = request.callback(result, request)
        self.add_callback_result(call, request.spider)

    def downloader_abandon(self, request: Request) -> None:
        """
        放弃一个请求
        """
        Logger.debug(f"Abandon a request {request}")
        if request not in self.link_requests:
            Logger.error(f"The abandoned download is not in link_request list. {request}")
            return
        self.link_requests.remove(request)

    def downloader_retry(self, request: Request) -> None:
        """
        重试一个请求
        """
        if request not in self.link_requests:
            Logger.error(f"The retry download is not in link_request list. {request}")
            return
        if request in self.requests:
            Logger.error(f"The retry download have not started to request. {request}")
            return
        self.link_requests.remove(request)
        self.requests.append(request)
