from .request import Request
import requests


class Spider:

    def __init__(self, name: str = ""):
        self.name = name

    def start(self):
        """
        爬虫的起点，这里可以用 return或yield 返回 Request或Item
        """
        pass

    def parse(self, result: requests.Response, request: Request):
        """
        解析函数的例子，其实并没有人会调用这个函数
        解析函数会被好多线程执行
        """
        pass

    def preparse(self, result: requests.Response, request: Request) -> requests.Response:
        """
        预解析函数
        预解析函数会被好多线程执行
        """
        return result

    def __str__(self) -> str:
        return f"[Spider - {self.name}]" if self.name else ''
