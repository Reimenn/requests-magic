"""
requests magic
"""

from .scheduler import Scheduler
from .item import Item
from .request import Request
from .pipeline import Pipeline
from .spider import Spider
from .logger import Logger, LoggerLevel
from typing import Union, List


def quick_start(spiders: Union[List[Spider], Spider],
                pipelines: Union[List[Pipeline], Pipeline] = None,
                max_link: int = 12,
                request_interval: float = 0,
                wait: bool = True, **kwargs) -> Scheduler:
    """
    快速开始爬虫，将自动配置调度器
    Parameters
    ----------
    spiders
        这是你的爬虫，可以只有一个，也可以是一个列表。这将自动执行这些爬虫的 start 方法，并将结果发送给调度器。
    pipelines
        这是你的管道，可以只有一个，也可以是一个列表。它们将用来保存爬取到的数据。
    max_link
        同时最大连接数（最大同时爬取线程）。默认：12
    request_interval
        请求之间的时间间隔（单位：秒）。默认：0
    wait
        是否暂停程序，内部有一个 `while self.wait: input()`。默认开启
    kwargs
        这些会传给调度器的实例化参数

    Returns
    -------
    返回调度器（如果wait = True，你应该也得不到这个调度器）

    Examples
    -------
    >>> quick_start(MySpider(),[P1(),P2()],max_link=32)
    """
    if pipelines is None:
        pipelines = [Pipeline()]

    _scheduler = Scheduler(pipelines=pipelines,
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
    return _scheduler


def start(spiders: Union[List[Spider], Spider], scheduler: Scheduler, wait: bool = True) -> Scheduler:
    """
    开始爬虫，这将自动调用 spiders 的 start 方法并传给调度器
    Parameters
    ----------
    spiders
        这是你的爬虫，可以只有一个，也可以是一个列表。这将自动执行这些爬虫的 start 方法，并将结果发送给调度器。
    scheduler
        你的调度器
    wait
        是否暂停程序，内部有一个 `while self.wait: input()`。默认开启

    Returns
    -------
    返回调度器（如果wait = True，你应该也得不到这个调度器）
    """
    if isinstance(spiders, Spider):
        spiders = [spiders]

    for s in spiders:
        call = s.start()
        scheduler.add_callback_result(call)

    scheduler.start()

    while wait:
        input()

    return scheduler
