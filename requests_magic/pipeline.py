import threading
from .logger import Logger


class Pipeline(threading.Thread):
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
                    Logger.info(f"[SAVE {len(self.items)}]")
                except Exception as e:
                    Logger.error(f"[SAVE {len(self.items)}] {e}")

    def save(self, item):
        pass
