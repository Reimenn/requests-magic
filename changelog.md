## v1.1-beta

2021年12月5日

---

#### 修改：

**弃用 Spider 类中的 item 方法和 request 方法**

> 现在直接实例化 Item 或 Request 类即可
> 
> 为此牺牲了它们俩的 spider 属性，它们不再纪录自己的 Spider 了

#### 新功能：

**自动去重**

> 通过纪录 request 的 md5 实现
> 
> 给 Request 添加了返回 md5 的方法，通过 method、url、data 三个参数计算
>
> Scheduler 有一个 requests_md5 list 纪录已经存在的 request

**下载器中超时重请求**

> 添加了一些异常类，其中 RequestTimeoutError 会让 Request 实现超时重请求
> 
> 可以给 Request 设置超时时间、重试等待时间、最大重试次数

**下载器中主动重请求**

> 添加的异常类中 RequestCanRetryError 会让 Request 无条件重请求
> 
> RequestTimeoutError 也继承自这个类

**全局请求头**

> 就是在 `request.py` 里定义了一个模块变量，每个 Request 的 headers 如果是 None，则copy这个变量

## v1.0.1

2021年12月4日

---

调整了一些代码结构，编码应该是更规范了。

加入了`setup.py`文件，方便本地安装了。