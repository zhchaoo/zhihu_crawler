Zhihu Questions Crawler
====================

Usage
-----
```
pip install scrapy
```
* Start crawl:
```
scrapy crawl question -o result.json
```

Settings
--------
You can set start question token and end question token in settings.
You can set login info in settings.

TODO
----
* crawl log of question when login.
* noly test on linux, if has some issue when running on windows, try not login and set TERMINAL False.
