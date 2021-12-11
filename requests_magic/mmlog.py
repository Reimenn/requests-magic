""" mmlog 模块，希望能更适合爬虫
"""

from typing import List
import sys
import datetime


class LoggerHandler:

    def __init__(self, acceptable_tags: List[str] = None):
        """ 日志处理器

        Args:
            acceptable_tags: 接收的标签，默认是一个['*']表示接收全部
        """
        if acceptable_tags is None:
            self.acceptable_tags: List[str] = ['*']
        else:
            self.acceptable_tags: List[str] = acceptable_tags

        # 会排除的标签，日志中存在的这些标签，而会无条件排除
        self.exclude_tags: List[str] = ['DEBUG']

    def acceptable(self, tags: List[str]) -> bool:
        """ 是否能处理这样 tags 的日志
        """
        result = False
        if '*' in self.acceptable_tags:
            result = True
        else:
            for tag in tags:
                if tag in self.acceptable_tags:
                    result = True
                    break
        for tag in tags:
            if tag in self.exclude_tags:
                result = False
                break
        return result

    def formatter(self, tags: List[str], message) -> str:
        """ 格式化日志
        Returns:
            格式化后的字符串
        """
        return f"{datetime.datetime.now()} [{'|'.join(tags)}] {message}"

    def on_log(self, tags: List[str], message: str):
        """ 真正的日志处理
        """
        pass


class ConsoleHandler(LoggerHandler):
    """ 控制台日志处理器
    """

    def on_log(self, tags: List[str], message: str):
        out = sys.stdout
        if 'ERROR' in tags or 'WARNING' in tags:
            out = sys.stderr
        print(str(message), file=out)


class FileHandler(LoggerHandler):
    """ 示范性质的文件日志处理器
    """

    def __init__(self, file_path: str, encoding: str = 'utf-8', acceptable_tags: List[str] = None, **kwargs):
        super().__init__(acceptable_tags)
        self.file = open(file_path, 'a', encoding=encoding, **kwargs)

    def formatter(self, tags: List[str], message) -> str:
        return super(FileHandler, self).formatter(tags, message) + '\n'

    def on_log(self, tags: List[str], message: str):
        self.file.write(message)
        self.file.flush()


class Logger:
    def __init__(self):
        self.handlers: List[LoggerHandler] = []
        self.to_upper: bool = True

    def log(self, tags: List[str], message):
        for handler in self.handlers:
            if handler.acceptable(tags):
                formatted = handler.formatter(tags, message)
                handler.on_log(tags, formatted)

    def __getattr__(self, item: str):
        tags = item.split('_')
        if self.to_upper:
            tags = [i.upper() for i in tags]

        def func(message):
            self.log(tags, message)

        return func


logger = Logger()
console_handler = ConsoleHandler()
logger.handlers.append(console_handler)
