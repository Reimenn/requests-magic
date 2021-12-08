import json
import os.path
from collections import Generator
from typing import Sequence, List, NoReturn, Dict, Any
from .request import Request
from .item import Item
from .spider import Spider
from .pipeline import Pipeline
from .logger import Logger
from .utils import HasNameObject
from .exceptions import *
import threading

import time


class Scheduler(HasNameObject, threading.Thread):
    """调度器，核心组件，负责请求管理与 item 转发

    Attributes:
        pause: 是否暂停，如果是，则不会发送新请求
        _link_requests: 正在下载中的请求
    """

    def __init__(self, spider_class, pipeline_class=Pipeline, tags: Dict[str, Any] = None,
                 max_link: int = 12, request_interval: float = 0, distinct: bool = True, start_pause: bool = False):
        """调度器，核心组件，爬虫的开始，负责请求管理与 item 转发

        Args:
            spider_class: 爬虫类或爬虫类们(list)，不要传递Spider实例进来
            pipeline_class: 管道类或管道类们(list)，不要传递Pipeline实例进来
            tags: 可以用来保存额外信息，例如纪录爬虫状态，可以由管道或爬虫更改
            max_link: 最大连接数，默认：12
            request_interval: 请求间隔时间，默认：0秒
            distinct: 是否开启去重，默认开启

        Warnings:
            注意线程安全问题
        """
        super().__init__()
        self.distinct = distinct
        self.max_link: int = max_link
        self.request_interval: float = request_interval

        # tags
        self._tags_lock = threading.Lock()
        if not tags:
            tags = {}
        self._tags = tags.copy()

        # 爬虫们
        self._spiders: Dict[str, Spider] = {}
        if not isinstance(spider_class, Sequence):
            spider_class = [spider_class]
        for i in spider_class:
            spider: Spider = i(scheduler=self)
            identity = spider.identity()
            if identity in self._spiders:
                Logger.warning(f'{spider} Spider with the same identity will be overwritten')
            self._spiders[identity] = spider

        # 管道们
        self._pipelines: Dict[str, Pipeline] = {}
        if not isinstance(pipeline_class, Sequence):
            pipeline_class = [pipeline_class]
        for i in pipeline_class:
            pipeline: Pipeline = i(scheduler=self)
            identity = pipeline.identity()
            if identity in self._pipelines:
                Logger.warning(f'{pipeline} pipeline with the same identity will be overwritten')
            self._pipelines[identity] = pipeline

        # 请求队列
        self._request_list: List[Request] = []
        # 正在请求中的请求
        self._link_requests: List[Request] = []
        # 添加过的请求的 MD5
        self._requests_md5: List[str] = []
        # 是否暂停了
        self.pause: bool = start_pause
        # 是否在保存中
        self.saving: bool = False
        self.save_data: dict = {}

    @property
    def request_list(self):
        return self._request_list

    @property
    def tags(self):
        return self._tags

    def add_request(self, request: Request, from_spider: Spider) -> NoReturn:
        """添加一个新的请求到请求队列（不会立刻执行）

        Args:
            request: 请求
            from_spider: 产生请求的爬虫
        """
        md5: str = request.md5()
        if self.distinct and md5 in self._requests_md5:
            Logger.info(f'Repeated request: {request} {request.show_url}')
            return
        request.spider = from_spider
        request.scheduler = self
        self._request_list.append(request)
        self._requests_md5.append(md5)

    def add_item(self, item: Item, from_spider: Spider) -> NoReturn:
        """ 添加一个新的 Item，这会转发给每个管道
        
        Args:
            item: Item
            from_spider: 产生这个 Item 的爬虫，可以为空，空了也没啥问题
        """
        item.spider = from_spider
        item.scheduler = self
        for pipeline in self._pipelines.values():
            if pipeline.acceptable(item):
                pipeline.add_item(item)

    def add_callback_result(self, result_ite, from_spider: Spider) -> NoReturn:
        """自动解析解析函数返回的结果，会自动迭代、添加请求或转发 Item

        Args
            result_ite: 结果
            from_spider: 产生结果的爬虫
        """

        if result_ite is None:
            return
        if not isinstance(result_ite, Generator) and not isinstance(result_ite, list):
            result_ite = [result_ite]

        for result in result_ite:
            if isinstance(result, Request):
                self.add_request(result, from_spider=from_spider)
            elif isinstance(result, Item):
                self.add_item(result, from_spider=from_spider)
            else:
                Logger.error(
                    f"Cannot handle {str(type(result))}, " +
                    f"Please do not generate it in spider methods.")

    def start(self) -> NoReturn:
        """ 运行调度器，这会开启管道，然后执行爬虫的 start 方法
        """
        for pipeline in self._pipelines.values():
            pipeline.start()

        for spider in self._spiders.values():
            call = spider.start()
            self.add_callback_result(call, from_spider=spider)
        super().start()

    def run(self) -> NoReturn:
        """开始处理请求队列
        """
        while True:
            if self.pause and self.saving:
                while self.is_requesting():
                    time.sleep(0.1)
                encoding = self.save_data['encoding']
                path = self.save_data['path']
                auto_continue: bool = self.save_data['auto_continue']
                data = self.save_data['data']
                for d in data:
                    file_name: str = ''
                    content: str = ''
                    if d == 'md5':
                        file_name = 'md5.txt'
                        content = '\n'.join(self._requests_md5)
                    elif d == 'tags':
                        file_name = 'tags.json'
                        content = json.dumps(self.tags, ensure_ascii=False)
                    elif d == 'spider_list':
                        file_name = 'spider_list.json'
                        content = json.dumps(list(self._spiders.keys()), ensure_ascii=False)
                    elif d == 'pipeline_list':
                        file_name = 'pipeline_list.json'
                        content = json.dumps(list(self._pipelines.keys()), ensure_ascii=False)
                    elif d == 'request_list':
                        file_name = 'request_list.json'
                        result = []
                        for r in self._request_list:
                            result.append(r.to_dict())
                        content = json.dumps(result, ensure_ascii=False)
                    else:
                        Logger.error(f"Can't handle save {d}")
                        continue
                    with open(os.path.join(path, file_name), 'w', encoding=encoding) as f:
                        f.write(content)
                    Logger.info(f"save {file_name} finish")
                if auto_continue:
                    self.pause = False
                self.saving = False
                continue
            elif self.pause or not self._request_list or len(self._link_requests) >= self.max_link:
                time.sleep(0.1)
                continue

            try:
                request = self._request_list[0]
                self._request_list.remove(request)
                self._link_requests.append(request)
                request.start()
                # rest
                if self.request_interval > 0:
                    time.sleep(self.request_interval)
            except Exception as e:
                Logger.error(f'[Scheduler] {e}')

    def downloader_finish(self, result, request: Request) -> NoReturn:
        """ 当下载完成时，由 Request 调用。
        这会在请求队列中移除这个请求并自动调用解析函数
        """
        if request not in self._link_requests:
            Logger.error(f"The completed download is not in link_request list. {request}")
            return
        self._link_requests.remove(request)
        result = request.preparse(result, request)
        call = request.callback(result, request)
        self.add_callback_result(call, request.spider)

    def downloader_abandon(self, request: Request) -> NoReturn:
        """放弃一个请求
        """
        if request not in self._link_requests:
            Logger.error(f"The abandoned download is not in link_request list. {request}")
            return
        self._link_requests.remove(request)

    def downloader_retry(self, request: Request, jump_in_line: bool = False) -> NoReturn:
        """重试一个请求
        """
        if request not in self._link_requests:
            Logger.error(f"The retry download is not in link_request list. {request}")
            return
        if request in self._request_list:
            Logger.error(f"The retry download have not started to request. {request}")
            return
        self._link_requests.remove(request)
        if jump_in_line:
            self._request_list.insert(0, request)
        else:
            self._request_list.append(request)

    def get_tag(self, key: str, default=None) -> Any:
        """获取 tag。支持使用切片进行这个操作

        Args:
            key: key
            default: 若key不存在，则返回这个默认值，默认：None

        Returns:
            获取到的值

        """
        if key in self._tags:
            return self._tags[key]
        else:
            return default

    def __getitem__(self, item: str):
        return self.get_tag(item)

    def set_tag(self, key: str, value: Any) -> NoReturn:
        """设置 tag 的数据，支持使用切片进行这个操作。
        建议只存放基础数据类型，如 int、float、str、list、dict。

        Args:
            key: key
            value: 要设置的值

        Warnings:
            这个操作是线程安全的，但要注意 value 自身的线程安全性。

        """
        self._tags_lock.acquire()
        self._tags[key] = value
        self._tags_lock.release()

    def __setitem__(self, key: str, value):
        self.set_tag(key, value)

    def save(self, dir_path: str, encoding: str = 'utf-8', auto_continue: bool = False, fast: bool = False) -> NoReturn:
        """ 保存调度器状态到一个目录。
        这包括等待请求列表、请求历史记录的md5（用于去重）、tags、管道和爬虫的唯一标识（读取时检查）
        配合 load 方法使用
        Args:
            dir_path: 目标目录
            encoding: 文件编码
            auto_continue: 保存完成后是否自动继续
            fast: 是否快速保存，这会取消当前正在进行的请求。
                取消的请求不会放弃，会重新添加到待请求队列中
        Warnings:
            这个方法的实际效果是在 调度器 线程中执行的，所以保存会有延迟
        """
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        if not os.path.isdir(dir_path):
            raise MagicSaveError(f"Save dir '{dir_path}' not is a dir")
        Logger.info("Pause the scheduler, it will be saved after the existing request is completed")

        if fast:
            stops = []
            for lr in self._link_requests:
                lr.stop()
                stops.append(lr)
            stops.reverse()
            for s in stops:
                self._link_requests.remove(s)
                self._request_list.insert(0, s)
            Logger.info(f"Fast save canceled the connection in {len(stops)} requests")

        self.pause = True
        self.saving = True
        self.save_data = {
            'path': dir_path,
            'encoding': encoding,
            'auto_continue': auto_continue,
            'data': [
                'md5',
                'request_list',
                'tags',
                'spider_list',
                'pipeline_list'
            ]
        }

    def load(self, dir_path: str, encoding: str = 'utf-8') -> NoReturn:
        """ 从某个目录读取完整的调度器状态。
        配合 save 方法使用

        Args:
            dir_path: 目录
            encoding: 文件编码，默认 utf-8
        Warnings:
            tags 会合并，同名 key 会覆盖
        """
        # Spider Check
        with open(os.path.join(dir_path, 'spider_list.json'), 'r', encoding=encoding) as f:
            spider_identity_list = json.loads(f.read())
            for spider_identity in spider_identity_list:
                if spider_identity not in self._spiders:
                    Logger.warning(f"The spider is missing: {spider_identity}")

        # Pipeline Check
        with open(os.path.join(dir_path, 'pipeline_list.json'), 'r', encoding=encoding) as f:
            pipeline_identity_list = json.loads(f.read())
            for pipeline_identity in pipeline_identity_list:
                if pipeline_identity not in self._pipelines:
                    Logger.warning(f"The pipeline is missing: {pipeline_identity}")

        # load requests
        with open(os.path.join(dir_path, 'request_list.json'), 'r', encoding=encoding) as f:
            request_list = json.loads(f.read())
            count = 0
            for request_dict in request_list:
                r = Request.from_dict(request_dict, self)
                if r.spider is None:
                    Logger.warning("Request parse Spider fil")
                self.add_request(r, r.spider)
                count += 1

        # load tags
        with open(os.path.join(dir_path, 'tags.json'), 'r', encoding=encoding) as f:
            tags = json.loads(f.read())
            for k, v in tags.items():
                if k in self._tags:
                    Logger.warning(f'The {k} key in the read tags already exists,' +
                                   ' which will overwrite the existing value')
                self[k] = v

        # load MD5 list
        with open(os.path.join(dir_path, 'md5.txt'), 'r', encoding=encoding) as f:
            self._requests_md5 = f.read().split('\n')
        Logger.info(f"Load '{dir_path}' finish")

    def get_spider_by_identity(self, identity: str) -> Spider:
        return self._spiders[identity]

    def get_pipeline_by_identity(self, identity: str) -> Pipeline:
        return self._pipelines[identity]

    def is_requesting(self) -> bool:
        """ 是否有正在请求的连接
        """
        return len(self._link_requests) > 0
