import os
import csv
import asyncio
from playwright.async_api import async_playwright

CATEGORY_ITEM    = "ul.products li.product"
CATEGORY_LINK    = f"{CATEGORY_ITEM} a"
VARIATION_FORM   = "form.variations_form"

async def get_product_links(page):
    # wait for the category grid to appear
    await page.wait_for_selector(CATEGORY_ITEM, timeout=20_000)
    # pull all hrefs
    return await page.locator(CATEGORY_LINK).evaluate_all(
        "els => els.map(el => el.href)"
    )

async def scrape_product(page, product_url, writer):
    print(f"→ scraping variants on {product_url}")
    # navigate, but don’t block forever waiting for every network call
    try:
        await page.goto(product_url, wait_until="load", timeout=60_000)
    except Exception as e:
        print(f"⚠️ navigation warning: {e}")

    # count how many variation‐forms appear
    form_locator = page.locator(VARIATION_FORM)
    count = await form_locator.count()
    if count == 0:
        print("⚠️ no variants found (or JS failed) on this page – skipping.")
        return

    # wait for at least the first one to become visible
    await form_locator.first.wait_for(state="visible", timeout=20_000)

    # grab all the variation‐form handles
    variants = await form_locator.element_handles()
    for form in variants:
        sku_el   = await form.get_attribute("data-product_sku")
        price_el = await form.locator(".woocommerce-variation-price .amount").inner_text()
        writer.writerow({
            "sku":   sku_el   or "",
            "price": price_el or "",
            "url":   product_url
        })

async def main():
    base_url = os.getenv("BASE_URL")
    rate     = float(os.getenv("RATE_LIMIT", "1.0"))

    # open CSV once for all products
    with open("products.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sku","price","url"])
        writer.writeheader()

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page    = await browser.new_page()

            # CATEGORY vs SINGLE‐PRODUCT logic
            await page.goto(base_url, wait_until="load", timeout=60_000)
            if await page.locator(CATEGORY_ITEM).count() > 0:
                prod_urls = await get_product_links(page)
            else:
                prod_urls = [base_url]

            # scrape each URL
            for url in prod_urls:
                await scrape_product(page, url, writer)
                await asyncio.sleep(1.0 / rate)

            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
