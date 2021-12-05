## v1.2-beta

2021年12月5日

---

#### 添加：

**预解析方法**

> 在调用 callback 之前会先调用一个预解析方法，它可以对数据进行一些预处理，默认的预解析方法是 callback 所在 Spider 的 preparse 方法，内部不做任何处理（仅返回 result）

**下载过滤器**

> 在下载器完成下载后调用的一个方法，它不需要返回值，依据请求结果在过滤器中抛出异常，效果和下载器中抛出异常相同

**管道队列**

> 同一个 Scheduler 可以拥有多个管道，根据管道类的 acceptable 方法决定是否向其中添加 Item，默认该方法始终返回 True

#### 修改：

**spider 的 item 和 request 方法添加了 \*\*kwargs 参数，可以直接传到对应的 Class 里**

**Request 和 Item 类的 spider 属性又加回来了，Request 的 spider 会自动根据 callback 获取，Item 的 spider 由 Scheduler 根据 Request 获取**

**全文的meta属性都换成了tags，改个名字而已**

**Item 类放弃了 data 属性，而是直接继承自了 dict**

**Request 和 Item 不能再通过切片获取 meta（tags） 的值了，只能通过 .tags 引用**

## v1.1-beta-f1

2021年12月5日

---

#### 修复：

**默认下载器的参数传递问题**

> 现在起 Request 类的 data 属性更加“智能”一些些
>
> 如果请求是 get 就把 data 当做 params 参数
>
> 如果请求不是 get 且 data 是 dict，则会当做 json 参数，不是 dict 就当做 data 参数
>
> 同时给 Request 加上了 kwargs， 默认下载器中会将其直接添加到 requests.request 参数中

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