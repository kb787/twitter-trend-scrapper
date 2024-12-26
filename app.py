# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.options import Options
# from selenium.common.exceptions import TimeoutException, WebDriverException
# from datetime import datetime
# import undetected_chromedriver as uc
# import uuid
# import requests
# import logging
# import time
# import os
# from dotenv import load_dotenv
# from pymongo import MongoClient
# from flask import Flask, render_template, jsonify

# load_dotenv()
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
# )
# logger = logging.getLogger(__name__)

# app = Flask(__name__)
# client = MongoClient(os.getenv("MONGODB_URI"))
# db = client.twitter_trends
# collection = db.trends


# class TwitterScraper:
#     def __init__(self):
#         self.twitter_username = os.getenv("TWITTER_USERNAME")
#         self.twitter_password = os.getenv("TWITTER_PASSWORD")
#         self.setup_logging()

#     def setup_logging(self):
#         for dir_name in ["logs", "screenshots"]:
#             if not os.path.exists(dir_name):
#                 os.makedirs(dir_name)
#         self.screenshot_dir = "screenshots"

#     def setup_driver(self):
#         try:
#             options = uc.ChromeOptions()
#             options.add_argument("--no-sandbox")
#             options.add_argument("--disable-dev-shm-usage")
#             options.add_argument("--disable-gpu")
#             options.add_argument("--window-size=1920,1080")
#             options.add_argument("--start-maximized")
#             options.add_argument("--disable-blink-features=AutomationControlled")

#             driver = uc.Chrome(options=options)
#             driver.execute_script(
#                 "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
#             )
#             return driver
#         except Exception as e:
#             logger.error(f"Driver setup failed: {str(e)}")
#             raise

