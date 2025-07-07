import os
import csv
import asyncio
from playwright.async_api import async_playwright

# ─── SITE-SPECIFIC SELECTORS ────────────────────────────────────────────
# product links are in <h3><a href="…/product/…">…
PRODUCT_LINK   = 'h3 a[href*="/product/"]'
# on each product page, the variation form still has this class:
VARIATION_FORM = "form.variations_form"

async def get_product_links(page):
    # wait for at least one product link to appear
    await page.wait_for_selector(PRODUCT_LINK)
    # pull all hrefs
    return await page.locator(PRODUCT_LINK).evaluate_all(
        "els => els.map(el => el.href)"
    )

async def scrape_product(page, product_url, writer):
    print(f"→ scraping variants on {product_url}")
    await page.goto(product_url)

    # count how many variation forms exist
    count = await page.locator(VARIATION_FORM).count()
    if count == 0:
        print("⚠️ no variants found (or JS failed) on this page – skipping.")
        return

    # wait for the first one to become visible
    await page.locator(VARIATION_FORM).first.wait_for(state="visible")

    # grab each form element handle
    forms = await page.locator(VARIATION_FORM).element_handles()
    for form in forms:
        # adjust these selectors to match your CSV schema:
        sku   = await form.get_attribute("data-product_sku")
        price = await form.query_selector(".woocommerce-variation-price .amount")
        price_text = await price.inner_text() if price else ""
        writer.writerow({
            "sku": sku or "",
            "price": price_text,
            "url": product_url
        })

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
            prod_urls = await get_product_links(page)

            # 2️⃣ Product pass: visit each product and scrape its variants
            for url in prod_urls:
                await scrape_product(page, url, writer)
                await asyncio.sleep(1.0 / rate)

            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
