import os
import csv
import time
import logging
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


class ForelleScraper:
    def __init__(self, base_url: str = "https://www.forelle.com"):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        self.service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=self.service, options=chrome_options)

        self.base_url = base_url
        self.product_urls = set()
        self.page_count = 0
        self.max_retries = 3

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s: %(message)s',
            handlers=[
                logging.FileHandler('forelle_scraping.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _safe_find_element(self, by, selector, context=None, timeout=20):
        try:
            if context:
                return WebDriverWait(context, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )
            else:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )
        except Exception as e:
            self.logger.error(f"Error while finding element {selector}: {e}")
            return None

    def scrape_category(self, category_url: str):
        try:
            self.page_count = 0
            current_url = category_url

            while True:
                self.driver.get(current_url)
                self.page_count += 1
                self.logger.info(f"Scraping Page {self.page_count}: {current_url}")

                try:
                    WebDriverWait(self.driver, 30).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.product"))
                    )
                except TimeoutException:
                    self.logger.warning("No products found on this page")
                    break

                self._extract_product_details()

                next_button = None
                try:
                    next_button = self.driver.find_elements(
                        By.XPATH,
                        "//button[contains(@class, 'page-btn') and contains(text(), 'Next') and contains(@class, 'is-disabled')]"
                    )

                    if next_button:
                        self.logger.info("The 'Next' button is disabled. Pagination ends.")
                        break

                    next_button = self.driver.find_elements(
                        By.XPATH, "//a[contains(@class, 'page-btn') and contains(text(), 'Next')]"
                    )

                    if next_button:
                        next_url = next_button[0].get_attribute('href')

                        if next_url and next_url != current_url:
                            current_url = next_url
                            self.logger.info(f"Proceeding to next page: {current_url}")
                        else:
                            self.logger.info("No next page. Pagination ends.")
                            break
                    else:
                        self.logger.info("No 'Next' button. Pagination ends.")
                        break
                except Exception as e:
                    self.logger.error(f"Error during pagination: {e}")
                    break

                time.sleep(2)

            self.logger.info(
                f"Category scraping completed. Total pages: {self.page_count}, Total URLs: {len(self.product_urls)}")

        except Exception as e:
            self.logger.error(f"Global error while scraping category {category_url}: {e}")

    def _extract_product_details(self):
        try:
            product_articles = WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.product"))
            )

            self.logger.info(f"Number of products on the page: {len(product_articles)}")

            for index, article in enumerate(product_articles, 1):
                try:
                    product_url = self.driver.execute_script("""
                        var link = arguments[0].querySelector('a.product-title, a.product-image');
                        return link ? link.href : null;
                    """, article)

                    if product_url:
                        self.product_urls.add(product_url)
                        self.logger.info(f"Product {index}: URL captured - {product_url}")

                except Exception as e:
                    self.logger.error(f"Error while extracting product {index}: {e}")

        except Exception as e:
            self.logger.error(f"Global error while extracting products: {e}")

    def save_urls_to_csv(self, filename: str = 'forelle_product_urls.csv'):
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Product URL'])

                for url_index, url in enumerate(self.product_urls, 1):
                    writer.writerow([url])
                    if url_index % 50 == 0:
                        self.logger.info(f"Written {url_index} URLs to CSV file")

            self.logger.info(f"Saving completed. Total unique URLs: {len(self.product_urls)}")
            print(f"Saved {len(self.product_urls)} unique URLs to {filename}")

        except Exception as e:
            self.logger.error(f"Error while saving URLs: {e}")

    def run(self, category_urls: List[str]):
        try:
            for category_url in category_urls:
                self.logger.info(f"Starting scraping for category: {category_url}")
                self.scrape_category(category_url)

            self.save_urls_to_csv()

        except Exception as e:
            self.logger.error(f"Scraping process failed: {e}")

        finally:
            self.driver.quit()


def main():
    category_urls = [
        "https://www.forelle.com/en_US/gloves-lh-left-hand-catch/263/",
        "https://www.forelle.com/en_US/balls/272/",
        "https://www.forelle.com/en_US/batting-gloves/383/",
        "https://www.forelle.com/en_US/field-equipment/253/",
        "https://www.forelle.com/en_US/training-equipment/265/",
        "https://www.forelle.com/en_US/bats/269/",
        "https://www.forelle.com/en_US/clothing-apparel/241/",
        "https://www.forelle.com/en_US/catcher-equipment/290/",
        "https://www.forelle.com/en_US/accessories/251/",
        "https://www.forelle.com/en_US/umpire-equipment/247/",
        "https://www.forelle.com/en_US/flag-football/1535/",
        "https://www.forelle.com/en_US/shoes-us-size/339/",
        "https://www.forelle.com/en_US/helmets/288/",
        "https://www.forelle.com/en_US/bags/307/",
        "https://www.forelle.com/en_US/protective-gear/249/",
        "https://www.forelle.com/en_US/rawlings-luxury-leather-goods/369/",
        "https://www.forelle.com/en_US/american-football-helmets/259/",
        "https://www.forelle.com/en_US/gloves/257/",
        "https://www.forelle.com/en_US/training-equipment/319/",
        "https://www.forelle.com/en_US/field-equipment/355/",
        "https://www.forelle.com/en_US/protective-gear/336/",
        "https://www.forelle.com/en_US/shoulder-pads/267/",
        "https://www.forelle.com/en_US/balls/300/",
        "https://www.forelle.com/en_US/accessories/243/",
        "https://www.forelle.com/en_US/official-s/392/",
        "https://www.forelle.com/en_US/flag-football/1535/",
        "https://www.forelle.com/en_US/shoes-us-size/282/",
        "https://www.forelle.com/en_US/clothing-apparel/261/",
        "https://www.forelle.com/en_US/bags/361/",
        "https://www.forelle.com/en_US/protection-medical/245/",
        "https://www.forelle.com/en_US/basketball/329/",
        "https://www.forelle.com/en_US/handball/498/",
        "https://www.forelle.com/en_US/soccer/517/",
        "https://www.forelle.com/en_US/rugby/484/",
        "https://www.forelle.com/en_US/volleyball/352/",
        "https://www.forelle.com/en_US/balls/272/",
    ]

    scraper = ForelleScraper()
    scraper.run(category_urls)


if __name__ == "__main__":
    main()
