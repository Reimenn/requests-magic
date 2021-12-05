def request_to_requests_kwargs(request) -> dict:
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
