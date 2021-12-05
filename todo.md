### 计划

- [ ] 三段式下载中间件（预处理-下载-结果处理）

- [ ] 预解析中间件（在调用解析函数之前的处理）

- [ ] 管道队列

- [ ] 监控器，纪录爬虫状态

- [x] 更好地匹配 requests.request 的参数

### v1.1

- [x] 替换掉 Spider 类中的 item 方法和 request 方法，直接实例化类就行了

- [x] 自动去重，通过纪录 request 的 md5 实现

- [x] 下载器中超时重请求，通过捕获 Timeout 异常实现

- [x] 下载器中主动重请求，通过 raise RequestCanRetryError 实现

- [x] 全局请求头