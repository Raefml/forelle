# Forelle Scraper

A Python-based web scraping project that uses Selenium to scrape product URLs from various categories on the Forelle website and saves them into a CSV file. The scraper handles pagination, navigates through multiple product categories, and ensures all product links are captured.

## Features

- **Scrapes multiple product categories**: The scraper extracts product URLs from different categories listed on the Forelle website.
- **Pagination handling**: It automatically handles pagination and continues scraping until all products are extracted from a category.
- **Error handling and logging**: Logs errors and progress, and retries in case of issues.
- **Saves URLs to CSV**: The product URLs are saved in a CSV file for easy access and further processing.

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/Raefml/forelle_scraping.git
   cd forelle_scraping