#     def take_error_screenshot(self, driver, error_type):
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         screenshot_path = os.path.join(
#             self.screenshot_dir, f"{error_type}_{timestamp}.png"
#         )
#         driver.save_screenshot(screenshot_path)
#         logger.info(f"Screenshot saved: {screenshot_path}")

#     def wait_and_find_element(self, driver, by, value, timeout=20, error_msg=None):
#         try:
#             element = WebDriverWait(driver, timeout).until(
#                 EC.presence_of_element_located((by, value))
#             )
#             time.sleep(1)
#             return element
#         except TimeoutException:
#             self.take_error_screenshot(driver, f"element_not_found_{value}")
#             raise TimeoutException(error_msg or f"Element not found: {value}")

#     def login_twitter(self, driver):
#         try:
#             logger.info("Attempting Twitter login")
#             driver.get("https://twitter.com/login")
#             time.sleep(5)

#             username_field = self.wait_and_find_element(
#                 driver, By.NAME, "text", error_msg="Username field not found"
#             )
#             username_field.send_keys(self.twitter_username)
#             time.sleep(2)

#             next_button = self.wait_and_find_element(
#                 driver,
#                 By.XPATH,
#                 "//span[text()='Next']",
#                 error_msg="Next button not found",
#             )
#             next_button.click()
#             time.sleep(3)

#             password_field = self.wait_and_find_element(
#                 driver, By.NAME, "password", error_msg="Password field not found"
#             )
#             password_field.send_keys(self.twitter_password)
#             time.sleep(2)

#             login_button = self.wait_and_find_element(
#                 driver,
#                 By.XPATH,
#                 "//span[text()='Log in']",
#                 error_msg="Login button not found",
#             )
#             login_button.click()
#             time.sleep(10)

#             logger.info("Successfully logged into Twitter")

#         except Exception as e:
#             self.take_error_screenshot(driver, "login_error")
#             logger.error(f"Login failed: {str(e)}")
#             raise

#     def verify_login_success(self, driver):
#         try:
#             self.wait_and_find_element(
#                 driver,
#                 By.XPATH,
#                 "//a[@aria-label='Home']",
#                 timeout=10,
#                 error_msg="Home link not found - login might have failed",
#             )
#             return True
#         except TimeoutException:
#             return False

#     def get_trending_topics(self):
#         driver = None
#         try:
#             driver = self.setup_driver()
#             self.login_twitter(driver)

#             if not self.verify_login_success(driver):
#                 raise Exception("Login verification failed")

#             # Navigate directly to trends page
#             driver.get("https://x.com/explore")
#             time.sleep(5)

#             # Wait for trends to load and get all trend elements
#             trends = self.wait_and_find_element(
#                 driver,
#                 By.XPATH,
#                 "//div[@data-testid='trend']",
#                 timeout=20,
#                 error_msg="Trends not found",
#             ).find_elements(By.XPATH, ".//span[contains(@class, 'css-901oao')]")

#             # Extract trend texts
#             trend_texts = []
#             for trend in trends[:10]:  # Get first 10 trends
#                 try:
#                     trend_text = trend.text.strip()
#                     if trend_text and not trend_text.startswith(
#                         ("Trending", "View", "#")
#                     ):
#                         trend_texts.append(trend_text)
#                 except Exception as e:
#                     logger.warning(f"Error extracting trend text: {str(e)}")

#             # Take first 5 valid trends
#             trend_texts = trend_texts[:5]
#             trend_texts.extend([None] * (5 - len(trend_texts)))

#             document = {
#                 "_id": str(uuid.uuid4()),
#                 "trend1": trend_texts[0],
#                 "trend2": trend_texts[1],
#                 "trend3": trend_texts[2],
#                 "trend4": trend_texts[3],
#                 "trend5": trend_texts[4],
#                 "timestamp": datetime.now(),
#                 "ip_address": requests.get("https://api.ipify.org").text,
#             }

#             collection.insert_one(document)
#             logger.info("Successfully saved trending topics")
#             return document

#         except Exception as e:
#             if driver:
#                 self.take_error_screenshot(driver, "scraping_error")
#             logger.error(f"Error getting trending topics: {str(e)}")
#             raise

#         finally:
#             if driver:
#                 driver.quit()


# @app.route("/")
# def home():
#     return render_template("index.html")


# @app.route("/scrape", methods=["POST"])
# def scrape():
#     try:
#         scraper = TwitterScraper()
#         result = scraper.get_trending_topics()
#         return jsonify(
#             {
#                 "status": "success",
#                 "data": {
#                     "id": result["_id"],
#                     "trends": [
#                         result["trend1"],
#                         result["trend2"],
#                         result["trend3"],
#                         result["trend4"],
#                         result["trend5"],
#                     ],
#                     "timestamp": result["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
#                     "ip": result["ip_address"],
#                 },
#             }
#         )
#     except Exception as e:
#         logger.error(f"Scraping endpoint error: {str(e)}")
#         return jsonify({"status": "error", "message": str(e)}), 500


# if __name__ == "__main__":
#     app.run(debug=True)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from datetime import datetime
import undetected_chromedriver as uc
import uuid
import requests
import logging
import time
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from flask import Flask, render_template, jsonify

load_dotenv()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
client = MongoClient(os.getenv("MONGODB_URI"))
db = client.twitter_trends
collection = db.trends


class TwitterScraper:
    def __init__(self):
        self.twitter_username = os.getenv("TWITTER_USERNAME")
        self.twitter_password = os.getenv("TWITTER_PASSWORD")
        self.twitter_email = os.getenv("TWITTER_EMAIL")
        self.setup_logging()

    def setup_logging(self):
        for dir_name in ["logs", "screenshots"]:
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
        self.screenshot_dir = "screenshots"

    def setup_driver(self):
        try:
            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")

            driver = uc.Chrome(options=options)
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            return driver
        except Exception as e:
            logger.error(f"Driver setup failed: {str(e)}")
            raise

    def take_error_screenshot(self, driver, error_type):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(
            self.screenshot_dir, f"{error_type}_{timestamp}.png"
        )
        driver.save_screenshot(screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")

    def wait_and_find_element(self, driver, by, value, timeout=20, error_msg=None):
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            time.sleep(1)
            return element
        except TimeoutException:
            self.take_error_screenshot(driver, f"element_not_found_{value}")
            raise TimeoutException(error_msg or f"Element not found: {value}")

    def login_twitter(self, driver):
        try:
            logger.info("Attempting Twitter login")
            driver.get("https://twitter.com/login")
            time.sleep(5)

            username_field = self.wait_and_find_element(
                driver, By.NAME, "text", error_msg="Username field not found"
            )
            username_field.send_keys(self.twitter_username)
            time.sleep(2)

            next_button = self.wait_and_find_element(
                driver,
                By.XPATH,
                "//span[text()='Next']",
                error_msg="Next button not found",
            )
            next_button.click()
            time.sleep(3)

            # Handle email verification if required
            try:
                email_field = self.wait_and_find_element(
                    driver, By.NAME, "text", timeout=5
                )
                if email_field:
                    email_field.send_keys(self.twitter_email)
                    next_button = self.wait_and_find_element(
                        driver,
                        By.XPATH,
                        "//span[text()='Next']",
                        error_msg="Next button not found after email",
                    )
                    next_button.click()
                    time.sleep(3)
            except TimeoutException:
                logger.info("No email verification required")

            password_field = self.wait_and_find_element(
                driver, By.NAME, "password", error_msg="Password field not found"
            )
            password_field.send_keys(self.twitter_password)
            time.sleep(2)

            login_button = self.wait_and_find_element(
                driver,
                By.XPATH,
                "//span[text()='Log in']",
                error_msg="Login button not found",
            )
            login_button.click()
            time.sleep(10)

            logger.info("Successfully logged into Twitter")

        except Exception as e:
            self.take_error_screenshot(driver, "login_error")
            logger.error(f"Login failed: {str(e)}")
            raise

    def verify_login_success(self, driver):
        try:
            self.wait_and_find_element(
                driver,
                By.XPATH,
                "//a[@aria-label='Home']",
                timeout=10,
                error_msg="Home link not found - login might have failed",
            )
            return True
        except TimeoutException:
            return False

    def get_trending_topics(self):
        driver = None
        try:
            driver = self.setup_driver()
            self.login_twitter(driver)

            if not self.verify_login_success(driver):
                raise Exception("Login verification failed")

            driver.get("https://x.com/explore")
            time.sleep(5)

            trends = self.wait_and_find_element(
                driver,
                By.XPATH,
                "//div[@data-testid='trend']",
                timeout=20,
                error_msg="Trends not found",
            ).find_elements(By.XPATH, ".//span[contains(@class, 'css-901oao')]")

            trend_texts = []
            for trend in trends[:10]:
                try:
                    trend_text = trend.text.strip()
                    if trend_text and not trend_text.startswith(
                        ("Trending", "View", "#")
                    ):
                        trend_texts.append(trend_text)
                except Exception as e:
                    logger.warning(f"Error extracting trend text: {str(e)}")

            trend_texts = trend_texts[:5]
            trend_texts.extend([None] * (5 - len(trend_texts)))

            document = {
                "_id": str(uuid.uuid4()),
                "trend1": trend_texts[0],
                "trend2": trend_texts[1],
                "trend3": trend_texts[2],
                "trend4": trend_texts[3],
                "trend5": trend_texts[4],
                "timestamp": datetime.now(),
                "ip_address": requests.get("https://api.ipify.org").text,
            }

            collection.insert_one(document)
            logger.info("Successfully saved trending topics")
            return document

        except Exception as e:
            if driver:
                self.take_error_screenshot(driver, "scraping_error")
            logger.error(f"Error getting trending topics: {str(e)}")
            raise

        finally:
            if driver:
                driver.quit()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/scrape", methods=["POST"])
def scrape():
    try:
        scraper = TwitterScraper()
        result = scraper.get_trending_topics()
        return jsonify(
            {
                "status": "success",
                "data": {
                    "id": result["_id"],
                    "trends": [
                        result["trend1"],
                        result["trend2"],
                        result["trend3"],
                        result["trend4"],
                        result["trend5"],
                    ],
                    "timestamp": result["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                    "ip": result["ip_address"],
                },
            }
        )
    except Exception as e:
        logger.error(f"Scraping endpoint error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
