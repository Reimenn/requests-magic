"""管道基类和内置的管道
"""

import os
import threading
import time
from .mmlog import logger
from .utils import get_log_name

__FUCK_CIRCULAR_IMPORT = False
if __FUCK_CIRCULAR_IMPORT:
    from .scheduler import Scheduler


class Pipeline:
    """管道基类，用来持久化数据，这是一个新线程
    """

    def __init__(self, scheduler: 'Scheduler' = None, name: str = ""):
        """管道基类，用来持久化数据，这是一个新线程

        Args:
            name: 管道的名字，希望能帮助 debug
        Warnings:
            不要实例化这个类，应该继承Pipeline实现你自己的持久化
        """
        super().__init__()
        self.scheduler: 'Scheduler' = scheduler
        self.name = name
        self._item_list = []
        self.thread = threading.Thread(target=self.run)

    def __str__(self) -> str:
        return get_log_name(self, True)

    def add_item(self, item):
        """ 添加新的需要持久化的数据

        Args:
            item:要持久化的数据
        """
        self._item_list.append(item)

    def is_alive(self) -> bool:
        return self.thread.is_alive()

    def start(self):
        if self.is_alive():
            return
        self.thread.start()

    def run(self) -> None:
        """ 开启线程，反复监听待保存的 item
        """
        while True:
            if self._item_list:
                item = self._item_list[0]
                del self._item_list[0]
                try:
                    self.save(item)
                    logger.info_saveitem_item(f"{self} [SAVE ITEM {item.name} Finish]")
                except Exception as e:
                    logger.error(f"{self} [SAVE ITEM {item.name} Error] {e}")
                    raise e
            else:
                time.sleep(0.1)

    def acceptable(self, item) -> bool:
        """ 判断是否可以接收某个 item。
        调度器会根据这里的返回值判断是否继续用这个管道保存这个item，
        重写这里实现你自己的判断

        Args:
            item: 被判断的item
        Returns:
            能否接收
        Warnings:
            这是一个会被好多线程调用的方法。
        """
        return True

    def save(self, item):
        """真正的持久化方法，
        重写这里用你的方式保存数据

        Args:
            item: 需要持久化的数据

        Warnings:
            这是一个被自身线程调用的方法
        """
        pass

    def identity(self) -> str:
        """ 获取当前实例的唯一标识，中断续爬用这个表示获取当前管道
        Warnings:
            标识相同的管道只能存在一个
        """
        return f'{self.__class__.__name__}|{self.name}'


class SimpleConsolePipeline(Pipeline):
    """
    简单的控制台管道，直接把item转换成字符串并显示在控制台上
    """

    def save(self, item):
        print(str(item))


class SimpleFilePipeline(Pipeline):
    """
    简单的文件持久化管道
    """

    def __init__(self, scheduler: 'Scheduler' = None, name: str = "SimpleFilePipeline",
                 output_file_tag_key: str = 'file',
                 mode: str = 'a',
                 auto_create_folder: bool = True,
                 encoding: str = 'utf-8',
                 newline: str = '\n',
                 ):
        """
        简单的文件持久化管道
        Parameters
        ----------
        name
            管道的名字，希望能帮助 debug
        output_file_tag_key
            在 item.tags 中表示保存路径的 key，值必须是字符串，默认：file
        mode
            文件的打开模式，默认是 a （追加）
        auto_create_folder
            是否在自动创建上层目录，默认开启
        encoding
            文件编码，默认：utf-8
        """
        super().__init__(scheduler, name)
        self.newline = newline
        self.encoding = encoding
        self.auto_create_folder = auto_create_folder
        self.mode = mode
        self.output_file_tag_key = output_file_tag_key

    def acceptable(self, item) -> bool:
        """
        判断 output_file_tag_key 是否存在以及值是否是字符串
        这是会被好多线程调用的方法
        """
        return self.output_file_tag_key in item.tags and isinstance(item.tags[self.output_file_tag_key], str)

    def save(self, item):
        """
        作为文件保存item
        这是执行在管道自身线程上的方法
        """
        file = item.tags[self.output_file_tag_key]
        path = os.path.abspath(os.path.join(file, '..'))
        if not os.path.exists(path):
            if self.auto_create_folder:
                os.makedirs(path)
            else:
                logger.error_pipeline(f"{self} {path} path not exists")
                return
        if not os.path.isdir(path):
            logger.error_pipeline(f"{self} {path} not is a dir")
            return
        with open(file, self.mode, encoding=self.encoding, newline=self.newline) as f:
            f.write(str(item))
