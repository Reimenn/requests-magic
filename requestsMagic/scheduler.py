from typing import List, Iterable
from requestsMagic.request import Request
from requestsMagic.Item import Item
from requestsMagic.pipeline import Pipeline
from requestsMagic.logger import logger
import threading
import time


class Scheduler(threading.Thread):

    def __init__(self, pipeline, max_link: int = 12, request_interval: float = 0, reservation_request: int = 50):
        """
        A request scheduler, which is the core of the crawler
        """
        super().__init__()
        self.reservation_request = reservation_request
        self.pipeline: Pipeline = pipeline
        self.max_link: int = max_link
        self.request_interval: float = request_interval
        self.requests: List[Request] = []
        self.link_requests: List[Request] = []
        self.over_requests: List[Request] = []

        self.pipeline.start()

    def add_request(self, request: Request) -> None:
        request.scheduler = self
        self.requests.append(request)

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
                logger.warning(
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
                logger.error(e)

    def downloader_over(self, result, request: Request) -> None:
        """
        Call from request. When the request is completed, remove the request, execute the callback and process the result
        """
        # remove request
        self.link_requests.remove(request)

        # reservation request
        if self.reservation_request > 0:
            self.over_requests.append(request)
            while len(self.over_requests) > self.reservation_request:
                del self.over_requests[0]

        call = request.callback(result, request)
        self.add_callback_result(call)
