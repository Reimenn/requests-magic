from .exceptions import *
from .utils import *
import requests


def requests_downloader(request) -> requests.Response:
    """
    Default download function (downloader)
    """
    kwargs = request_to_requests_kwargs(request)
    try:
        return requests.request(**kwargs)
    except requests.Timeout as timeoutError:
        raise RequestTimeoutError(request)


def requests_downloader_filter(response: requests.Response, request) -> None:
    """
    Default downloader filter
    """
    if response.status_code >= 400:
        raise RequestHttpError(request, response.status_code)


def spider_parse_before(result, request):
    pass
