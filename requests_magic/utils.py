"""工具模块
"""
import importlib
import threading
import time
from typing import Callable, NoReturn


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


def get_log_name(obj, cls_name: bool = True) -> str:
    cn = obj.__class__.__name__
    if hasattr(obj, 'name'):
        name = obj.name
    else:
        name = None
    if cls_name:
        if name:
            return f'[{cn}-{name}]'
        else:
            return f'[{cn}]'
    else:
        return f'[{name}]' if name else ''


class Looper(threading.Thread):
    """ 循环线程，类似 VB 或 WinForm 中的 Timer。
    不过 loop 方法需要一个 delta_time 参数，类似 Unity 中的 Time.DeltaTime
    """

    def __init__(self, target: Callable[[float], NoReturn] = None) -> None:
        """ 循环线程

        Args:
            target: 可以指定一个目标方法，它需要一个 float 类型参数，如果为空则执行 loop 方法
        """
        super().__init__()
        self.target = target if target else self.loop
        self.loop_interval: float = 0.05
        self._close: bool = False
        self._pause: bool = False
        self._old_time: float = time.time()
        self._in_action: bool = False

    @property
    def in_action(self):
        """ 是否正在执行 target 或 loop 方法。
        间隔等待时返回 False
        """
        return self._in_action

    def run(self):
        self._old_time = time.time()
        while not self._close:
            if not self._pause:
                ct = time.time()
                self._in_action = True
                self.target(ct - self._old_time)
                self._in_action = False
                self._old_time = ct
            if self.loop_interval > 0:
                time.sleep(self.loop_interval)

    def close(self):
        """ 关闭循环线程，这只在运行中有效
        """

        if self.is_alive():
            self._close = True

    def pause(self):
        """ 暂停线程
        """
        self._pause = True

    def unpause(self, reset_delta: bool = True):
        """ 解除暂停

        Args:
            reset_delta: 是否归零 delta 时间，默认开启
        """

        if reset_delta:
            self._old_time = time.time()
        self._pause = False

    @property
    def is_pause(self) -> bool:
        """ 是否暂停中
        """
        return self._pause

    def loop(self, delta_time: float):
        """ 可以重写这里实现你的循环方法

        Args:
            delta_time: 当前循环和上次循环之间相差的时间
        """

        pass
