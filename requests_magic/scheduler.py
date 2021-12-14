import json
import os.path
from collections import Generator
from typing import Sequence, List, NoReturn, Dict, Any, Optional, Callable, Iterable, Mapping
from dataclasses import dataclass
from .request import Request
from .item import Item
from .spider import Spider
from .pipeline import Pipeline
from .mmlog import logger
from .exception import *
import threading

import time

from .utils import Looper


class Scheduler:
    """调度器，核心组件，负责请求管理与 item 转发
    """

    def __init__(self, spiders=None, pipelines=None,
                 call_start_spider: bool = True,
                 auto_start_pipeline: bool = True,
                 tags: Dict[str, Any] = None,
                 max_link: int = 12,
                 request_interval: float = 0,
                 distinct: bool = True,
                 start_pause: bool = False,
                 web_view=None):
        """调度器，核心组件，爬虫的开始，负责请求管理与 item 转发

        Args:
            spiders: spider 或 spider list. 可以是 spider 实例也可以是 spider class
            pipelines: pipeline 或 pipeline list. 可以是 pipeline 实例也可以是 pipeline class
            call_start_spider: 是否调用爬虫实例们的start方法. 如果 spider是class 则忽略这个参数强制调用
            auto_start_pipeline: 是否自动开启 pipeline, 如果 pipeline 是 class 则忽略这个参数强制开启
            tags: 可以用来保存额外信息，例如纪录爬虫状态，可以由管道或爬虫更改.
            max_link: 最大连接数，默认：12.
            request_interval: 请求间隔时间，默认：0秒.
            distinct: 是否开启去重，默认开启.
            start_pause: 调度器开启时是否处于暂停状态.
            web_view: 可在浏览器上查看的页面，默认关闭（None），可以设置为一个端口号，或是一个包含ip与端口的元组

        Warnings:
            注意线程安全问题
        """
        super().__init__()
        self.distinct = distinct
        self.max_link: int = max_link
        self.request_interval: float = request_interval

        # tags

        if not tags:
            tags = {}
        self._tags = tags.copy()

        # 爬虫们
        self._spiders: Dict[str, Spider] = {}
        if not isinstance(spiders, Sequence):
            spiders = [spiders]
        for i in spiders:
            if isinstance(i, Spider):
                self.add_spider(i, call_start=call_start_spider)
            elif isinstance(i, type):
                self.add_spider(i(scheduler=self), call_start=True)
            else:
                logger.error(f"[{i}] not is a spider or spider class")

        # 管道们
        self._pipelines: Dict[str, Pipeline] = {}
        if not isinstance(pipelines, Sequence):
            pipelines = [pipelines]
        for i in pipelines:
            if isinstance(i, Pipeline):
                self.add_pipeline(i, auto_start=auto_start_pipeline)
            elif isinstance(i, type):
                self.add_pipeline(i(scheduler=self), auto_start=True)
            else:
                logger.error(f"[{i}] not is a pipeline or pipeline class")

        # 请求队列
        self._request_list: List[Request] = []
        # 正在请求中的请求
        self._link_requests: List[Request] = []
        # 请求冷却剩余时间
        self._request_wait_time: float = 0
        # 添加过的请求的 MD5
        self._requests_md5: List[str] = []
        # 响应队列
        self._response_list: List[tuple] = []

        # 是否暂停了
        self._pause: bool = start_pause
        # 是否在保存中
        self._saving: bool = False
        # 请求纪录，只保留一些基本信息（url，method，时间，结果状态码，spider）
        self.request_log = []

        # web view
        if web_view:
            port = 5012
            host = 'localhost'
            if isinstance(web_view, Sequence):
                port = web_view[1]
                host = web_view[0]
            elif isinstance(web_view, int):
                port = web_view
            from .webview import SchedulerWebView
            SchedulerWebView(self, host, port).start()
        #
        self.load_from: str = ''

        # looper
        self.request_looper = Looper(target=self._request_loop)
        self.response_looper = Looper(target=self._response_loop)

        # lock
        self._request_list_lock = threading.Lock()
        self._other_lock = threading.Lock()

    # add

    def add_request(self, request: Request, from_spider: Spider) -> NoReturn:
        """添加一个新的请求到请求队列（不会立刻执行）

        Args:
            request: 请求
            from_spider: 产生请求的 Spider
        """
        md5: str = request.md5()
        # lock
        self._request_list_lock.acquire()
        if self.distinct and md5 in self._requests_md5:
            logger.info_repetated(f'Repeated request: {request} {request.show_url}')
            self._request_list_lock.release()
            return
        request.spider = from_spider
        request.scheduler = self
        self._requests_md5.append(md5)
        self._request_list.append(request)
        self._request_list_lock.release()

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
                logger.error(
                    f"Cannot handle {str(type(result))}, " +
                    f"Please do not generate it in spider methods.")

    def add_spider(self, spider: Spider, call_start: bool = False) -> NoReturn:
        """ 添加一个已经实例化好的 spider.

        Args:
            spider: spider 实例（注意不是 class）
            call_start: 是否执行爬虫的 start 方法

        Raises:
            ExistingIdentityError
        """
        identity = spider.identity
        self._other_lock.acquire()
        if identity in self._spiders:
            self._other_lock.release()
            raise ExistingIdentityError(identity)
        if call_start:
            self.add_callback_result(spider.start(), spider)
        self._spiders[identity] = spider
        self._other_lock.release()

    def add_pipeline(self, pipeline: Pipeline, auto_start: bool = True) -> NoReturn:
        """ 添加一个已经实例化好的 pipeline。
        如果管道线程没有运行则会尝试 start

        Args:
            pipeline: 管道实例（注意不是 class）
            auto_start: 是否尝试开启管道

        Raises:
            ExistingIdentityError
        """
        identity = pipeline.identity
        self._other_lock.acquire()
        if identity in self._pipelines:
            self._other_lock.release()
            raise ExistingIdentityError(identity)
        if not pipeline.is_running and auto_start:
            pipeline.start()
        self._pipelines[identity] = pipeline
        self._other_lock.release()

    # thread
    def _request_loop(self, delta_time: float):
        self._request_wait_time = max(self._request_wait_time - delta_time, 0)
        for r in self._request_list.copy():
            # time
            r.wait = max(r.wait - delta_time, 0)
            if r.wait > 0:
                continue
            # new link
            if self._request_wait_time <= 0 and len(self._link_requests) < self.max_link:
                self._request_list.remove(r)
                self._link_requests.append(r)
                r.start()
                # wait
                self._request_wait_time = self.request_interval

    def _response_loop(self, delta_time: float):
        for r in self._response_list.copy():
            response = r[0]
            request: Request = r[1]
            try:
                result = request.preparse(response, request)
                call = request.callback(result, request)
            except Exception as e:
                logger.ERROR(f"{request.spider} - {request} Error: {e}")
                return
            self.add_callback_result(call, request.spider)
            # remove
            self._response_list.remove(r)

    def start(self, load_from: str = None, load_encoding: str = 'utf-8', only_load: bool = True) -> NoReturn:
        """ 运行调度器，这会开启管道，然后执行爬虫的 start 方法

        Args:
            only_load: 如果从文件夹中读取了状态，是否仅用读取的状态开始爬虫（这将不再执行 Spider 的 start 方法），默认 开启
            load_encoding: 读取状态的编码，默认 utf-8
            load_from: 从某个文件夹中读取爬取状态，默认 None 或目录不存在则表示不读取
        """

        if self.is_running:
            logger.WARNING_SCHEDULER("Scheduler is running")
            return

        for pipeline in self._pipelines.values():
            pipeline.start()

        self.load_from = load_from

        if load_from and os.path.exists(load_from):
            self.load(load_from, load_encoding)
            if only_load:
                self.request_looper.start()
                self.response_looper.start()
                return

        for spider in self._spiders.values():
            call = spider.start()
            self.add_callback_result(call, from_spider=spider)
        self.request_looper.start()
        self.response_looper.start()

    # downloader

    def downloader_finish(self, result, request: Request) -> NoReturn:
        """ 当下载完成时，由 Request 调用。
        这会在请求队列中移除这个请求并自动调用解析函数
        """
        if request not in self._link_requests:
            logger.error(f"The completed download is not in link_request list. {request}")
            return
        # append response
        self._response_list.append((result, request))
        # log
        state = 'OK'
        if hasattr(result, 'status_code'):
            state += ' ' + str(result.status_code)
        self._add_request_log(request, state)
        # remove
        self._link_requests.remove(request)

    def downloader_abandon(self, request: Request) -> NoReturn:
        """放弃一个请求
        """
        if request not in self._link_requests:
            logger.error(f"The abandoned download is not in link_request list. {request}")
            return

        # log
        self._add_request_log(request, 'Abandon')
        self._link_requests.remove(request)

    def downloader_retry(self, request: Request, jump_in_line: bool = False, wait: float = 0) -> NoReturn:
        """重试一个请求，如果有等待，则会让调用的线程暂停
        """
        if request not in self._link_requests:
            logger.error(f"The retry download is not in link_request list. {request}")
            return
        if request in self._request_list:
            logger.error(f"The retry download have not started to request. {request}")
            return

        # log
        self._add_request_log(request, 'To Retry')
        # remove and wait
        self._link_requests.remove(request)
        request.wait = wait
        # insert or append
        if jump_in_line:
            self._request_list.insert(0, request)
        else:
            self._request_list.append(request)

    # tags

    def get_tags_copy(self) -> dict:
        """ 获取一份 tags 的拷贝。
        """
        return self._tags.copy()

    def get_tag(self, key: str, default=None):
        """ 获取 tag, 如果不存在则返回默认值
        """

        if key in self:
            return self[key]
        return default

    def __getitem__(self, item: str):
        return self._tags[item]

    def __setitem__(self, key: str, value):
        self._tags[key] = value

    def __contains__(self, item: str) -> bool:
        return item in self._tags

    # get by identity

    def get_spider_by_identity(self, identity: str) -> Spider:
        """ 根据 identity 获取某个爬虫
        """
        return self._spiders[identity]

    def get_pipeline_by_identity(self, identity: str) -> Pipeline:
        """ 根据 identity 获取 pipeline
        """
        return self._pipelines[identity]

    # state

    @property
    def is_running(self) -> bool:
        """ 调度器线程是否正在运行。
        即使暂停了调度器这也返回 True，这只代表调度器线程状态，而不是调度状态
        """
        return self.response_looper.is_alive() or self.request_looper.is_alive()

    @property
    def is_requesting(self) -> bool:
        """ 是否有正在请求的连接
        """
        return len(self._link_requests) > 0

    @property
    def is_parsing(self) -> bool:
        """ 是否有等待被解析的数据
        """
        return len(self._response_list) > 0

    @property
    def is_saving(self) -> bool:
        """ 是否正处于保存中
        """
        return self._saving

    @property
    def is_pause(self) -> bool:
        """ 是否在暂停中
        """
        return self._pause

    @property
    def is_saveable(self) -> bool:
        """ 获取当前状态是否可保存。
        可保存需要关闭请求 Looper、完成全部现存请求、
        解析完全部现存响应、不在 response_looper 的 in_action中、
        暂停调度器、调度器的 is_saving 为 True
        """
        if not self.request_looper.is_pause:
            return False
        if self.is_requesting:
            return False
        if self.is_parsing:
            return False
        if self.response_looper.in_action:
            return False
        if not self.is_pause:
            return False
        if not self.is_saving:
            return False
        return True

    def pause(self):
        """ 暂停调度器，这会阻止新链接发送。
        但不会停止现存连接
        """
        self.request_looper.pause()
        # self.response_looper.pause()
        self._pause = True

    def unpause(self):
        """ 解除暂停，开始发送新链接
        """
        self.request_looper.unpause()
        # self.response_looper.unpause()
        self._pause = False

    # get info

    def get_pending_request_info(self) -> List[dict]:
        """ 获取请求等待队列的信息

        Returns:
            表示信息的字典，不是请求实例！
        """
        result: List[dict] = []
        for r in self._request_list:
            result.append({
                'method': r.method,
                'url': r.url,
                'data': r.data.copy(),
                'headers': r.headers.copy(),
                'tags': r.tags.copy(),
                'spider': r.spider.identity,
                'downloader': r.downloader.__name__,
                'downloader_filter': r.downloader_filter.__name__,
                'wait': r.wait
            })

        # result.sort(key=lambda x: x['wait'], reverse=False)
        return result

    def get_link_request_info(self) -> List[dict]:
        """ 获取正在下载中的请求信息

        Returns:
            表示信息的字典，不是请求实例！
        """
        result = []
        for r in self._link_requests:
            result.append({
                'method': r.method,
                'url': r.url,
                'data': r.data.copy(),
                'headers': r.headers.copy(),
                'tags': r.tags.copy(),
                'spider': r.spider.identity,
                'downloader': r.downloader.__name__,
                'downloader_filter': r.downloader_filter.__name__,
                'start_time': r.start_time
            })
        return result

    def get_request_log_info(self) -> List[dict]:
        """ 获取请求纪录的 copy

        Returns:
            表示信息的字典，不是请求实例！
        """
        return self.request_log.copy()

    # add log

    def _add_request_log(self, request: 'Request', state: str):
        """ 当需要纪录请求状态时调用
        """
        self.request_log.append({
            'url': request.url,
            'method': request.method,
            'state': state,
            'start_time': request.start_time,
            'total_time': request.total_time,
            'spider': request.spider.identity
        })

    # save and load

    def save(self, dir_path: str = None, encoding: str = 'utf-8', auto_continue: bool = False,
             fast: bool = False) -> NoReturn:
        """ 保存调度器状态到一个目录。
        这包括等待请求列表、请求历史记录的md5（用于去重）、tags、管道和爬虫的唯一标识（读取时检查）
        配合 load 方法使用
        Args:
            dir_path: 目标目录，如果不指定，则会使用 start 方法的 load_from
            encoding: 文件编码，默认 utf-8
            auto_continue: 保存完成后是否自动继续
            fast: 是否快速保存，这会取消当前正在进行的请求。
                  取消的请求不会放弃，会重新添加到待请求队列中
        Warnings:
            这个方法的实际效果是在 调度器 线程中执行的，所以保存会有延迟。
            这不会保存 web 页面中显示的 History Request 列表，也就是不会保存 request_log
        """
        if dir_path is None:
            dir_path = self.load_from
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        if fast:
            logger.info_scheduler("Pause the scheduler, it will be saved")
            stops = []
            self._request_list_lock.acquire()
            for lr in self._link_requests:
                lr.stop()
                stops.append(lr)
            stops.reverse()
            for s in stops:
                self._link_requests.remove(s)
                self._request_list.insert(0, s)
            self._request_list_lock.release()
            logger.info_scheduler(f"Fast save canceled the connection in {len(stops)} requests")
        else:
            logger.info_scheduler("Pause the scheduler, it will be saved after the existing request is completed")

        self.pause()
        self._saving = True

        def callback():
            self._saving = False
            if auto_continue:
                self.unpause()

        def error_callback(e: Exception):
            logger.ERROR(f"An error occurred while saving in the scheduler: {e}")
            self._saving = False
            if auto_continue:
                self.unpause()

        SchedulerSaver(scheduler=self,
                       callback=callback, error_callback=error_callback,
                       path=dir_path, encoding=encoding).start()

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
                    logger.warning(f"The spider is missing: {spider_identity}")

        # Pipeline Check
        with open(os.path.join(dir_path, 'pipeline_list.json'), 'r', encoding=encoding) as f:
            pipeline_identity_list = json.loads(f.read())
            for pipeline_identity in pipeline_identity_list:
                if pipeline_identity not in self._pipelines:
                    logger.warning(f"The pipeline is missing: {pipeline_identity}")

        # load requests
        with open(os.path.join(dir_path, 'request_list.json'), 'r', encoding=encoding) as f:
            request_list = json.loads(f.read())
            count = 0
            for request_dict in request_list:
                r = Request.from_dict(request_dict, self)
                if r.spider is None:
                    logger.warning("Request parse Spider fil")
                self.add_request(r, r.spider)
                count += 1

        # load tags
        with open(os.path.join(dir_path, 'tags.json'), 'r', encoding=encoding) as f:
            tags = json.loads(f.read())
            for k, v in tags.items():
                if k in self._tags:
                    logger.warning(f'The {k} key in the read tags already exists,' +
                                   ' which will overwrite the existing value')
                self[k] = v

        # load MD5 list
        with open(os.path.join(dir_path, 'md5.txt'), 'r', encoding=encoding) as f:
            self._requests_md5 = f.read().split('\n')
        logger.info_scheduler(f"Load '{dir_path}' finish")

    def get_save_info(self) -> 'SchedulerSaveInfo':
        save_info = SchedulerSaveInfo(
            tags=self._tags.copy(),
            request_list=self._request_list.copy(),
            requests_md5=self._requests_md5.copy(),
            pipeline_identity_list=list(self._pipelines.keys()),
            spider_identity_list=list(self._spiders.keys())
        )
        return save_info
        pass


