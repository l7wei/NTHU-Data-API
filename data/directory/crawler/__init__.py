import os

from loguru import logger

from crawler import get_all_dept_details, get_dept_departments
from sort_data import combine_file, combine_json, combine_contact


def crawl_all():
    if not os.path.isdir("dept"):
        os.mkdir("dept")

    if not os.path.isdir("combined"):
        os.mkdir("combined")

    # 1. 爬取所有系所資料
    logger.info("開始爬取所有系所資料")
    # get_all_dept_details()

    # 2. 從系所資料中取得子系所資料並爬取
    logger.info("開始爬取所有子系所資料")
    # get_dept_departments()

    # 3. 合併父系所和子系所的資料
    logger.info("開始合併所有系所資料")
    combine_file()

    # 4. 合併所有的系所資料成一個檔案
    logger.info("開始合併所有系所資料")
    combine_json()

    # 5. 合併聯絡資訊
    logger.info("開始合併聯絡資訊")
    combine_contact()

    logger.info("所有爬蟲工作完成!")


if __name__ == "__main__":
    crawl_all()
