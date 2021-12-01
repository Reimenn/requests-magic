import threading
from requestsMagic.logger import logger


class Pipeline(threading.Thread):
    """
    管道基类
    """

    def __init__(self):
        super().__init__()
        self.items = []

    def add_item(self, item):
        self.items.append(item)

    def run(self) -> None:
        while True:
            if self.items:
                item = self.items[0]
                del self.items[0]
                try:
                    self.save(item)
                    logger.info(f"[SAVE {len(self.items)}]")
                except Exception as e:
                    logger.error(f"[SAVE {len(self.items)}] {e}")

    def save(self, item):
        pass
