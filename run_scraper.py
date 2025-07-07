import os
import csv
import asyncio
from playwright.async_api import async_playwright

# ─────────────────────────────────────────────────────────────────────────────
# Adjust these if your theme uses different classes
CATEGORY_ITEM  = "ul.products li.product"
CATEGORY_LINK  = f"{CATEGORY_ITEM} a"
VARIATION_FORM = "form.variations_form"
# ─────────────────────────────────────────────────────────────────────────────

async def get_product_links(page):
    """Scrape all <a> hrefs out of your category grid."""
    await page.wait_for_selector(CATEGORY_ITEM, timeout=10_000)
    return await page.locator(CATEGORY_LINK).evaluate_all(
        "els => els.map(el => el.href)"
    )

async def scrape_product(page, product_url, writer):
    """Visit one product page, pull out every variation form, extract sku+price."""
    print(f"→ scraping variants on {product_url}")
    # give the JS time to finish loading all variation HTML
    await page.goto(product_url, wait_until="networkidle")
    # count how many variation forms actually appeared
    variant_count = await page.locator(VARIATION_FORM).count()
    if variant_count == 0:
        print("⚠️ no variants found (or JS failed) on this page – skipping.")
        return

    # wait for at least the first one to be visible
    await page.locator(VARIATION_FORM).first.wait_for(state="visible", timeout=10_000)

    # pull them all into a list of ElementHandles
    variants = await page.locator(VARIATION_FORM).element_handles()

    for form in variants:
        sku   = await form.get_attribute("data-product_sku")
        # adjust this to whatever selector holds your price text
        price = await form.locator(".woocommerce-variation-price .amount").inner_text()
        writer.writerow({
            "sku":   sku,
            "price": price,
            "url":   product_url
        })

async def main():
    # pull in your two environment variables
    base_url = os.getenv("BASE_URL", "").strip()
    if not base_url:
        raise RuntimeError("❌ BASE_URL environment variable must be set before running.")
    rate = float(os.getenv("RATE_LIMIT", "1.0"))

    # open one CSV for the entire run
    with open("products.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sku", "price", "url"])
        writer.writeheader()

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page    = await browser.new_page()

            # 1️⃣ CATEGORY PASS: grab every product link (or treat BASE_URL as a single product)
            await page.goto(base_url, wait_until="networkidle")
            if await page.locator(CATEGORY_ITEM).count() > 0:
                prod_urls = await get_product_links(page)
            else:
                prod_urls = [base_url]

            # 2️⃣ PRODUCT PASS: hit each product page in turn
            for url in prod_urls:
                await scrape_product(page, url, writer)
                # rate limit so you don’t DDOS the server
                await asyncio.sleep(1.0 / rate)

            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
