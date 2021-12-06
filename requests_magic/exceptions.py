"""requests magic 用到的异常们
"""


class MagicError(Exception):
    """requests magic 的基础异常类型
    """
    pass


class SchedulerError(MagicError):
    """调度器异常类型
    """
    pass


class RequestError(MagicError):
    """请求错误的基础异常类型，记录了犯错的请求
    """

    def __init__(self, request):
        """请求错误的基础异常类型，记录了犯错的请求

        Args:
            request: 犯错的请求
        """
        self.request = request

    def __str__(self) -> str:
        return f'[ERROR] {self.request}'


class RequestCanRetryError(RequestError):
    """这个异常会让请求无条件重试
    """
    pass


class RequestTimeoutError(RequestCanRetryError):
    """请求超时异常，这会让请求根据超时设置决定是否要等待一定时间后重试
    """
    pass


class RequestHttpError(RequestError):
    """Http错误，这里记录了 Http 状态码
    """

    def __init__(self, request, code: int):
        """Http错误，这里记录了 Http 状态码

        Args:
            request: 犯错的请求
            code: 得到的状态码，这里应该不会出现 200
        """
        super(RequestHttpError, self).__init__(request)
        self.code = code

    def __str__(self) -> str:
        return f"[ERROR] [{self.code}] {self.request}"
