import time
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

def get_product_urls(base_url: str, rate_limit: float) -> list[str]:
    """
    Loads each shop page under /page/1/, /page/2/, … waits for the JS-rendered product links,
    then collects all unique URLs containing '/product/'. Stops when a page yields zero new links.
    """
    product_urls: list[str] = []
    page_num = 1
    base = base_url.rstrip("/")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        while True:
            # build the page URL
            page_url = f"{base}/page/{page_num}/" if page_num > 1 else base_url
            print(f"▶ Loading {page_url}")
            page.goto(page_url)

            # wait up to 5s for any product link to appear
            try:
                page.wait_for_selector("a[href*='/product/']", timeout=5000)
            except:
                print("⚠️ No products found (or JS failed) on this page – stopping.")
                break

            anchors = page.query_selector_all("a[href*='/product/']")
            new_found = 0
            for a in anchors:
                href = a.get_attribute("href")
                # normalize to absolute
                href = urljoin(base_url, href)
                if href not in product_urls:
                    product_urls.append(href)
                    new_found += 1

            print(f"  • Page {page_num}: {new_found} new product links (total {len(product_urls)})")
            if new_found == 0:
                break

            page_num += 1
            time.sleep(1 / rate_limit)

        browser.close()

    return product_urls
