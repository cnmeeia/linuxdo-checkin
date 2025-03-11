import os
import random
import time
import functools
import sys

from loguru import logger
from playwright.sync_api import sync_playwright
from tabulate import tabulate
from dotenv import load_dotenv

load_dotenv()

def retry_decorator(retries=3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == retries - 1:
                        logger.error(f"函数 {func.__name__} 最终执行失败: {str(e)}")
                    logger.warning(f"函数 {func.__name__} 第 {attempt + 1}/{retries} 次尝试失败: {str(e)}")
                    time.sleep(1)
            return None
        return wrapper
    return decorator

USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")

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
        try:
            self.page.wait_for_selector(".login-button .d-button-label", state="visible", timeout=60000)
            self.page.click(".login-button .d-button-label")
        except Exception as e:
            logger.warning(f"普通点击失败，尝试 JavaScript 方式: {e}")
            self.page.evaluate("document.querySelector('.login-button .d-button-label').click()")

        try:
            self.page.wait_for_selector("#login-account-name", state="visible", timeout=10000)
            self.page.fill("#login-account-name", USERNAME)
            self.page.fill("#login-account-password", PASSWORD)
            self.page.click("#login-button")
            self.page.wait_for_selector("#current-user", state="visible", timeout=20000)
            logger.info("登录成功")
            return True
        except Exception as e:
            logger.error(f"登录失败: {e}")
            self.page.screenshot(path="login_failed.png")
            return False

    def click_topic(self):
        topic_list = self.page.query_selector_all("#list-area .title")
        logger.info(f"发现 {len(topic_list)} 个主题帖")
        for topic in topic_list:
            self.click_one_topic(topic.get_attribute("href"))

    @retry_decorator()
    def click_one_topic(self, topic_url):
        page = self.context.new_page()
        page.goto(HOME_URL + topic_url)
        if random.random() < 0.3:
            self.click_like(page)
        self.browse_post(page)
        page.close()

    def browse_post(self, page):
        prev_url = None
        for _ in range(10):
            scroll_distance = random.randint(550, 650)
            logger.info(f"向下滚动 {scroll_distance} 像素...")
            page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            logger.info(f"已加载页面: {page.url}")
            try:
                page.wait_for_function("document.readyState === 'complete'", timeout=5000)
            except:
                logger.warning("页面加载超时或失败。")
            if random.random() < 0.03:
                logger.success("随机退出浏览")
                break
            at_bottom = page.evaluate("window.scrollY + window.innerHeight >= document.body.scrollHeight")
            current_url = page.url
            if current_url != prev_url:
                prev_url = current_url
            elif at_bottom and prev_url == current_url:
                logger.success("已到达页面底部，退出浏览")
                break
            wait_time = random.uniform(2, 4)
            logger.info(f"等待 {wait_time:.2f} 秒...")
            time.sleep(wait_time)

    def run(self):
        if not self.login():
            logger.error("登录失败，程序终止")
            sys.exit(1)
        self.click_topic()
        self.print_connect_info()

    def click_like(self, page):
        try:
            like_button = page.locator('.discourse-reactions-reaction-button[title="点赞此帖子"]').first
            if like_button:
                logger.info("找到未点赞的帖子，准备点赞")
                like_button.click()
                logger.info("点赞成功")
                time.sleep(random.uniform(1, 2))
            else:
                logger.info("帖子可能已经点过赞了")
        except Exception as e:
            logger.error(f"点赞失败: {str(e)}")

    def print_connect_info(self):
        logger.info("获取连接信息")
        page = self.context.new_page()
        page.goto("https://connect.linux.do/")
        rows = page.query_selector_all("table tr")

        info = []

        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) >= 3:
                project = cells[0].text_content().strip()
                current = cells[1].text_content().strip()
                requirement = cells[2].text_content().strip()
                info.append([project, current, requirement])

        print("--------------Connect Info-----------------")
        print(tabulate(info, headers=["项目", "当前", "要求"], tablefmt="pretty"))

        page.close()

if __name__ == "__main__":
    if not USERNAME or not PASSWORD:
        logger.error("请设置 USERNAME 和 PASSWORD 环境变量")
        sys.exit(1)
    l = LinuxDoBrowser()
    l.run()
