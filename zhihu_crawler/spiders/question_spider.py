# -*- coding:utf-8 -*-

import os
import platform
import random
import re
import sys
from getpass import getpass

import scrapy
import termcolor
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError

from zhihu_crawler import settings
from zhihu_crawler.items import QuestionItem


def get_captcha_code(response, logger):
    if int(response.status) != 200:
        raise HttpError(u"验证码请求失败")
    image_name = u"verify." + response.headers['content-type'].split("/")[1]
    open(image_name, "wb").write(response.body)
    """
        System platform: https://docs.python.org/2/library/platform.html
    """
    logger.info(u"正在调用外部程序渲染验证码 ... ")
    if platform.system() == "Linux":
        logger.info(u"Command: xdg-open %s &" % image_name)
        os.system("xdg-open %s &" % image_name)
    elif platform.system() == "Darwin":
        logger.info(u"Command: open %s &" % image_name)
        os.system("open %s &" % image_name)
    elif platform.system() in ("SunOS", "FreeBSD", "Unix", "OpenBSD", "NetBSD"):
        os.system("open %s &" % image_name)
    elif platform.system() == "Windows":
        os.system("%s" % image_name)
    else:
        logger.info(u"我们无法探测你的作业系统，请自行打开验证码 %s 文件，并输入验证码。" % os.path.join(os.getcwd(), image_name))

    sys.stdout.write(termcolor.colored(u"请输入验证码: ", "cyan"))
    captcha_code = raw_input()
    return captcha_code


class QuestionSpider(scrapy.Spider):
    name = 'question'

    index_url = 'http://www.zhihu.com'
    login_url_phone = 'http://www.zhihu.com/login/phone_num'
    login_url_email = 'https://www.zhihu.com/login/email'
    captcha_url = 'https://www.zhihu.com/captcha.gif'
    profile_url = 'https://www.zhihu.com/settings/profile'
    question_url = 'https://www.zhihu.com/question/'
    account = settings.USER_NAME
    password = settings.PASSWORD
    has_login = False

    def start_requests(self):
        if not self.account or not self.password:
            sys.stdout.write(u"请输入登录账号(空为不登陆爬取): ")
            self.account = raw_input()
            if self.account:
                self.password = getpass("请输入登录密码: ")

        # get xsrf first.
        if self.account:
            callback = self.get_captcha
        else:
            callback = self.crawl_question
        yield scrapy.Request(self.index_url,
                             callback=callback,
                             errback=self.err_back,
                             dont_filter=True)

    def parse(self, response):
        # not expected to reach here.
        self.logger.warn("not expected to reach url:" + response.url)

    def get_captcha(self, response):
        request = scrapy.Request(self.captcha_url + "?r=" + str(random.random()) + "&type=login",
                                 callback=self.begin_login,
                                 errback=self.err_back,
                                 dont_filter=True)
        request.meta['xsrf'] = response.xpath('//input[@name="_xsrf"]/@value').extract()[0]
        yield request

    def begin_login(self, response):
        if re.match(r"^1\d{10}$", self.account):
            account_type = "phone_num"
        elif re.match(r"^\S+\@\S+\.\S+$", self.account):
            account_type = "email"
        else:
            raise ValueError(u"帐号类型错误")

        form = {account_type: self.account,
                "password": self.password,
                "remember_me": "true",
                '_xsrf': response.meta['xsrf'],
                'captcha': get_captcha_code(response, self.logger)}

        if "email" in form:
            url = self.login_url_email
        elif "phone_num" in form:
            url = self.login_url_phone
        else:
            raise ValueError(u"账号类型错误")

        yield scrapy.FormRequest(url,
                                 formdata=form,
                                 callback=self.check_login,
                                 errback=self.err_back,
                                 dont_filter=True)

    def check_login(self, response):
        # check login succeed before going on
        yield scrapy.Request(self.profile_url,
                             callback=self.crawl_question,
                             errback=self.err_back,
                             meta={
                                 'dont_redirect': True,
                                 'handle_httpstatus_list': [301, 302]
                             },
                             dont_filter=True)

    def crawl_question(self, response):
        if response.status == 301 or response.status == 302:
            self.logger.warn(u"登录失败")
        elif response.status == 200:
            if self.account:
                self.has_login = True
            # crawler questions
            for i in range(settings.QUESTION_START, settings.QUESTION_END, settings.QUESTION_STEP):
                yield scrapy.Request(self.question_url + str(i),
                                     callback=self.parse_question,
                                     meta={
                                         'dont_redirect': True,
                                         'handle_httpstatus_list': [301, 302]
                                     })
        else:
            self.logger.warn(u"网络故障")

    def parse_question(self, response):
        if response.status != 200:
            return

        try:
            question_item = QuestionItem()
            question_item["url_token"] = response.url.split('/')[-1]
            question_item["title"] = \
                response.xpath('//div[@id="zh-question-title"]//span[@class="zm-editable-content"]/text()').extract()[0]

            comment_num = response.xpath('//div[@id="zh-question-meta-wrap"]//a[@name="addcomment"]/text()').re('\d+')
            question_item["comment_num"] = comment_num and int (comment_num[0]) or 0
            question_item["tag_list"] = \
                response.xpath(
                    '//div[contains(@class, "zm-tag-editor-labels")]/a[@class="zm-item-tag"]/text()').extract()
            if self.has_login:
                follow_num = response.xpath('//div[@id="zh-question-side-header-wrap"]'
                                            '//div[contains(@class, "zg-gray-normal")]//strong/text()').re('\d+')
                visitor_num = response.xpath('//div[@class="zu-main-sidebar"]//strong').re('\d+')
            else:
                follow_num = response.xpath('//div[@id="zh-question-side-header-wrap"'
                                            ' and contains(@class, "zg-gray-normal")]/text()').re('\d+')
                visitor_num = False
            question_item["follow_num"] = follow_num and int(follow_num[0]) or 0
            question_item["visitor_num"] = (visitor_num and len(visitor_num) >= 2) and int(visitor_num[-2]) or -1

            answer_num = response.xpath('//h3[@id="zh-question-answer-num"]/@data-num').extract()
            answer_dict = {}
            if answer_num:
                question_item["answer_num"] = int(answer_num[0])
                answer_list = response.xpath(
                    '//div[@id="zh-question-answer-wrap"]/div[contains(@class,"zm-item-answer")]')
                for answer_item in answer_list:
                    author = answer_item.xpath('.//a[@class="author-link"]/@href').extract()
                    key = author and author[0].split('/')[-1] or "unknown"
                    vote = answer_item.xpath(
                        './/div[@class="zm-votebar"]/button[contains(@class,"up")]/span[@class="count"]').re('\d+')
                    value = vote and int(vote[0]) or 0
                    if value > 0:
                        answer_dict[key] = value
            else:
                question_item["answer_num"] = 0
            question_item["answer_list"] = answer_dict
            question_item["answer_top"] = answer_dict and max(answer_dict.values()) or 0

            yield question_item
        except Exception as e:
            self.logger.error(repr(e))

    def err_back(self, failure):
        # log all failures
        self.logger.error(repr(failure))

        # in case you want to do something special for some errors,
        # you may need the failure's type:

        if failure.check(HttpError):
            # these exceptions come from HttpError spider middleware
            # you can get the non-200 response
            response = failure.value.response
            self.logger.error('HttpError on %s', response.url)

        elif failure.check(DNSLookupError):
            # this is the original request
            request = failure.request
            self.logger.error('DNSLookupError on %s', request.url)

        elif failure.check(TimeoutError, TCPTimedOutError):
            request = failure.request
            self.logger.error('TimeoutError on %s', request.url)
