import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from dateutil.parser import parse

from src.utils import cached_requests


def replace_numbers_in_url(url: str, new_number: str) -> str:
    # 使用正則表達式替換 -1.php 為 -{new_number}.php
    new_url = re.sub(r"-(1)\.php", f"-{new_number}.php", url)
    return new_url


def process_date(mdate):
    if mdate is None:
        return None
    mdate = mdate.text.strip()
    return mdate


def process_timestamp(date):
    try:
        date = parse(date)
        timestamp = int(date.timestamp())
    except (ValueError, TypeError):
        # 如果日期不能被解析，返回 None
        timestamp = None
    return timestamp


def process_link(url_dom, parsed_url):
    if url_dom is not None:
        title = str(url_dom.get("title"))
        href = str(url_dom.get("href"))
        # 如果 href 是相對路徑，則轉換成絕對路徑
        if href.startswith("//"):
            href = f"{parsed_url.scheme}:{href}"
        elif href.startswith("/"):
            href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
    else:
        title = None
        href = None
    return title, href


def get_announcement(url: str, maxpage: int = 1) -> list:
    page_list = (
        [url] + [replace_numbers_in_url(url, str(i)) for i in range(2, maxpage + 1)]
        if maxpage > 1
        else [url]
    )
    data = []
    for url in page_list:
        response, _using_cache = cached_requests.get(url, update=True, auto_headers=True)
        parsed_url = urlparse(url)
        soup = BeautifulSoup(response, "html.parser")
        recruitments = soup.select("#pageptlist .listBS")
        for item in recruitments:
            mdate = item.select_one(".mdate")
            date = process_date(mdate)
            timestamp = process_timestamp(date)
            url_dom = item.select_one("a")
            title, href = process_link(url_dom, parsed_url)
            data.append(
                {
                    "title": title,
                    "link": href,
                    "date": date,
                    "unix_timestamp": timestamp,
                }
            )
    return data
