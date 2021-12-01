from requestsMagic.scheduler import Scheduler
from requestsMagic.Item import Item
from requestsMagic.pipeline import Pipeline
from requestsMagic.spider import Spider
from requestsMagic.logger import logger, LoggerLevel
from typing import Union, List

Scheduler = Scheduler
Spider = Spider
Pipeline = Pipeline
Item = Item
Logger = logger
LoggerLevel = LoggerLevel


def quick_start(spider: Union[List[Spider], Spider], pipeline, max_link: int = 12,
                request_interval: float = 0, wait: bool = True):
    scheduler = Scheduler(pipeline=pipeline, max_link=max_link, request_interval=request_interval)
    if isinstance(spider, Spider):
        spider = [spider]

    for s in spider:
        call = s.start()
        scheduler.add_callback_result(call)

    scheduler.start()

    while wait:
        input()
