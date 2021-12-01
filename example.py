import requestsMagic
from lxml import etree


class TestSpider(requestsMagic.Spider):
    def start(self):
        return self.request("https://www.runoob.com/html/html-tutorial.html")

    def parse(self, result, request):
        text = result.text
        tree = etree.HTML(text)
        a_list = tree.xpath(r'//div[@id="leftcolumn"]/a[@target="_top"]')
        for a in a_list:
            t = str(a.xpath('text()')[0]).strip()
            u = str(a.xpath('@href')[0]).strip()
            r = self.request("https://www.runoob.com/" + u, callback=self.parse_inner)
            r['title'] = t
            yield r

    def parse_inner(self, result, request):
        item = self.item(result.text)
        item['title'] = request['title']
        yield item


class TestPipeline(requestsMagic.Pipeline):
    def save(self, item):
        pass


requestsMagic.quick_start(TestSpider(), TestPipeline())
