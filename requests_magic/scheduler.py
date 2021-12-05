from typing import List, Iterable, Union
from .request import Request
from .item import Item
from .pipeline import Pipeline
from .logger import Logger
from .exceptions import *
import threading
import time


class Scheduler(threading.Thread):

    def __init__(self, pipeline: Union[Pipeline, List[Pipeline]], max_link: int = 12,
                 request_interval: float = 0, distinct: bool = True):
        """
        A request scheduler, which is the core of the crawler
        """
        super().__init__()
        self.distinct = distinct
        if isinstance(pipeline, list):
            self.pipeline_list: List[Pipeline] = pipeline
        elif isinstance(pipeline, Pipeline):
            self.pipeline_list: List[Pipeline] = [pipeline]
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
        md5: str = request.md5()
        if self.distinct and md5 in self.requests_md5:
            Logger.warning(f'Repeated request: {request}')
            return
        request.scheduler = self
        self.requests.append(request)
        self.requests_md5.append(md5)

    def add_item(self, item: Item, from_spider=None) -> None:
        item.scheduler = self
        item.spider = from_spider
        for pl in self.pipeline_list:
            if pl.acceptable(item):
                pl.add_item(item)

    def add_callback_result(self, result_ite, from_spider=None) -> None:
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
                Logger.warning(
                    f"Cannot handle {str(type(result))}, " +
                    f"Please do not generate it in spider methods.")

    def run(self) -> None:
        # Create link
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

    def downloader_over(self, result, request: Request) -> None:
        """
        Call from request. When the request is completed,
        remove the request, execute the callback and process the result
        """
        self.link_requests.remove(request)
        result = request.preparse(result, request)
        call = request.callback(result, request)
        self.add_callback_result(call, request.spider)

    def downloader_abandon(self, request: Request) -> None:
        """
        abandon a request
        """
        self.link_requests.remove(request)
