# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class QuestionItem(scrapy.Item):
    # define the fields for your item here like:
    url_token = scrapy.Field()
    title = scrapy.Field()
    tag_list = scrapy.Field()
    follow_num = scrapy.Field()
    comment_num = scrapy.Field()
    visitor_num = scrapy.Field()
    answer_num = scrapy.Field()
    answer_top = scrapy.Field()
    answer_list = scrapy.Field()

class QuestionDetailItem(scrapy.Item):
    date = scrapy.Field()
    answer_first = scrapy.Field()

