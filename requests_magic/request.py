"""请求类和请求线程类

Attributes:
    default_headers (dict): 当请求没有指定 headers 时，会从这里copy一份，默认是空的。
"""
import threading
import time
import hashlib
from typing import Callable, NoReturn, Dict, Any
from .logger import Logger
from .downloader import *
from .exceptions import *
from .utils import HasNameObject, getattr_in_module

__FUCK_CIRCULAR_IMPORT = False
if __FUCK_CIRCULAR_IMPORT:
    from .scheduler import Scheduler


class Request(HasNameObject):
    """表示一个请求，这里会自动创建 RequestThread
    """

    def __init__(self, url: str, callback: Callable[[Any, 'Request'], NoReturn],
                 data: dict = None, method: str = 'GET', headers: dict = None,
                 time_out: int = 10, time_out_wait: int = 15, time_out_retry: int = 3,
                 tags: dict = None,
                 downloader: Callable[['Request'], NoReturn] = requests_downloader,
                 downloader_filter: Callable[['Result', 'Request'], NoReturn] = requests_downloader_filter,
                 preparse: Callable[['Result', 'Request'], NoReturn] = None,
                 name: str = '',
                 **kwargs):
        """表示一个请求，这里会自动创建 RequestThread

        Args:
            url: 请求的目标地址
            callback: 回调解析函数，这必须是爬虫类中的方法
            data: 请求数据
            method: 请求方法，默认：GET
            headers: 请求头，如果为空，则从 requests_magic.request.default_headers copy一份
            time_out: 超时时限，默认：10秒
            time_out_wait: 超时后重试前的等待时间，默认：15秒
            time_out_retry: 超时重试次数，默认：3次
            tags: 标签，用来记录一些额外内容，可以用来在解析函数、下载中间件等东西之间传递信息
            downloader: 下载器，这个方法需要有一个参数表示 Request 并返回请求结果，默认使用基于 requests 实现，如果要持久化请求，则需要把你的下载器定义在某个模块顶级
            downloader_filter: 下载过滤器，这个方法需要有两个参数分别表示 请求结果 和 Request，默认使用基于 requests 实现，如果要持久化请求，则需要把你的下载过滤器定义在某个模块顶级
            preparse: 预解析器，这必须是爬虫类中的方法，默认使用解析函数所在爬虫类的 preparse 方法
            name: 请求的名字，希望能帮助 debug
            kwargs: 直接记录在自己的 kwargs 属性上，默认的 requests 下载器会把这里的值添加到 requests.request 方法的参数上
        """
        super().__init__()

        self.name = name
        if tags is None:
            tags = {}
        if data is None:
            data = {}
        if headers is None:
            headers = callback.__self__.default_headers.copy()

        self.url: str = url
        self.data: dict = data
        self.method: str = method
        self.headers: dict = headers

        self.callback: Callable[[Any, 'Request'], NoReturn] = callback
        self.downloader = downloader
        self.downloader_filter = downloader_filter
        self.tags: dict = tags
        self.scheduler = None

        self.spider = callback.__self__
        from .spider import Spider
        if not isinstance(self.spider, Spider):
            raise TypeError('callback must be a method in spider')

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

    def is_requesting(self) -> bool:
        """ 是否正在请求中，根据是否存在下载线程判断
        """
        return self.thread is not None

    def is_finish(self) -> bool:
        """ 是否已经请求完成，根据是否有结果和 is_requesting 判断
        """
        return self.result and not self.is_requesting()

    def start(self):
        """开始下载，自动创建 RequestThread，下载完成后会自动调用调度器的方法
        """
        if self.thread:
            Logger.error(f"{self} downloading, Can't start")
            return
        Logger.info(f"{self} [{self.method.upper()} START] {self.show_url}")
        self.thread = RequestThread(self)
        self.start_time = time.time()
        self.thread.start()

    def md5(self) -> str:
        """根据某些属性计算自己的md5，
        用于url去重，默认时使用 请求方法、url、data、time_out_retry 按照 utf-8 编码计算
        Returns:
            md5字符串
        """
        return hashlib.md5(
            f'{self.method};{self.url};{self.data};{self.time_out_retry}'.encode('utf-8')
        ).hexdigest()

    def request_thread_error(self, error: BaseException) -> NoReturn:
        if self.thread != threading.current_thread():
            return

        self.stop()
        self.scheduler.downloader_abandon(self)
        Logger.error(f'{self} {error}')

    def request_thread_fail(self, operate: DownloaderFailOperate) -> NoReturn:
        if self.thread != threading.current_thread():
            return

        self.stop()
        if isinstance(operate, Timeout):
            message = f'{self} Request is timeout ({self.time_out}s) to {self.url}. '
            if self.time_out_retry > 0:
                message += \
                    f'Try again in {self.time_out_wait} seconds. ({self.time_out_retry - 1} remaining)'
            else:
                message += 'Gave up the request'
            Logger.warning(message)
            if self.time_out_retry > 0:
                self.time_out_retry -= 1
                # if self.time_out_wait > 0:
                #     time.sleep(self.time_out_wait)
                self.scheduler.downloader_retry(self, wait=self.time_out_wait)
        elif isinstance(operate, Retry):
            Logger.warning(f'{self} Retry [{self.method.upper()}] {self.show_url} in {operate.wait} seconds')
            # if operate.wait > 0:
            #     time.sleep(operate.wait)
            self.scheduler.downloader_retry(self, jump_in_line=operate.jump_in_line, wait=operate.wait)
        elif isinstance(operate, Abandon):
            Logger.warning(f'{self} Abandon [{self.method.upper()}] {self.show_url}')
            self.scheduler.downloader_abandon(self)
        elif isinstance(operate, Error):
            Logger.error(f'{self} {operate.message}')
            self.scheduler.downloader_abandon(self)

    def request_thread_finish(self, result) -> NoReturn:
        if self.thread != threading.current_thread():
            return

        self.stop()
        self.result = result
        Logger.info(f"{self} [{self.method.upper()} OVER {round(self.total_time, 2)}s] {self.show_url}")
        self.scheduler.downloader_finish(self.result, self)

    def stop(self) -> None:
        """终止请求线程
        """
        self.thread = None

    def to_dict(self) -> Dict[str, Union[int, float, str]]:
        """把请求转换成用字符串表示的 Dict，可以保存起来以后再读取再请求

        Returns:
            Dict
        Warnings:
            这是个测试功能，不一定稳定，要配合 from_json 方法使用
            这不会保存下载状态和结果，并且 Request 的 **kwargs 参数会以简单的 json.dumps 形式保存，可能会存在问题。
            callback、downloader等属性会被保存成字符串，在读取时利用 importlib 模块加载。
            callback 和 preparse 必须是爬虫中的方法
            downloader 和 downloader_filter 必须是某个模块中的顶级方法
        """
        if self.is_requesting():
            Logger.warning(
                "The downloading state will not be retained after the request being downloaded is converted to json")
        if self.is_finish():
            Logger.warning(
                "The downloaded result will not be retained after the request being downloaded is converted to json")
        json_dict = {
            'name': self.name,
            'url': self.url,
            'method': self.method,
            'data': self.data,
            'tags': self.tags,
            'headers': self.headers,
            'time_out': self.time_out,
            'time_out_wait': self.time_out_wait,
            'time_out_retry': self.time_out_retry,
            'save_tags': {
                'downloader':
                    (self.downloader.__module__, self.downloader.__name__),
                'downloader_filter':
                    (self.downloader_filter.__module__, self.downloader_filter.__name__),
                'callback': self.callback.__name__,
                'preparse': self.preparse.__name__,
                'spider': self.spider.identity(),
                'kwargs': self.kwargs,
            }
        }
        return json_dict

    @staticmethod
    def from_dict(json_dict: Dict[str, Union[int, float, str, dict]], scheduler: 'Scheduler') -> 'Request':
        """ 从Dict中解析出新的 Request

        Args:
            scheduler: 需要一个调度器分配爬虫、解析函数等
            json_dict: json 格式的 dict

        Returns:
            解析得到的请求

        Warnings:
            这是个测试功能，不一定稳定，要配合 to_dict 方法使用
            其他警告查看 to_dict 方法文档
        """
        save_tags = json_dict['save_tags']
        del json_dict['save_tags']
        spider = scheduler.get_spider_by_identity(save_tags['spider'])
        json_dict['downloader'] = getattr_in_module(*save_tags['downloader'])
        json_dict['downloader_filter'] = getattr_in_module(*save_tags['downloader_filter'])
        json_dict['callback'] = getattr(spider, save_tags['callback'])
        json_dict['preparse'] = getattr(spider, save_tags['preparse'])

        result: Request = Request(**json_dict)
        result.kwargs = save_tags['kwargs']
        result.spider = spider
        return result


class RequestThread(threading.Thread):
    """请求的下载线程
    """

    def __init__(self, request: Request):
        """请求的下载线程

        Args:
            request: 请求
        """
        super(RequestThread, self).__init__()
        self.request = request

    def run(self) -> None:
        """开始下载
        """

        result = self.request.downloader(self.request)
        self.request.total_time = time.time() - self.request.start_time
        if isinstance(result, DownloaderFailOperate):
            self.request.request_thread_fail(result)
            return
        if isinstance(result, BaseException):
            self.request.request_thread_error(result)
            return
        result_filter = self.request.downloader_filter(result, self.request)
        if isinstance(result_filter, DownloaderFailOperate):
            self.request.request_thread_fail(result_filter)
            return
        if isinstance(result_filter, BaseException):
            self.request.request_thread_error(result_filter)
            return
        self.request.request_thread_finish(result)
