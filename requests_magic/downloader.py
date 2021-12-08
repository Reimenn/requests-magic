"""下载中间件们
"""

from .utils import *
from typing import Union
import requests

__FUCK_CIRCULAR_IMPORT = False
if __FUCK_CIRCULAR_IMPORT:
    from .request import Request


class DownloaderFailOperate:
    """
    让你的下载器或下载过滤器在发生错误的时候返回 DownloaderFailOperate，
    则会根据对应的 DownloaderFailOperate 进行操作
    """
    pass


class Abandon(DownloaderFailOperate):
    """ 放弃当前请求
    """


class Retry(DownloaderFailOperate):
    """ 无条件重试当前请求
    """

    def __init__(self, wait: float = 0, jump_in_line: bool = False):
        """ 无条件重试当前请求

        Args:
            wait: 等待一段时候后再重试（重新添加到待请求队列）
            jump_in_line: 是否插队到队列最前端
        """
        self.jump_in_line = jump_in_line
        self.wait = wait


class Timeout(DownloaderFailOperate):
    """ 表示请求超时
    """


class Error(DownloaderFailOperate):
    """ 未知错误，建议写明message，这会放弃请求并输出 message，相比直接 raise 这会让日志更整齐，除此外没其他用处
    """

    def __init__(self, message) -> None:
        super().__init__()
        self.message = message


def requests_downloader(request: 'Request') -> Union[requests.Response, DownloaderFailOperate]:
    """这是默认的下载中间件，基于 requests。

    Args:
        request: 请求
    Raises:
        RequestTimeoutError: 请求超时，这会尝试重试请求
    Returns:
        下载的最终结果，或者下载失败时返回 DownloaderFailOperate 的子类们（Retry,Abandon,Timeout,Error等）
        如果返回的是个异常，也会和 Error 类一样放弃请求并显示错误信息
    """
    kwargs = request_to_requests_kwargs(request)
    try:
        return requests.request(**kwargs)
    except requests.Timeout as timeoutError:
        return Timeout()
    except requests.RequestException as e:
        return Error(e)


def requests_downloader_filter(response: requests.Response, request: 'Request') -> DownloaderFailOperate:
    """默认的请求过滤器。空的，不过滤任何东西
    用来过滤下载完成后的结果

    Args:
        response: 下载好的结果
        request: 请求
    Returns:
        如果想要过滤掉下载的内容，可以返回 DownloaderFailOperate 的子类们（Retry,Abandon,Timeout,Error等）。
        如果返回的是个异常，也会和 Error 类一样放弃请求并显示错误信息
        如果不返回则表示下载结果可接受
    """

