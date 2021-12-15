""" mmlog 模块，希望能更适合爬虫
"""
import threading
from collections import namedtuple
from typing import List, Callable, NoReturn
import sys
import time


def get_time_str(formatter: str = '%Y-%m-%d %H:%M:%S') -> str:
    local_time = time.localtime(time.time())
    return time.strftime(formatter, local_time)


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
        header = f"{get_time_str()} [{'|'.join(tags)}] "
        spaces: str = ' ' * len(header)
        lines = str(message).split('\n')
        result: str = lines[0]
        if len(lines) > 1:
            result += '\n' + '\n'.join(spaces + i for i in lines[1:])
        return header + result

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
        out.write(str(message) + "\n")


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


Log = namedtuple('log', ['tags', 'message'])


class Logger(threading.Thread):
    def __init__(self, use_thread: bool = False, name: str = 'mm-Logger'):
        super().__init__(name=name)
        self.handlers: List[LoggerHandler] = []
        self.to_upper: bool = True
        self._use_thread = use_thread
        if use_thread:
            self._log_queue: List[Log] = []
            self._start_lock: threading.Lock = threading.Lock()

    def run(self) -> None:
        while True:
            if self._log_queue:
                log = self._log_queue[0]
                self.handle(log)
                self._log_queue.remove(log)
            else:
                time.sleep(0.1)

    def handle(self, log: Log) -> None:
        """ 让 Handler 们处理日志

        Args:
            log: 日志
        """
        tags = log.tags
        for handler in self.handlers:
            if handler.acceptable(tags):
                formatted = handler.formatter(tags, log.message)
                handler.on_log(tags, formatted)

    def log(self, tags: List[str], message):
        """ 发送日志
        """
        log = Log(tags=tags, message=message)
        if self._use_thread:
            self._start_lock.acquire()
            if not self.is_alive():
                self.start()
            self._start_lock.release()
            self._log_queue.append(log)

        else:
            self.handle(log)

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