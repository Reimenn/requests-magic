""" 爬取 17k 小说网。
这里只爬 《化龙：开局菜花蛇，用我煲蛇羹？》
"""
import os
from typing import List

from lxml import etree
from requests_magic import \
    Spider, Scheduler, Item, Saver, logger
from requests_magic.request import \
    Request, Response


class KSpider(Spider):
    def start(self):
        yield Request(
            url="https://www.17k.com/list/3375693.html",
            callback=self.parse
        )

    def parse(self, response: Response, request: Request):
        root = etree.HTML(response.text)
        a_list = root.xpath(
            r'//dl[@class="Volume"]//dd//a'
        )
        book = root.xpath(r'//h1[@class="Title"]/text()')[0]
        for a in a_list:
            href: str = a.xpath('@href')[0].strip()
            chapter: str = a.xpath('./span/text()')[0].strip()
            yield Request(
                url=f"https://www.17k.com/{href}",
                callback=self.parse_content,
                tags={
                    'book': book,
                    'chapter': chapter
                }
            )

    def parse_content(self, response: Response, request: Request):
        root = etree.HTML(response.text)
        result: List[str] = []
        p_list = root.xpath(
            '//div[@class="readAreaBox content"]/div[@class="p"]/p')
        for p in p_list:
            result.append(p.xpath('text()')[0])
        return Item(
            data={
                'text': '\n\n'.join(result)
            },
            tags=request.tags.copy()
        )


class KSaver(Saver):
    def save(self, item: 'Item'):
        dir = f'./{item.tags["book"]}/'
        if not os.path.exists(dir):
            os.makedirs(dir)
        with open(
                os.path.join(dir, f'{item.tags["chapter"]}.txt'),
                'w',
                encoding='utf-8',
        ) as f:
            f.write(item['text'])


Scheduler(KSpider, KSaver).start()
