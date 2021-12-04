import requests_magic


class TestSpider(requests_magic.Spider):
    def start(self):
        return self.request("https://www.runoob.com/html/html-tutorial.html")

    def parse(self, result, request):
        text = result.text
        yield self.item({'content': text})


class TestPipeline(requests_magic.Pipeline):
    def save(self, item):
        print(item)
        pass


requests_magic.quick_start(TestSpider(), TestPipeline())
