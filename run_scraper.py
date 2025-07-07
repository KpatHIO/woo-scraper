import os
import csv
import asyncio
from playwright.async_api import async_playwright

PRODUCT_LINK = "a.woocommerce-LoopProduct-link"  # Updated selector
VARIATION_FORM = "form.variations_form"

async def get_product_links(page):
    # Wait for at least one product link to appear
    await page.wait_for_selector(PRODUCT_LINK)
    # Get all product URLs from the category page
    return await page.locator(PRODUCT_LINK).evaluate_all("els => els.map(el => el.href)")

async def scrape_product(page, product_url, writer):
    print(f"→ scraping variants on {product_url}")
    await page.goto(product_url, wait_until="domcontentloaded")
    # Check if there are any variation forms on the page
    variant_count = await page.locator(VARIATION_FORM).count()
    if variant_count:
        await page.locator(VARIATION_FORM).first.wait_for(state="visible")
        variants = await page.locator(VARIATION_FORM).element_handles()
        for form in variants:
            sku = await form.get_attribute("data-product_sku")
            # This selector may need adjustment depending on the product page structure
            try:
                price = await form.query_selector(".woocommerce-variation-price .amount")
                price_text = await price.inner_text() if price else ""
            except Exception:
                price_text = ""
            writer.writerow({"sku": sku, "price": price_text, "url": product_url})
    else:
        print("⚠️ no variants found (or JS failed) on this page – skipping.")

async def main():
    base_url = os.environ["BASE_URL"]
    rate = float(os.environ.get("RATE_LIMIT", 1.0))

    with open("products.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sku", "price", "url"])
        writer.writeheader()

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Try to get product links from the category page
            await page.goto(base_url, wait_until="networkidle")
            if await page.locator(PRODUCT_LINK).count() > 0:
                prod_urls = await get_product_links(page)
            else:
                # If not a category page, treat BASE_URL as a single product
                prod_urls = [base_url]

            for url in prod_urls:
                await scrape_product(page, url, writer)
                await asyncio.sleep(1.0 / rate)

            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
