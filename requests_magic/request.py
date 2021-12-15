"""请求类和请求线程类
"""
import hashlib
import threading
import time
import json
from typing import Callable, NoReturn, Dict, Any, List, Union
from dataclasses import dataclass
from requests_magic.mmlog import logger
import requests_magic.downloader as magic_d
from requests_magic.utils import getattr_in_module, get_log_name

__FUCK_CIRCULAR_IMPORT = False
if __FUCK_CIRCULAR_IMPORT:
    from .scheduler import Scheduler


class Request:
    """表示一个请求，这里会自动创建 RequestThread
    """

    # 会被持久化的字段，这些字段必须在 init 参数、self 字段中保持一致
    _dict_fields = (
        'name',
        'url',
        'method',
        'data',
        'params'
        'tags',
        'headers',
        'time_out',
        'time_out_wait',
        'time_out_retry',
        'wait'
    )

    def __init__(self, url: str,
                 callback: Callable[[Any, 'Request'], NoReturn],
                 method: str = 'GET',
                 data: dict = None, params: dict = None,
                 headers: dict = None, cookies: dict = None,
                 time_out: int = 10, time_out_wait: int = 15,
                 time_out_retry: int = 3,
                 tags: dict = None, wait: float = 0,
                 downloader: Callable[['Request'], NoReturn] = magic_d.requests_downloader,
                 downloader_filter: Callable[['Response', 'Request'], NoReturn] = magic_d.requests_downloader_filter,
                 preparse: Callable[['Response', 'Request'], NoReturn] = None,
                 name: str = '',
                 **kwargs):
        """表示一个请求，这里会自动创建 RequestThread

        Args:
            url: 请求的目标地址
            callback: 回调解析函数，这必须是爬虫类中的方法
            data: 请求数据
            params: 请求查询数据
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

        self.wait = wait
        self.name = name
        if tags is None:
            tags = {}
        if data is None:
            data = {}
        if params is None:
            params = {}
        if headers is None:
            headers = callback.__self__.headers.copy()
        if cookies is None:
            cookies = callback.__self__.cookies.copy()

        # http
        self.url: str = url
        self.data: dict = data
        self.params: dict = params
        self.method: str = method
        self.headers: dict = headers
        self.cookies: dict = cookies

        # scheduler
        self.callback: Callable[[Any, 'Request'], NoReturn] = callback
        self.downloader = downloader
        self.downloader_filter = downloader_filter
        self.tags: dict = tags
        self.scheduler = None
        # get spider by callback

        self.spider = callback.__self__
        from .spider import Spider
        if not isinstance(self.spider, Spider):
            raise TypeError('callback must be a method in spider')
        # preparse
        self.preparse = preparse
        if self.preparse is None:
            self.preparse = self.spider.preparse
        # time
        self.start_time: float = -1
        self.total_time: float = -1
        # time out
        self.time_out: float = time_out
        self.time_out_wait: float = time_out_wait
        self.time_out_retry: int = time_out_retry

        self.kwargs = kwargs

        # Request self field
        self.response:'Response' = None
        self.show_url = \
            (self.url if len(self.url) < 40 else '...') + \
            self.url[-37:-1]
        self._thread: threading.Thread = None

    def __str__(self) -> str:
        return get_log_name(self, False)

    def is_requesting(self) -> bool:
        """ 是否正在请求中，根据是否存在下载线程判断
        """
        return self._thread is not None

    def is_finish(self) -> bool:
        """ 是否已经请求完成，根据是否有结果和 is_requesting 判断
        """
        return self.response and not self.is_requesting()

    def start(self):
        """开始下载，自动创建 RequestThread，下载完成后会自动调用调度器的方法
        """
        if self._thread:
            logger.error(f"{self} downloading, Can't start")
            return
        logger.info_request(
            f"{self} [{self.method.upper()} START] {self.show_url}"
        )
        self._thread = threading.Thread(target=self._request_thread)
        self.start_time = time.time()
        self._thread.start()

    def md5(self) -> str:
        """根据某些属性计算自己的md5，
        用于url去重，默认时使用 请求方法、url、data、time_out_retry 按照 utf-8 编码计算
        Returns:
            md5字符串
        """
        return hashlib.md5(
            f'{self.method};{self.url};{self.data};'
            f'{self.time_out_retry}'.encode('utf-8')
        ).hexdigest()

    def _request_thread_error(self, error: Exception) -> NoReturn:
        """ 当下载器或下载过滤器返回错误时调用。（在下载线程中调用）。
        这会放弃这个请求。
        """
        self.stop()
        self.scheduler.downloader_abandon(self)
        logger.error(f'{self} {error}')

    def _request_thread_fail(self, operate: magic_d.DownloaderFailOperate
                             ) -> NoReturn:
        """ 当下载器或下载过滤器返回失败操作时调用。（在下载线程中调用）。
        这会重试或放弃这个请求。
        """
        self.stop()
        if isinstance(operate, magic_d.Timeout):
            message = f'{self} Request is timeout ({self.time_out}s) ' \
                      f'to {self.url}. '
            if self.time_out_retry > 0:
                message += f'Try again in {self.time_out_wait} seconds.' \
                           f' ({self.time_out_retry - 1} remaining)'
            else:
                message += 'Gave up the request'
            logger.warning(message)
            if self.time_out_retry > 0:
                self.time_out_retry -= 1
                # if self.time_out_wait > 0:
                #     time.sleep(self.time_out_wait)
                self.scheduler.downloader_retry(
                    self, wait=self.time_out_wait
                )
        elif isinstance(operate, magic_d.Retry):
            logger.warning(
                f'{self} Retry [{self.method.upper()}] '
                f'{self.show_url} in {operate.wait} seconds'
            )
            # if operate.wait > 0:
            #     time.sleep(operate.wait)
            self.scheduler.downloader_retry(
                self, jump_in_line=operate.jump_in_line, wait=operate.wait
            )
        elif isinstance(operate, magic_d.Abandon):
            logger.warning(
                f'{self} Abandon [{self.method.upper()}] {self.show_url}'
            )
            self.scheduler.downloader_abandon(self)
        elif isinstance(operate, magic_d.Error):
            logger.error(f'{self} {operate.message}')
            self.scheduler.downloader_abandon(self)

    def _request_thread_finish(self, response: 'Response') -> NoReturn:
        """ 当下载器或下载过滤器成功时调用。（在下载线程中调用）。
        这会解析这个请求的结果。
        """
        self.stop()
        self.response = response
        logger.info_request(
            f"{self} [{self.method.upper()} OVER "
            f"{round(self.total_time, 2)}s] {self.show_url}"
        )
        self.scheduler.downloader_finish(self.response, self)

    def _request_thread(self) -> NoReturn:
        """开始下载，这是新线程执行的方法
        """
        self.start_time = time.time()

        # download
        response = self.downloader(self)
        if self._thread != threading.current_thread():
            return
        self.total_time = time.time() - self.start_time
        if isinstance(response, magic_d.DownloaderFailOperate):
            self._request_thread_fail(response)
            return
        if isinstance(response, Exception):
            self._request_thread_error(response)
            return

        # filter
        response_filter = self.downloader_filter(response, self)
        if self._thread != threading.current_thread():
            return
        if isinstance(response_filter, magic_d.DownloaderFailOperate):
            self._request_thread_fail(response_filter)
            return
        if isinstance(response_filter, Exception):
            self._request_thread_error(response_filter)
            return

        self._request_thread_finish(response)

    def stop(self) -> NoReturn:
        """终止请求线程
        Warnings:
            这并不会真正停止请求线程，只是让正在进行中的线程不再返回结果。
            这不是放弃请求，stop 后这个请求仍然会留在调度器的 link_request 中。
        """
        self._thread = None

    def to_dict(self) -> Dict[str, Union[int, float, str]]:
        """把请求转换成用字符串表示的 Dict，可以保存起来以后再读取再请求

        Returns:
            Dict
        Warnings:
            这不会保存下载状态和结果，并且 Request 的 **kwargs 参数会以简单的 json.dumps 形式保存，可能会存在问题。
            callback、downloader 等属性会被保存成字符串，在读取时利用 importlib 模块加载。
            callback 和 preparse 必须是爬虫中的方法。
            downloader 和 downloader_filter 必须是某个模块中的顶级方法。
        """
        if self.is_requesting():
            logger.warning(
                "The downloading state will not be retained after"
                " the request being downloaded is converted to json")
        if self.is_finish():
            logger.warning(
                "The downloaded result will not be retained after"
                " the request being downloaded is converted to json")
        json_dict = {
            'save_tags': {
                'downloader':
                    (self.downloader.__module__,
                     self.downloader.__name__),
                'downloader_filter':
                    (self.downloader_filter.__module__,
                     self.downloader_filter.__name__),
                'callback': self.callback.__name__,
                'preparse': self.preparse.__name__,
                'spider': self.spider.identity,
                'kwargs': self.kwargs,
            }
        }
        for field in Request._dict_fields:
            json_dict[field] = getattr(self, field)
        return json_dict

    @staticmethod
    def from_dict(data_dict: Dict[str, Union[int, float, str, dict]],
                  scheduler: 'Scheduler') -> 'Request':
        """ 从Dict中解析出新的 Request

        Args:
            scheduler: 需要一个调度器分配爬虫、解析函数等
            data_dict: 源 dict

        Returns:
            解析得到的请求

        Warnings:
            因为涉及到反射，所以不要加载不信任的请求。
            其他警告查看 to_dict 方法文档。
        """
        save_tags = data_dict['save_tags']
        del data_dict['save_tags']
        spider = scheduler.get_spider_by_identity(
            save_tags['spider']
        )
        data_dict['downloader'] = getattr_in_module(
            *save_tags['downloader']
        )
        data_dict['downloader_filter'] = getattr_in_module(
            *save_tags['downloader_filter']
        )
        data_dict['callback'] = getattr(
            spider, save_tags['callback']
        )
        data_dict['preparse'] = getattr(
            spider, save_tags['preparse']
        )

        result: Request = Request(**data_dict)
        result.kwargs = save_tags['kwargs']
        result.spider = spider
        return result


@dataclass
class SetCookie:
    version: int
    name: str
    value: str
    domain: str = ''
    path: str = '/'
    expires: int = 0
    secure: bool = False
    comment: str = None


@dataclass
class Response:
    request: Request
    url: str
    content: bytes
    status_code: int
    headers: dict
    set_cookies: List[SetCookie]
    reason: str
    request_time: float

    @property
    def is_redirect(self) -> bool:
        return 'location' in self.headers and 300 <= self.status_code <= 399

    @property
    def location(self) -> str:
        return self.headers['location']

    @property
    def encoding(self) -> str:
        encoding = 'UTF-8'
        ct: str = self.headers.get('content-type', 'text/html; charset=utf-8')
        for s in ct.split(';'):
            s: str = s.strip()
            if s.startswith('charset='):
                encoding = s[8:]
                break
        return encoding

    @property
    def text(self) -> str:
        return self.text_by(self.encoding)

    @property
    def json(self) -> dict:
        return json.loads(self.text)

    def text_by(self, encoding: str) -> str:
        if isinstance(self.content, str):
            return self.content
        return self.content.decode(encoding, 'replace')
