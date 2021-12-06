"""下载中间件们
"""

from .exceptions import *
from .utils import *
import requests


def requests_downloader(request) -> requests.Response:
    """这是默认的下载中间件，基于 requests

    Args:
        request: 请求
    Raises:
        RequestTimeoutError: 请求超时，这会尝试重试请求
    Returns:
        下载的最终结果
    """
    kwargs = request_to_requests_kwargs(request)
    try:
        return requests.request(**kwargs)
    except requests.Timeout as timeoutError:
        raise RequestTimeoutError(request)


def requests_downloader_filter(response: requests.Response, request) -> None:
    """默认的请求过滤器。
    基于 requests，用来过滤下载完成后的结果，没有返回值，但可能抛出各种异常

    Args:
        response: 下载好的结果
        request: 请求
    """
    if response.status_code >= 400:
        raise RequestHttpError(request, response.status_code)
