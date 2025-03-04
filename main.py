import os
import random
import time
import functools
import sys
import argparse

from loguru import logger
from playwright.sync_api import sync_playwright
from tabulate import tabulate


def retry_decorator(retries=3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == retries - 1:  # Last attempt
                        logger.error(f"函数 {func.__name__} 最终执行失败: {str(e)}")
                    logger.warning(f"函数 {func.__name__} 第 {attempt + 1}/{retries} 次尝试失败: {str(e)}")
                    time.sleep(1)
            return None
        return wrapper
    return decorator


# Parse command-line arguments
parser = argparse.ArgumentParser(description="Linux Do Browser Automation")
parser.add_argument("--username", required=True, help="Your username for login")
parser.add_argument("--password", required=True, help="Your password for login")
args = parser.parse_args()

USERNAME = args.username
PASSWORD = args.password

HOME_URL = "https://linux.do/"


class LinuxDoBrowser:
    def __init__(self) -> None:
        self.pw = sync_playwright().start()
        self.browser = self.pw.firefox.launch(headless=True, timeout=30000)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.goto(HOME_URL)

    def login(self):
        logger.info("开始登录")
        self.page.click(".login-button .d-button-label")
        time.sleep(2)
        self.page.fill("#login-account-name", USERNAME)
        time.sleep(2)
        self.page.fill("#login-account-password", PASSWORD)
        time.sleep(2)
        self.page.click("#login-button")
        time.sleep(10)  # Wait for login to complete
        user_ele = self.page.query_selector("#current-user")
        if not user_ele:
            logger.error("登录失败")
            return False
        else:
            logger.info("登录成功")
            return True

    def click_topic(self):
        topic_list = self.page.query_selector_all("#list-area .title")
        logger.info(f"发现 {len(topic_list)} 个主题帖")
        for topic in topic_list:
            self.click_one_topic(topic.get_attribute("href"))

    @retry_decorator()
    def click_one_topic(self, topic_url):
        page = self.context.new_page()
        page.goto(HOME_URL + topic_url)
        if random.random() < 0.3:  # 30% chance to like
            self.click_like(page)
        self.browse_post(page)
        page.close()

    def browse_post(self, page):
        prev_url = None
        # Scroll up to 10 times
        for _ in range(10):
            # Random scroll distance
            scroll_distance = random.randint(550, 650)  # Scroll 550-650 pixels
            logger.info(f"向下滚动 {scroll_distance} 像素...")
            page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            logger.info(f"已加载页面: {page.url}")

            if random.random() < 0.03:  # 3% chance to exit early
                logger.success("随机退出浏览")
                break

            # Check if at bottom
            at_bottom = page.evaluate("window.scrollY + window.innerHeight >= document.body.scrollHeight")
            current_url = page.url
            if current_url != prev_url:
                prev_url = current_url
            elif at_bottom and prev_url == current_url:
                logger.success("已到达页面底部，退出浏览")
                break

            # Random wait
            wait_time = random.uniform(2, 4)  # Wait 2-4 seconds
            logger.info(f"等待 {wait_time:.2f} 秒...")
            time.sleep(wait_time)

    def click_like(self, page):
        try:
            # Locate unliked "like" button (assuming Discourse forum structure)
            like_button = page.locator('.discourse-reactions-reaction-button:not(.has-reacted)')
            if like_button.count() > 0:
                like_button.first.click()
                logger.info("成功点赞一个帖子")
            else:
                logger.info("没有可点赞的按钮")
        except Exception as e:
            logger.error(f"点赞失败: {str(e)}")

    def print_connect_info(self):
        # Print basic connection info and cleanup
        logger.info("浏览器运行结束，连接信息：")
        logger.info(f"当前页面: {self.page.url}")
        self.browser.close()
        self.pw.stop()

    def run(self):
        if not self.login():
            logger.error("登录失败，程序终止")
            sys.exit(1)  # Exit with error code
        self.click_topic()
        self.print_connect_info()


if __name__ == "__main__":
    browser = LinuxDoBrowser()
    browser.run()
