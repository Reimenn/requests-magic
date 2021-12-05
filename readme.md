# requests-magic

效仿 scrapy 制作的极简爬虫框架

-----

### 特点

- 多线程下载
- 下载中间件
- Pipeline ← Item ← Scheduler ↔ Request ↔ Spider
- 极简的代码
- 默认下载件基于 requests

### 极速入门

开始工作就是继承 Spider 实现一个你的爬虫类，再重写 Pipeline 重写一个你的持久化类。

调用 quick_start 方法开始爬虫，方法内会自动配置 Scheduler

```python
import requests_magic as rm


class MySpider(rm.Spider):
    ...


class MyPipeline(rm.Pipeline):
    ...


rm.quick_start(MySpider(), MyPipeline())
```

重写 Spider 的 start 方法开始第一个请求，默认会在 parse 方法中处理结果：

```python
class MySpider(rm.Spider):
    def start(self):
        yield rm.Request("http://balabala.com",self.parse)
    def parse(self, result, request):
        yield rm.Item(result.text, tags={'path':'./out'})
```

可以使用 yield 返回多个 Request 或 Item，也可以用 return 只返回一个，或 return 一个包含 request 或 item 的 list

重写 Pipeline 的 save 方法保存数据：

```python
class MyPipeline(rm.Pipeline):
    def save(self,item):
        with open(item.tags['path'],'w') as f:
            f.write(item.data) # item.data 才是真正的数据
```

### 关于架构

相比 scrapy ，省掉了好多东西（因为懒得写）

下载中间件其实就是一个方法，可以在 Request 里设置请求使用的下载方式，也就是说 Request 内包含了开始下载的代码，并没有单独的下载类。

Request 的回调方法是多线程执行的，注意线程安全，Pipeline 的 save 方法是单线程的。

### 日后计划

整一个 web 监控页面，可以查看爬虫情况

