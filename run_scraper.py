import os
import csv
import asyncio
from playwright.async_api import async_playwright

async def scrape_product(page, product_url, writer):
    print(f"→ Scraping product at {product_url}")
    await page.goto(product_url, wait_until="domcontentloaded", timeout=60000)

    # Get option dropdowns
    dropdown_selectors = [
        "select#pa_location",  # Location
        "select#pa_r-value",   # R-Value
        "select#pa_width"      # Width
    ]

    # Get all possible option values for each dropdown
    option_values = []
    for sel in dropdown_selectors:
        opts = await page.locator(f"{sel} option").all()
        # Skip the first option ("Choose an option")
        values = []
        for opt in opts[1:]:
            value = await opt.get_attribute("value")
            if value:
                values.append(value)
        option_values.append(values)

    # For all combinations
    from itertools import product
    for loc, rval, width in product(*option_values):
        # Select the options
        await page.select_option(dropdown_selectors[0], loc)
        await page.select_option(dropdown_selectors[1], rval)
        await page.select_option(dropdown_selectors[2], width)
        await asyncio.sleep(0.5)  # give JS a moment

        # Wait for price to update
        price_elem = page.locator("p.price span.woocommerce-Price-amount bdi")
        await price_elem.wait_for(state="visible", timeout=8000)
        price = await price_elem.inner_text()

        writer.writerow({
            "location": loc,
            "r_value": rval,
            "width": width,
            "price": price,
            "url": product_url
        })
        print(f"    {loc} | {rval} | {width} = {price}")

async def main():
    base_url = os.environ["BASE_URL"]
    rate     = float(os.environ.get("RATE_LIMIT", 1.0))

    # open CSV
    with open("products.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["location", "r_value", "width", "price", "url"])
        writer.writeheader()

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page    = await browser.new_page()

            # Grab all product URLs from category or treat as single product
            await page.goto(base_url)
            product_links = [base_url]
            # Optionally, you can update the logic here for category scraping

            for url in product_links:
                await scrape_product(page, url, writer)
                await asyncio.sleep(1.0 / rate)

            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
