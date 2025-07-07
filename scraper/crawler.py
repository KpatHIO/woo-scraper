import time
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

def get_product_urls(base_url: str, rate_limit: float) -> list[str]:
    """
    Uses Playwright to load each paginated category page (product-page=1,2,…),
    waits for the product grid to render, then extracts all hrefs containing '/product/'.
    Stops when no new URLs appear.
    """
    product_urls: list[str] = []
    page_num = 1

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        while True:
            url = f"{base_url}?product-page={page_num}"
            print(f"▶ Loading {url}")
            page.goto(url)
            # wait up to 5s for at least one product link to appear
            try:
                page.wait_for_selector("a[href*='/product/']", timeout=5000)
            except:
                print("⚠️ No products found on this page; stopping pagination.")
                break

            anchors = page.query_selector_all("a[href*='/product/']")
            new_found = 0
            for a in anchors:
                href = a.get_attribute("href")
                # make absolute
                href = urljoin(base_url, href)
                if href not in product_urls:
                    product_urls.append(href)
                    new_found += 1

            print(f"  • Page {page_num}: found {new_found} new products (total {len(product_urls)})")
            if new_found == 0:
                break

            page_num += 1
            time.sleep(1 / rate_limit)

        browser.close()

    return product_urls
