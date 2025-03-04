import os
import random
import time

from loguru import logger
from playwright.sync_api import sync_playwright
from tabulate import tabulate

# 移除環境變數，避免與無頭模式衝突
os.environ.pop("DISPLAY", None)
os.environ.pop("DYLD_LIBRARY_PATH", None)

# 從環境變數取得使用者名稱和密碼
USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")

# 定義網站 URL
HOME_URL = "https://linux.do/"
CONNECT_URL = "https://connect.linux.do/"


class LinuxDoBrowser:
    def __init__(self) -> None:
        # 初始化 Playwright 和瀏覽器
        self.pw = sync_playwright().start()
        self.browser = self.pw.firefox.launch(headless=True, timeout=30000)  # 設定超時時間
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.goto(HOME_URL)

    def login(self):
        # 登入功能
        logger.info("Login")
        try:
            self.page.click(".login-button .d-button-label")
            self.page.fill("#login-account-name", USERNAME)
            self.page.fill("#login-account-password", PASSWORD)
            self.page.click("#login-button")
            self.page.wait_for_selector("#current-user", timeout=10000) #等待登陸成功標誌
            logger.info("Login success")
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def click_topic(self):
        # 點擊主題列表
        topic_list = self.page.query_selector_all("#list-area .title")
        logger.info(f"Click {len(topic_list)} topics")
        for topic in topic_list:
            href = topic.get_attribute("href")
            if href:
                logger.info("Click topic: " + href)
                page = self.context.new_page()
                full_url = HOME_URL + href
                full_url = full_url.replace("//t", "/t") #修正url雙斜線問題
                retries = 3
                for attempt in range(retries):
                    try:
                        page.goto(full_url, timeout=60000) # 增加超時時間
                        break
                    except playwright._impl._errors.TimeoutError as e:
                        logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                        if attempt < retries - 1:
                            time.sleep(5)
                        else:
                            logger.error(f"Failed to load {full_url} after {retries} attempts.")
                            page.close()
                            continue
                if random.random() < 0.3:
                    self.click_like(page)
                self.browse_post(page)
                page.close()
            else:
                logger.warning("Topic href is None, skipping.")

    def browse_post(self, page):
        # 瀏覽貼文並隨機滾動
        prev_url = None
        for _ in range(10):
            scroll_distance = random.randint(550, 650)
            logger.info(f"Scrolling down by {scroll_distance} pixels...")
            page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            logger.info(f"Loaded: {page.url}")

            if random.random() < 0.03:
                logger.success("Randomly exit")
                break

            at_bottom = page.evaluate(
                "window.scrollY + window.innerHeight >= document.body.scrollHeight"
            )
            current_url = page.url
            if current_url != prev_url:
                prev_url = current_url
            elif at_bottom and prev_url == current_url:
                logger.success("Reached the bottom of the page. Exiting.")
                break

            wait_time = random.uniform(2, 4)
            logger.info(f"Waiting for {wait_time:.2f} seconds...")
            time.sleep(wait_time)

    def run(self):
        # 執行程式的主要流程
        if not self.login():
            return
        self.click_topic()
        self.print_connect_info()

    def click_like(self, page):
        # 點擊點讚按鈕
        try:
            like_button = page.locator(
                '.discourse-reactions-reaction-button[title="点赞此帖子"]'
            ).first
            if like_button.is_visible():
                logger.info("找到未点赞的帖子，准备点赞")
                like_button.click()
                logger.info("点赞成功")
                time.sleep(random.uniform(1, 2))
            else:
                logger.info("帖子可能已经点过赞了")
        except Exception as e:
            logger.error(f"点赞失败: {str(e)}")

    def print_connect_info(self):
        # 顯示連接資訊
        logger.info("Print connect info")
        page = self.context.new_page()
        page.goto(CONNECT_URL)
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

    def __del__(self):
        # 釋放資源
        self.context.close()
        self.browser.close()
        self.pw.stop()


if __name__ == "__main__":
    if not USERNAME or not PASSWORD:
        print("Please set USERNAME and PASSWORD")
        exit(1)
    l = LinuxDoBrowser()
    l.run()
