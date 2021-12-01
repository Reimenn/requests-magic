class Item:
    def __init__(self, data: dict, spider=None, meta: dict = {}):
        super().__init__()
        self.data = data
        self.spider = spider
        self.scheduler = None
        self.meta: dict = meta

    def __getitem__(self, item):
        return self.meta[item]

    def __setitem__(self, key, value):
        self.meta[key] = value

    def has_key(self, key) -> bool:
        """
        KEY exist in META
        """
        return key in self.meta.keys()

    def __str__(self) -> str:
        return str(self.data)
