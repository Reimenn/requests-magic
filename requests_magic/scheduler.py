from typing import List, Iterable
from .request import Request
from .item import Item
from .pipeline import Pipeline
from .logger import Logger
import threading
import time


class Scheduler(threading.Thread):

    def __init__(self, pipeline, max_link: int = 12,
                 request_interval: float = 0, distinct: bool = True):
        """
        A request scheduler, which is the core of the crawler
        """
        super().__init__()
        self.distinct = distinct
        self.pipeline: Pipeline = pipeline
        self.max_link: int = max_link
        self.request_interval: float = request_interval
        self.requests: List[Request] = []
        self.link_requests: List[Request] = []
        self.requests_md5: List[str] = []
        self.pipeline.start()

    def add_request(self, request: Request) -> None:
        md5: str = request.md5()
        if self.distinct and md5 in self.requests_md5:
            Logger.warning(f'Repeated request: {request}')
            return
        request.scheduler = self
        self.requests.append(request)
        self.requests_md5.append(md5)

    def add_item(self, item: Item) -> None:
        item.scheduler = self
        self.pipeline.add_item(item)

    def add_callback_result(self, result_ite) -> None:
        if result_ite is None:
            return
        if not isinstance(result_ite, Iterable):
            result_ite = [result_ite]
        for result in result_ite:
            if isinstance(result, Request):
                self.add_request(result)
            elif isinstance(result, Item):
                self.add_item(result)
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
        # remove request
        self.link_requests.remove(request)
        call = request.callback(result, request)
        self.add_callback_result(call)

    def downloader_abandon(self, request: Request) -> None:
        """
        abandon a request
        """
        self.link_requests.remove(request)
