# requests-magic

效仿 scrapy 制作的爬虫框架

-----

### 特点

- 简单易学

- 多线程下载

- 可保存、读取爬取状态

- 基于Bottle 的 Web 监控页面

- 下载中间件、下载过滤器、预解析器

- Pipeline ← Item ← Scheduler ←→ Request ←→ Spider

- 默认下载件基于 requests

- 只依赖 requests 模块，甚至简单修改即可取消依赖 requests

### 极速入门

开始工作就是继承 Spider 实现一个你的爬虫类

```python
import requests_magic as rm


class MySpider(rm.Spider):

    def start(self):
        # start 方法会在一开始调用
        yield rm.Request(url='http://balabalaba.com', callback=self.parse)

    def parse(self, result, request):
        # yield 一个 item 就是持久化数据，或者 yield 一个 Request 发起新的请求
        yield rm.Item(data={'text': result.text}, tags={'file': 't.txt'})
```

看起来和 Scrapy 一模一样是不是。

最后弄一个调度器开始爬虫：

```python
rm.Scheduler(MySpider, rm.SimpleFilePipeline, web_view=3344).start()
# web_view 可以在 3344 端口开启一个 web 页面用来监控爬虫状态
# 第一个参数表示爬虫，可以传进去一个列表，多个爬虫同时工作
# 第二个参数表示管道，可以传进去一个列表，多个管道同时保存
```

SimpleFilePipeline 默认会根据 Item 中 tags 的 file 保存文件，或者也可以自己写一个简单的文件保存：

```python
import requests_magic as rm


class MyPipeline(rm.Pipeline):
    def save(self, item):
        with open(item.tags['file'], 'w') as f:
            f.write(str(item))  
```

### 关于架构

相比 scrapy ，省掉了好多东西（因为懒得写）

![project](project.png)

