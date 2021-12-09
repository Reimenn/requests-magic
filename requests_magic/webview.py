from .bottle import Bottle, SimpleTemplate, Route, request
import threading
import time
import os.path as path

__FUCK_CIRCULAR_IMPORT = False
if __FUCK_CIRCULAR_IMPORT:
    from .scheduler import Scheduler


def load_template(name, encoding='utf-8') -> SimpleTemplate:
    """ 在 web_view 目录中加载 html 文件

    Args:
        name: html 文件名（不包含后缀）
        encoding: 编码，默认 utf-8
    Returns:
        SimpleTemplate 实例
    """
    p = path.abspath(path.join(__file__, f'../web_view/{name}.html'))
    if not path.isfile(p):
        raise FileExistsError(p)
    f = open(p, 'r', encoding=encoding)
    r = f.read()
    f.close()
    return SimpleTemplate(r)


# 会用到的模板
index_template = load_template('index')
command_template = load_template('command')

# 如果开启，每次使用模板时将重新加载文件
debug = False


class SchedulerWebView(threading.Thread):
    """ 调度器 web 视图
    """

    def __init__(self, scheduler: 'Scheduler', host: str, port: int):
        """ 调度器视图，需要调用 start 方法开启

        Args:
            scheduler: 调度器
            host: web 页面的主机地址
            port: web 页面的端口地址
        """
        super().__init__()
        self.port = port
        self.host = host
        self.scheduler = scheduler
        self.app = Bottle()
        self.app.add_route(Route(self.app, '/', 'GET', self.index))
        self.app.add_route(Route(self.app, '/command/<args>', 'GET', self.command))

    def index(self) -> str:
        """ 首页 view
        """
        log = self.scheduler.get_request_log_info()
        pr = self.scheduler.get_pending_request_info()
        lr = self.scheduler.get_link_request_info()
        data = {
            'log': log,
            'pr': pr,
            'lr': lr,
            'time': time.time(),
            'pause': self.scheduler.pause,
            'saving': self.scheduler.saving
        }
        if debug:
            return load_template('index').render(**data)
        return index_template.render(**data)

    def command(self, args: str) -> str:
        """ 命令处理
        """
        state = {
            'state': 'ok',
            'message': '',
        }
        try:
            if args == 'pause':
                self.scheduler.pause = True
            elif args == 'continue':
                self.scheduler.pause = False
            elif args == 'save':
                save_path: str = str(request.query.path)
                fast: bool = str(request.query.fast) == 'on'
                self.scheduler.save(save_path, fast=fast, auto_continue=False)
            else:
                state['message'] = 'Unknown command'
        except Exception as e:
            state['state'] = 'error'
            state['message'] = str(e)
        if debug:
            return load_template('command').render(**state)
        return command_template.render(**state)

    def run(self) -> None:
        self.app.run(host=self.host, port=self.port)
