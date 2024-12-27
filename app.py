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
import json
import traceback  # Added for detailed error tracking
from dotenv import load_dotenv
from pymongo import MongoClient
from flask import Flask, render_template, jsonify

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),  # Added file handler
        logging.StreamHandler(),
    ],
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
        self.chrome_path = os.getenv("CHROME_BINARY_PATH")
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
            options.add_argument("--headless")  # Added for headless mode
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")  # Added
            options.add_argument("--remote-debugging-port=9222")  # Added for debugging
            options.binary_location = self.chrome_path

            # Additional logging for debugging
            logger.info("Setting up Chrome driver with options")
            for arg in options.arguments:
                logger.info(f"Chrome option: {arg}")

            driver = uc.Chrome(options=options)
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            logger.info("Chrome driver setup successful")
            return driver
        except Exception as e:
            logger.error(f"Driver setup failed: {str(e)}")
            logger.error(f"Error traceback: {traceback.format_exc()}")
            raise

    def take_error_screenshot(self, driver, error_type):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(
                self.screenshot_dir, f"{error_type}_{timestamp}.png"
            )
            driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
        except Exception as e:
            logger.error(f"Failed to take screenshot: {str(e)}")

    def wait_and_find_element(self, driver, by, value, timeout=20, error_msg=None):
        try:
            logger.info(f"Waiting for element: {by}={value}")
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            time.sleep(1)
            logger.info(f"Element found: {by}={value}")
            return element
        except TimeoutException:
            logger.error(f"Element not found: {by}={value}")
            self.take_error_screenshot(driver, f"element_not_found_{value}")
            raise TimeoutException(error_msg or f"Element not found: {value}")

    def login_twitter(self, driver):
        try:
            logger.info("Attempting Twitter login")
            driver.get("https://twitter.com/login")
            time.sleep(5)

            # Take screenshot of login page for debugging
            self.take_error_screenshot(driver, "login_page")

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
            logger.error(f"Login failed: {str(e)}")
            logger.error(f"Error traceback: {traceback.format_exc()}")
            self.take_error_screenshot(driver, "login_error")
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
            logger.info("Login verification successful")
            return True
        except TimeoutException:
            logger.error("Login verification failed")
            self.take_error_screenshot(driver, "login_verification_failed")
            return False

    def get_trending_topics(self):
        driver = None
        try:
            driver = self.setup_driver()
            self.login_twitter(driver)

            if not self.verify_login_success(driver):
                raise Exception("Login verification failed")

            logger.info("Navigating to Twitter explore page")
            driver.get("https://x.com/explore")
            time.sleep(5)

            trend_data = []
            retries = 3
            while len(trend_data) < 5 and retries > 0:
                try:
                    logger.info(f"Attempting to fetch trends (retry {4-retries}/3)")
                    trend_containers = driver.find_elements(
                        By.XPATH, "//div[@data-testid='cellInnerDiv']"
                    )
                    logger.info(f"Found {len(trend_containers)} trend containers")

                    for container in trend_containers:
                        if len(trend_data) >= 5:
                            break

                        try:
                            trend_text_element = container.find_element(
                                By.XPATH, ".//span[@dir='ltr']"
                            )
                            trend_text = trend_text_element.text.strip()

                            try:
                                additional_info_element = container.find_element(
                                    By.XPATH, ".//div[@dir='auto']"
                                )
                                additional_info = additional_info_element.text.strip()
                            except:
                                additional_info = "N/A"

                            if trend_text not in [
                                trend["trend_text"] for trend in trend_data
                            ]:
                                trend_data.append(
                                    {
                                        "trend_text": trend_text,
                                        "additional_info": additional_info,
                                        "timestamp": datetime.now().strftime(
                                            "%Y-%m-%d %H:%M:%S"
                                        ),
                                    }
                                )
                                logger.info(f"Added trend: {trend_text}")
                        except Exception as e:
                            logger.warning(
                                f"Error processing trend container: {str(e)}"
                            )

                    if len(trend_data) < 5:
                        logger.info("Fewer than 5 trends found, reloading page")
                        driver.refresh()
                        time.sleep(5)

                    retries -= 1

                except Exception as e:
                    logger.error(f"Error fetching trends: {str(e)}")
                    logger.error(f"Error traceback: {traceback.format_exc()}")
                    raise

            if len(trend_data) < 5:
                raise Exception("Failed to extract 5 trends after retries")

            ip_address = None
            try:
                ip_address = requests.get("https://api.ipify.org").text
            except Exception as e:
                logger.warning(f"Failed to retrieve IP address: {str(e)}")

            document = {
                "_id": str(uuid.uuid4()),
                "trends": trend_data[:5],
                "timestamp": datetime.now(),
                "ip_address": ip_address or "IP unavailable",
            }

            collection.insert_one(document)
            logger.info("Successfully saved trending topics")
            return document

        except Exception as e:
            if driver:
                self.take_error_screenshot(driver, "scraping_error")
            logger.error(f"Error getting trending topics: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error traceback: {traceback.format_exc()}")
            raise

        finally:
            if driver:
                driver.quit()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/scrape", methods=["POST", "GET"])
def scrape():
    try:
        logger.info("Starting scraping process")
        scraper = TwitterScraper()
        result = scraper.get_trending_topics()

        trend_details = []
        for trend in result["trends"]:
            trend_details.append(
                {
                    "trend_text": trend["trend_text"],
                    "additional_info": trend["additional_info"],
                }
            )

        response_data = {
            "status": "success",
            "data": {
                "id": str(result["_id"]),
                "trends": trend_details,
                "timestamp": result["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                "ip": str(result["ip_address"]),
            },
        }

        logger.info("Scraping completed successfully")
        return app.response_class(
            response=json.dumps(response_data, ensure_ascii=False),
            status=200,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Error scraping Twitter: {str(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
