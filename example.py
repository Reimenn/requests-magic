import requests_magic as rm


class TestSpider(rm.Spider):
    def start(self):
        return rm.Request("https://www.runoob.com/html/html-tutorial.html", callback=self.parse)

    def parse(self, result, request):
        text = result.text
        yield rm.Item({'content': text})


class TestPipeline(rm.Saver):
    def save(self, item):
        print(item)
        pass


rm.Scheduler(TestSpider, TestPipeline).start()
