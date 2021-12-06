class Item(dict):
    """
    表示需要持久化的数据，本质上是个字典
    """

    def __init__(self, data: dict, tags: dict = None, name: str = ''):
        """
        表示需要持久化的数据，本质上是个字典
        Parameters
        ----------
        data
            想要持久化的数据，可以通过切片这个实例的形式更改
        tags
            标签，用来记录一些额外内容
        name
            名字，在日志中显示，应该能帮助 debug
        Examples
        --------
        >>> import requests_magic as rm
        >>> # 在你的爬虫回调函数中：
        >>>     yield rm.Item(result.json(),tags={'file':'./output.json'})
        >>> # 如果使用了 SimpleFilePipeline，这个 Item 会自动保存到 output.json 中
        """
        super().__init__()
        self.name = name
        for k, v in data.items():
            self[k] = v

        if tags is None:
            tags = {}
        self.tags: dict = tags

        self.spider = None
        self.scheduler = None
