import asyncio
import csv
from playwright.async_api import async_playwright

PRODUCT_URL = "https://pricewiseinsulation.com.au/product/knauf-earthwool-thermal-ceiling-insulation-batts/"

async def get_options(page, selector):
    return await page.eval_on_selector_all(
        selector,
        '''els => els
            .filter(e => e.value && e.value !== "" && !/choose|select/i.test(e.textContent))
            .map(e => ({value: e.value, text: e.textContent.trim()}))
        '''
    )

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(PRODUCT_URL)

        # Get all valid options
        locs = await get_options(page, 'select[name="attribute_pa_location"] option')
        rvals = await get_options(page, 'select[name="attribute_pa_r-value"] option')
        widths = await get_options(page, 'select[name="attribute_pa_width"] option')

        # Open CSV to write results
        with open("variants.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["location", "r_value", "width", "price", "url"])
            writer.writeheader()

            for loc in locs:
    # ← Wrap this select in try/except
    try:
        await page.select_option(
            'select[name="attribute_pa_location"]',
            loc['value']
        )
    except Exception as e:
        print(f"Skipping invalid location: {loc['value']} ({e})")
        continue

    for rval in rvals:
        # ← And wrap this one too
        try:
            await page.select_option(
                'select[name="attribute_pa_r-value"]',
                rval['value']
            )
        except Exception as e:
            print(f"Skipping invalid R-value: {rval['value']} ({e})")
            continue

        for width in widths:
            # ← And this one
            try:
                await page.select_option(
                    'select[name="attribute_pa_width"]',
                    width['value']
                )
            except Exception as e:
                print(f"Skipping invalid width: {width['value']} ({e})")
                continue

                        # Wait for price update (AJAX)
                        await page.wait_for_timeout(500)  # Wait a little for AJAX, can be improved

                        # Check if combination is available (Add to Cart enabled)
                        add_btn = await page.query_selector('button.single_add_to_cart_button')
                        if add_btn:
                            disabled = await add_btn.get_attribute("disabled")
                            if disabled:
                                continue  # Not available

                        # Get price (or blank if not shown)
                        price = await page.text_content('.woocommerce-Price-amount.amount') or ""
                        price = price.replace("\u20ac", "").replace("$", "").strip()

                        # Save row
                        writer.writerow({
                            "location": loc['text'],
                            "r_value": rval['text'],
                            "width": width['text'],
                            "price": price,
                            "url": PRODUCT_URL
                        })

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
