import os
import csv
import asyncio
from playwright.async_api import async_playwright

# ——— CONFIG ———
# On your category page, each product has a "Buy Now" link that points to the product URL
PRODUCT_LINK_SELECTOR   = 'a:has-text("Buy Now")'
# On your product pages, WooCommerce renders each variation in a <form class="variations_form …">
VARIATION_FORM_SELECTOR = "form.variations_form"


async def get_product_links(page):
    # wait for the Buy Now buttons to show up
    await page.wait_for_selector(PRODUCT_LINK_SELECTOR)
    # grab every unique href
    links = await page.locator(PRODUCT_LINK_SELECTOR).evaluate_all(
        "els => Array.from(new Set(els.map(el => el.href)))"
    )
    print(f"→ found {len(links)} product links")
    return links


async def scrape_product(page, product_url, writer):
    print(f"→ scraping variants on {product_url}")
    await page.goto(product_url)

    # count variants forms
    variant_locator = page.locator(VARIATION_FORM)
    count = await variant_locator.count()
    if count == 0:
        print("⚠️ no variants found – skipping")
        return

    # wait for at least one to be visible
    await variant_locator.first.wait_for(state="visible")

    # now loop
    for i in range(count):
        form = variant_locator.nth(i)
        sku   = await form.get_attribute("data-product_sku")
        price = await form.locator(".woocommerce-variation-price .amount") \
                        .inner_text()
        writer.writerow({ "sku": sku, "price": price, "url": product_url })


async def main():
    base_url = os.environ.get("BASE_URL")
    if not base_url:
        raise RuntimeError("❌  BASE_URL env var is required")

    rate = float(os.environ.get("RATE_LIMIT", 1.0))

    # open CSV once, write header
    with open("products.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sku", "price", "url"])
        writer.writeheader()

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page    = await browser.new_page()

            print(f"Starting scrape of {base_url}")
            await page.goto(base_url)

            # 1️⃣ grab all product-page links
            prod_urls = await get_product_links(page)
            if not prod_urls:
                # fallback: maybe BASE_URL is itself a product page
                prod_urls = [base_url]

            # 2️⃣ visit each product and scrape its variants
            for url in prod_urls:
                await scrape_product(page, url, writer)
                await asyncio.sleep(1.0 / rate)

            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
