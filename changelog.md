## v1.4-beta-2

2021年12月10日

---

#### 添加：

- 调度器的 start 方法添加了 load_from 参数，可以指定从某个目录中读取爬取状态，这可以跳过 Spider 的 start 方法，如果这个目录不存在或不指定参数，则和直接 start
  效果相同，为此可以通过这个参数设定一个类似“工程目录”的东西，方便“中断续爬”。当然这个中断之前需要手动调用 save 方法。

> 调度器同时添加了 self.load_from 属性，用来纪录当前调度器是从哪里读取的

#### 修改：

- 调度器增加了 _wait_request_list 用来保存重试等待中的请求，目的是修复保存时无法保存重试等待中的请求。

> 在调用 save 方法时，这个列表会被重新添加到待请求列表中，因此 save 操作会清除重试请求的延迟时间

- 移除了 exception 模块，因为没啥用，唯一使用的调度器 save 方法中的 MagicSaveError 换成了 NotADirectoryError 错误

## v1.4-beta

2021年12月9日

---

#### 添加：

- 给调度器增加了个 request_log 属性，这会自动纪录下载器完成时的状态和操作，这里只包含请求的基本信息（url\method\time\spider 等）

- 导入了 Bottle.py 文件，并对内容做了一些删减

- 给 Scheduler 构造方法加了一个 web_view 参数，可以设置一个显示调度器状态的 web 页面

> 在 web 页面中可以查看请求队列和新增加的 request_log，还可以操作调度器暂停、继续、保存

#### 修改：

- Request 中的 start_time 的赋值改到了 Request 的 start 方法，不在 RequestThread 线程中了

- 当请求需要重试时，将立刻从 link_requests 中移除，等待重试时间后，添加到待请求队列

#### TODO：

- 需要做一个 等待重试队列

## v1.3.1

2021年12月8日

---

#### 修改：

- default_headers 从 Request 模块移动到了 Spider 上，可在 Spider 中设置 self.default_headers 控制从这个 Spider 产生的请求默认头

## v1.3-beta

2021年12月8日

---

#### 添加：

- Scheduler 加了一个 tags 属性，用来纪录一些额外信息，计划做中断续爬功能时用到

- Scheduler 添加了 save\load 方法，用来持久化调度器状态

- 同时增加了 get_tag、set_tag 方法以及对应的切片方式调用

- 添加了 HasNameObject 工具类，重写了 `__str__` ，pipeline、spider等都继承了他

#### 修改：

- Spider 和 Pipeline 可以 self.scheduler 了

- 修改了调度器的启动方式和组织结构，现在可以抛弃 quick_start 和 start 方法了，直接实例化 Scheduler 即可

- 更改了 Scheduler 的构造方法

- 把 Request 类中 to_json 和 from_json 方法中转换 dict 的操作独立了出来，提取出了新的 to_dict 和 from_dict 方法

## v1.2.1-beta

2021年12月7日

---

#### 添加：

- Request 可以转换成json，也可以从json生成，方便持久化

- 调度器增加了 pause 属性，可以暂停发送新请求

#### 修改：

- 在调度器和管道的线程中，如果没有可发送的请求或没有可保存的 Item，则会线程休眠 0.1 秒，为了减少CPU占用

#### 修复：

- 修复 Request 的 kwargs 参数不能转换成 requests.request 的错误

## v1.2-beta-f2

2021年12月6日

---

完善了文档

## v1.2-beta-f1

2021年12月6日

---

#### 添加：

**name 属性**

> 给 Pipeline、Spider、Item、Request 添加了 name 属性，会在日志中显示，希望能对排错有帮助

#### 修复：

**重请求添加到调度器**

> 修复了重请求无视调度器请求间隔时间 Bug，现在的重请求会重新添加到 Scheduler 中。
>
> 为此，建立了一个新的 RequestThread 类，Request 类的 start 方法会实例化一个新的 RequestThread 来发送请求（曾经的Request直接继承自Thread，导致其不能反复start，现在可以反复start了）

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