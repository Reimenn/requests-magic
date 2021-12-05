class RequestError(Exception):
    """
    requests magic base error
    """
    def __init__(self, request):
        self.request = request

    def __str__(self) -> str:
        return f'[ERROR] {self.request}'


class RequestCanRetryError(RequestError):
    """
    Raise this error in the downloader will automatically re-download
    """
    pass


class RequestTimeoutError(RequestCanRetryError):
    """
    Timeout error, auto re-download when request time_out_retry > 0
    """
    pass


class RequestHttpError(RequestError):
    """
    Other errors
    """
    def __init__(self, request, code: int):
        super(RequestHttpError, self).__init__(request)
        self.code = code

    def __str__(self) -> str:
        return f"[ERROR] [{self.code}] {self.request}"
