import os
from typing import List, Dict
import csv
import logging
import time
from typing import List
from itertools import product
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import requests
import re


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

    def save_urls_to_csv(self, filename: str = 'forelle_product_urlss.csv'):
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


class ForelleVariantScraper:
    def __init__(self, base_url: str = "https://www.forelle.com"):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        self.service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=self.service, options=chrome_options)
        self.session = requests.Session()

        self.base_url = base_url
        self.variant_urls = set()

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s: %(message)s',
            handlers=[
                logging.FileHandler('forelle_variant_scraping.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _extract_product_id(self, url: str) -> str:
        match = re.search(r'/p/[^/]+/(\d+)/', url)
        if match:
            return match.group(1)

        parts = url.split('/')
        for i, part in enumerate(parts):
            if part.isdigit():
                return part

        self.logger.error(f"Impossible d'extraire l'ID du produit de l'URL : {url}")
        return ""

    def get_product_variants(self, product_url: str) -> List[Dict]:
        product_id = self._extract_product_id(product_url)
        if not product_id:
            self.logger.error(f"ID de produit non trouvé pour {product_url}")
            return []

        variant_filter_url = f"{self.base_url}/en_US/api/v1/product/v2/{product_id}/variant-filter/"
        response = self.session.get(variant_filter_url)

        if response.status_code == 200:
            return response.json()
        else:
            self.logger.error(f"Échec de la récupération des variants pour {product_url}. Code de statut : {response.status_code}")
            return []

    from itertools import product

    def generate_variant_urls(self, product_url: str, variants: List[Dict]) -> List[str]:
        variant_urls = []
        try:
            product_id = self._extract_product_id(product_url)
            if not product_id:
                self.logger.error(f"Product ID not found for {product_url}")
                return [product_url]

            # Build variant attributes
            size_variant = next((v for v in variants if v['name'] == 'Size'), None)
            color_variant = next((v for v in variants if v['name'] == 'Variant'), None)

            if not size_variant:
                self.logger.warning(f"No size variants found for {product_url}")
                return [product_url]

            # Get all size options
            size_options = size_variant['options']
            color_options = color_variant['options'] if color_variant else [None]

            # Generate combinations
            for size in size_options:
                for color in color_options:
                    filters = {
                        str(size_variant['id']): str(size['id'])
                    }

                    if color:
                        filters[str(color_variant['id'])] = str(color['id'])

                    variant_url_request = {
                        "attribute": str(size_variant['id']),
                        "value": str(size['id']),
                        "filters": filters
                    }

                    try:
                        response = self.session.post(
                            f"{self.base_url}/en_US/xhr/product/get_filter_attributes/{product_id}",
                            json=variant_url_request,
                            timeout=10
                        )

                        if response.status_code == 200:
                            response_data = response.json()
                            if response_data.get('url'):
                                variant_url = f"{self.base_url}{response_data['url']}"
                                variant_urls.append(variant_url)
                                self.logger.info(f"Generated variant URL: {variant_url}")
                        else:
                            self.logger.error(f"API error for {product_url}, status: {response.status_code}")

                    except Exception as e:
                        self.logger.error(f"Error while making API request for variant: {e}")
                        continue

            if not variant_urls:
                self.logger.warning(f"No variant URLs generated for {product_url}")
                return [product_url]

        except Exception as e:
            self.logger.error(f"Error while generating variant URLs for {product_url}: {e}")
            return [product_url]

        return variant_urls
    def scrape_variant_urls(self, product_urls: List[str]):
        for product_url in product_urls:
            try:
                variants = self.get_product_variants(product_url)

                if variants:
                    variant_urls = self.generate_variant_urls(product_url, variants)

                    for variant_url in variant_urls:
                        self.variant_urls.add(variant_url)

            except Exception as e:
                self.logger.error(f"Erreur lors du scraping des variants pour {product_url}: {e}")

    def save_urls_to_csv(self, filename: str = 'forelle_variant_urls2.csv'):
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Product/Variant URL'])

                for url in self.variant_urls:
                    writer.writerow([url])

            self.logger.info(f"Enregistrement terminé. Total d'URLs uniques : {len(self.variant_urls)}")
            print(f"Sauvegardé {len(self.variant_urls)} URLs uniques dans {filename}")

        except Exception as e:
            self.logger.error(f"Erreur lors de l'enregistrement des URLs : {e}")

    def run(self, product_urls: List[str]):
        try:
            self.scrape_variant_urls(product_urls)
            self.save_urls_to_csv()

        except Exception as e:
            self.logger.error(f"Le processus de scraping a échoué : {e}")

        finally:
            self.driver.quit()


def main():
    # Scrape product URLs from category pages
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
        "https://www.forelle.com/en_US/p/nike-vapor-jet-7-0-n-100-3505-xl-black/15000/",
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

    # Run variant scraper with the product URLs captured
    product_urls = scraper.product_urls
    variant_scraper = ForelleVariantScraper()
    variant_scraper.run(list(product_urls))


if __name__ == "__main__":
    main()
