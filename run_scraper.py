import os
import csv
import asyncio
from playwright.async_api import async_playwright

CATEGORY_ITEM    = "ul.products li.product"
CATEGORY_LINK    = f"{CATEGORY_ITEM} a"
VARIATION_FORM   = "form.variations_form"

async def get_product_links(page):
    # wait for the category grid to appear
    await page.wait_for_selector(CATEGORY_ITEM)
    # pull all hrefs
    return await page.locator(CATEGORY_LINK).evaluate_all(
        "els => els.map(el => el.href)"
    )

async def scrape_product(page, product_url, writer):
    print(f"→ scraping variants on {product_url}")
    await page.goto(product_url)
    # your existing variation logic lives here:
    await page.wait_for_selector(VARIATION_FORM)
    variants = await page.locator(VARIATION_FORM).element_handles()
    if not variants:
        print("   ⚠️ no variants found, skipping")
        return

    for form in variants:
        # adjust these selectors to match your CSV schema:
        sku   = await form.get_attribute("data-product_sku")
        price = await form.locator(".woocommerce-variation-price .amount").inner_text()
        writer.writerow({ "sku": sku, "price": price, "url": product_url })

async def main():
    base_url = os.environ["BASE_URL"]
    rate     = float(os.environ.get("RATE_LIMIT", 1.0))

    # open CSV once for all products
    with open("products.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sku","price","url"])
        writer.writeheader()

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page    = await browser.new_page()

            # 1️⃣ Category pass: grab every product link
            await page.goto(base_url)
            if await page.locator(CATEGORY_ITEM).count() > 0:
                prod_urls = await get_product_links(page)
            else:
                # if it wasn’t a category, just treat BASE_URL as one product
                prod_urls = [base_url]

            # 2️⃣ Product pass: visit each product and scrape its variants
            for url in prod_urls:
                await scrape_product(page, url, writer)
                await asyncio.sleep(1.0 / rate)

            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
