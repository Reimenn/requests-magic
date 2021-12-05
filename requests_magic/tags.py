class Tags:
    def __init__(self, tags: dict = None):
        if tags:
            self.tags = tags
        else:
            self.tags = {}

    def __getitem__(self, item):
        return self.tags[item]

    def __setitem__(self, key, value):
        self.tags[key] = value

    def __contains__(self, item):
        return item in self.tags
