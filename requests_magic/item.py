class Item(dict):
    def __init__(self, data: dict, tags: dict = None):
        super().__init__()

        for k, v in data.items():
            self[k] = v

        if tags is None:
            tags = {}
        self.tags: dict = tags

        self.spider = None
        self.scheduler = None
