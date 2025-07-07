import time
import requests
from bs4 import BeautifulSoup

def get_product_urls(base_url: str, rate_limit: float) -> list[str]:
    """
    Crawl WooCommerce category pages and collect all product page URLs.
    Stops when a page returns no products.
    """
    headers = {"User-Agent": "woo-scraper-bot/1.0"}
    product_urls: list[str] = []
    page = 1

    while True:
        list_url = f"{base_url}?product-page={page}"
        print(f"Crawling {list_url} …")
        resp = requests.get(list_url, headers=headers)
        if resp.status_code != 200:
            print(f" → Status {resp.status_code}; stopping.")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        # Adjust this selector if your theme differs:
        items = soup.select("ul.products li.product a.woocommerce-LoopProduct-link")

        if not items:
            print(" → No more products found; pagination complete.")
            break

        for a in items:
            href = a.get("href")
            if href and href not in product_urls:
                product_urls.append(href)

        print(f" → Page {page}: found {len(items)} products (total {len(product_urls)})")
        time.sleep(1 / rate_limit)
        page += 1

    return product_urls
