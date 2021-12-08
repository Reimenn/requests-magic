"""requests magic 的日志模块，可以在这里设置日志等级
"""
import logging

Logger = logging.getLogger("RequestsMagic")
streamHandler = logging.StreamHandler()
streamHandler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s\t %(message)s"))
streamHandler.setLevel(logging.INFO)
Logger.addHandler(streamHandler)
Logger.setLevel(logging.INFO)


def set_logger_level(level):
    """给你的爬虫项目设置一下日志等级

    Args:
        level: 等级，参考内置模块 logging
    Examples:
        >>> import requests_magic as rm
        >>> rm.set_logger_level('WARNING')
    """
    Logger.setLevel(level)
    streamHandler.setLevel(level)
