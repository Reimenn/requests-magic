from typing import List, Any, Dict

__FUCK_CIRCULAR_IMPORT = False
if __FUCK_CIRCULAR_IMPORT:
    import requests
    from .request import Response, Request


def create_response_from_requests(r: 'requests.Response', request: 'Request') -> 'Response':
    """ 根据 Requests 库中的 Response 创建 magic Response

    Args:
        r: Requests 库的 Response.
        request: magic Request 请求.

    Returns:
        magic Response

    """
    from .request import Response, SetCookie
    set_cookies: List[SetCookie] = []
    for c in r.cookies:
        set_cookies.append(SetCookie(
            version=c.version,
            name=c.name,
            value=c.value,
            domain=c.domain,
            path=c.path,
            expires=c.expires,
            secure=c.secure,
            comment=c.comment,
        ))
    return Response(
        request=request,
        url=r.url,
        status_code=r.status_code,
        reason=r.reason,
        content=r.content,
        headers=dict(r.headers),
        request_time=r.elapsed.total_seconds(),
        set_cookies=set_cookies
    )


def create_requests_request_kwargs_from_magic_request(request: "Request") -> Dict[str, Any]:
    """ 根据 Request 生成 requests.request 会用到的参数字典

    Args:
        request: 请求
    Returns:
        参数字典
    """
    result: dict = {
        'method': request.method,
        'url': request.url,
        'timeout': request.time_out,
        'params': request.params
    }

    if request.data:
        if isinstance(request.data, dict):
            result['json'] = request.data
        else:
            result['data'] = request.data

    if request.headers:
        result['headers'] = request.headers
    if request.cookies:
        result['cookies'] = request.cookies

    for k, v in request.kwargs.items():
        result[k] = v

    return result
