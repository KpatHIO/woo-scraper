import os
import asyncio
import csv
from playwright.async_api import async_playwright

# ──────────────────────────────────────────────────────────────────────────────
# Read the product page URL from the env passed in by your workflow
PRODUCT_URL = os.environ.get("BASE_URL")
if not PRODUCT_URL:
    raise RuntimeError("Environment variable BASE_URL must be set to the product URL")
# ──────────────────────────────────────────────────────────────────────────────

async def get_options(page, selector):
    """
    Return a list of { value: "...", text: "Label" } for all <option> elements
    that have a real value and aren’t just the placeholder.
    """
    return await page.eval_on_selector_all(
        selector,
        """
        els => els
          .filter(e => e.value && e.value !== "" && !/choose|select/i.test(e.textContent))
          .map(e => ({ value: e.value, text: e.textContent.trim() }))
        """
    )

async def main():
    print("🔍 Starting scraper…")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(PRODUCT_URL)

        # 1) grab all your dropdown options
        locs   = await get_options(page, 'select[name="attribute_pa_location"] option')
        rvals  = await get_options(page, 'select[name="attribute_pa_r-value"] option')
        widths = await get_options(page, 'select[name="attribute_pa_width"] option')

        # 2) open the CSV once
        with open("variants.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["location", "r_value", "width", "price", "url"]
            )
            writer.writeheader()

            # 3) nested loops for each combination
            for loc in locs:
                await page.select_option(
                    'select[name="attribute_pa_location"]',
                    loc["value"]
                )
                for rval in rvals:
                    await page.select_option(
                        'select[name="attribute_pa_r-value"]',
                        rval["value"]
                    )
                    for width in widths:
                        await page.select_option(
                            'select[name="attribute_pa_width"]',
                            width["value"]
                        )

                        # let the price AJAX update
                        await page.wait_for_timeout(500)

                        # skip if “Add to cart” is disabled
                        btn = await page.query_selector("button.single_add_to_cart_button")
                        if btn:
                            if await btn.get_attribute("disabled"):
                                continue

                        # pull the price text (strip currency symbols)
                        price = await page.text_content(".woocommerce-Price-amount.amount") or ""
                        price = price.replace("$", "").replace("€", "").strip()

                        # write the row
                        writer.writerow({
                            "location": loc["text"],
                            "r_value":  rval["text"],
                            "width":    width["text"],
                            "price":    price,
                            "url":      PRODUCT_URL
                        })
                        print(f"✔️  {loc['text']} | {rval['text']} | {width['text']} → {price}")

        await browser.close()
        print("✅ Done! Wrote variants.csv")

if __name__ == "__main__":
    asyncio.run(main())
