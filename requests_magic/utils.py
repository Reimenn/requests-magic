"""工具模块
"""
import importlib
from typing import Any


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

    for k, v in request.kwargs.items():
        if k not in result:
            result[k] = v

    return result


def getattr_in_module(module_name: str, func_name: str):
    """ 在某个模块中获取属性

    Args:
        module_name: 模块名
        func_name: 属性名

    Returns:
        属性
    """
    m = importlib.import_module(module_name)
    return getattr(m, func_name)


class HasNameObject:
    """ 重写了 requests magic 风格的 __str__ 方法。
    是 '[class_name: name]' 或 '[class_name]' 这样的字符串
    """

    def __str__(self) -> str:
        cls_name = self.__class__.__name__
        if hasattr(self, 'name') and self.name:
            return f'[{cls_name}: {self.name}]'
        else:
            return f'[{cls_name}]'
