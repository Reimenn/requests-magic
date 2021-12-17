""" 爬取 Lol 全部英雄信息
"""

import json
import os

from requests_magic import \
    Spider, Scheduler, Item, SimpleFileSaver, logger
from requests_magic.request import \
    Request, Response


class LOLHeroSpider(Spider):

    def __init__(self, scheduler: 'Scheduler' = None):
        super().__init__(scheduler, "LOLHeroSpider")

    def start(self):
        yield Request(
            url="https://game.gtimg.cn/images/lol/act/img/js/heroList/hero_list.js",
            callback=self.parse
        )

    def parse(self, response: Response, request: Request):
        hero_list = response.json['hero']
        for hero in hero_list:
            yield Request(
                url=
                "https://game.gtimg.cn/images/lol/act/img/js/"
                f"hero/{hero['heroId']}.js",
                callback=self.parse_detail,
                tags={'title': hero}
            )

    def parse_detail(self, response: Response, request: Request):
        yield Item(
            data={
                'detail': response.json,
                'title': request.tags['title']
            },
            tags={
                'file':
                    f"./heros_json/{response.json['hero']['name']}.json"
            }
        )


class JsonSaver(SimpleFileSaver):

    def save(self, item: 'Item'):
        """ 复制的 SimpleFileSaver 代码"""
        file = item.tags[self.output_file_tag_key]
        path = os.path.abspath(os.path.join(file, '../..'))
        if not os.path.exists(path):
            if self.auto_create_folder:
                os.makedirs(path)
            else:
                logger.error_saver(f"{self} {path} path not exists")
                return
        if not os.path.isdir(path):
            logger.error_saver(f"{self} {path} not is a dir")
            return
        with open(file, 'w', encoding=self.encoding,
                  newline=self.newline) as f:
            # 最后这里做了更改，改成了Json
            f.write(json.dumps(item, ensure_ascii=False))


Scheduler(LOLHeroSpider, JsonSaver,
          request_interval=0, web_view=3000).start()