@dataclass
class SchedulerSaveInfo:
    tags: Dict[str, Any]
    requests_md5: List[str]
    request_list: List[Request]
    spider_identity_list: List[str]
    pipeline_identity_list: List[str]


class SchedulerSaver(threading.Thread):
    """ 调度器保存器，需要配合 SchedulerSaveInfo 使用
    """

    def __init__(self, scheduler: Scheduler,
                 callback: Callable[[], NoReturn],
                 error_callback: Callable[[Exception], NoReturn],
                 path: str, encoding: str):
        """ 调度器保存期

        Args:
            scheduler: 调度器
            callback: 保存成功后的回调方法
            info: 需要保存的信息
        """
        super().__init__()
        self.encoding = encoding
        self.path = path
        self.scheduler = scheduler
        self.callback = callback
        self.error_callback = error_callback

    def _save_to_file(self, file: str, content: str):
        final_file = os.path.join(self.path, file)
        with open(final_file, 'w', encoding=self.encoding) as f:
            f.write(content)
        logger.info_scheduler(f"Save {file} finish to {self.path}")

    def run(self) -> None:
        # check
        if not self.scheduler.is_pause or not self.scheduler.is_saving:
            raise Exception("Save scheduler must pause and set saving to True")
        # wait
        while not self.scheduler.is_saveable:
            time.sleep(0.1)
        try:
            # SAVE
            info = self.scheduler.get_save_info()
            self._save_to_file('md5.txt', '\n'.join(info.requests_md5))
            self._save_to_file('tags.json', json.dumps(info.tags, ensure_ascii=False))
            self._save_to_file('spider_list.json', json.dumps(info.spider_identity_list, ensure_ascii=False))
            self._save_to_file('pipeline_list.json', json.dumps(info.pipeline_identity_list, ensure_ascii=False))
            result = []
            for request in info.request_list:
                result.append(request.to_dict())
            self._save_to_file('request_list.json', json.dumps(result, ensure_ascii=False))
            logger.info_scheduler(f"Save scheduler finish")
        except Exception as e:
            self.error_callback(e)
            return

        # Callback
        if self.callback:
            self.callback()
