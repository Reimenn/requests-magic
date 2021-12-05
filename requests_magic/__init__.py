from .scheduler import Scheduler
from .item import Item
from .request import Request
from .pipeline import Pipeline
from .spider import Spider
from .logger import Logger, LoggerLevel
from typing import Union, List


def quick_start(spiders: Union[List[Spider], Spider],
                pipeline: Union[List[Pipeline], Pipeline] = None,
                max_link: int = 12,
                request_interval: float = 0,
                wait: bool = True, **kwargs):
    """
    quick start a web spider, need one or more spider
    """
    if pipeline is None:
        pipeline = [Pipeline()]

    _scheduler = Scheduler(pipeline=pipeline,
                           max_link=max_link,
                           request_interval=request_interval, **kwargs)
    if isinstance(spiders, Spider):
        spiders = [spiders]

    for s in spiders:
        call = s.start()
        _scheduler.add_callback_result(call, from_spider=s)

    _scheduler.start()

    while wait:
        input()
