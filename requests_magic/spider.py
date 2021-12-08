from .request import Request
from .utils import HasNameObject
import requests

__FUCK_CIRCULAR_IMPORT = False
if __FUCK_CIRCULAR_IMPORT:
    from .scheduler import Scheduler


class Spider(HasNameObject):

    def __init__(self, scheduler: 'Scheduler' = None, name: str = ""):
        """ 爬虫类，你不应该实例化我，应该继承我写一个你自己的爬虫
        Args:
            scheduler: 调度器
            name: 名字

        Warnings:
            调度器内部会实例化Spider。
            如果需要重写Spider的 __init__ 方法，不要改动方法参数，这可能会导致调度器无法生成你的Spider
        """
        self.scheduler: 'Scheduler' = scheduler
        self.name = name
        self.default_headers: dict = {}

    def identity(self) -> str:
        """ 获取当前实例的唯一标识，中断续爬用这个表示获取当前爬虫
        Warnings:
            标识相同的爬虫只能存在一个
        """
        return f'{self.__class__.__name__}|{self.name}'

    def start(self):
        """爬虫的起点，这里可以用 return或yield 返回 Request或Item
        """
        pass

    def parse(self, result: requests.Response, request: Request):
        """解析函数的例子，默认情况下并没有人会调用这个函数
        Warnings:
            解析函数会被好多线程执行
        """
        pass

    def preparse(self, result: requests.Response, request: Request) -> requests.Response:
        """默认的预解析函数
        Warnings:
            预解析函数会被好多线程执行
        """
        return result
