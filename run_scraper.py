import os
import csv
import asyncio
from playwright.async_api import async_playwright

# ─── your CSS selectors ────────────────────────────────────────────────────────
CATEGORY_ITEM    = "ul.products li.product"
CATEGORY_LINK    = f"{CATEGORY_ITEM} a"
VARIATION_FORM   = "form.variations_form"

async def get_product_links(page):
    await page.wait_for_selector(CATEGORY_ITEM)
    return await page.locator(CATEGORY_LINK).evaluate_all(
        "els => els.map(el => el.href)"
    )

async def scrape_product(page, product_url, writer):
    print(f"→ scraping variants on {product_url}")
    await page.goto(product_url)

    # 1) count how many variation forms there are
    variant_locator = page.locator(VARIATION_FORM)
    count = await variant_locator.count()
    if count == 0:
        print("⚠️ no variants found – skipping")
        return

    # 2) wait until the first one is actually visible
    await variant_locator.first.wait_for(state="visible")

    # 3) loop over them by index so that 'form' is itself a Locator
    for i in range(count):
        form = variant_locator.nth(i)
        sku   = await form.get_attribute("data-product_sku")
        price = await form.locator(".woocommerce-variation-price .amount") \
                        .inner_text()
        writer.writerow({
            "sku":   sku,
            "price": price,
            "url":   product_url,
        })

async def main():
    base_url = os.environ["BASE_URL"]
    rate     = float(os.environ.get("RATE_LIMIT", 1.0))

    # open CSV once for all products
    with open("products.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sku", "price", "url"])
        writer.writeheader()

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page    = await browser.new_page()

            #───────────────────────────────────────────────────────────
            # 1️⃣ Category pass: grab every product link
            await page.goto(base_url)
            if await page.locator(CATEGORY_ITEM).count() > 0:
                prod_urls = await get_product_links(page)
            else:
                prod_urls = [base_url]

            #───────────────────────────────────────────────────────────
            # 2️⃣ Product pass: visit each product and scrape its variants
            for url in prod_urls:
                await scrape_product(page, url, writer)
                await asyncio.sleep(1.0 / rate)

            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
