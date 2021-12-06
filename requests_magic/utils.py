"""工具模块
"""


def request_to_requests_kwargs(request) -> dict:
    """根据 Request 生成 requests.request 会用到的参数字典

    Args:
        request: 请求
    Returns:
        参数字典
    """
    result: dict = {
        'method': request.method,
        'url': request.url,
        'timeout': request.time_out
    }

    if request.data:
        if request.method == 'GET':
            result['params'] = request.data
        else:
            if isinstance(request.data, dict):
                result['json'] = request.data
            else:
                result['data'] = request.data

    if request.headers:
        result['headers'] = request.headers

    for k, v in request.kwargs:
        if k not in result:
            result[k] = v

    return result
