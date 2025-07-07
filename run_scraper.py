import os
import asyncio
import csv
import json  # Import the json module
from playwright.async_api import async_playwright

# ──────────────────────────────────────────────────────────────────────────────
# Read the product page URL from the env passed in by your workflow
PRODUCT_URL = os.environ.get("BASE_URL")
if not PRODUCT_URL:
    raise RuntimeError("Environment variable BASE_URL must be set to the product URL")
# ──────────────────────────────────────────────────────────────────────────────

async def main():
    print("🔍 Starting scraper…")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(PRODUCT_URL, wait_until="domcontentloaded") # wait until DOM is loaded

        # --- NEW APPROACH: Extract data directly from JavaScript data layer ---
        # Evaluate JavaScript on the page to get the wpmDataLayer.products object
        # This will return a Python dictionary representation of the JavaScript object
        all_product_data = await page.evaluate("window.wpmDataLayer.products")

        # 2) open the CSV once
        with open("variants.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["id", "sku", "name", "price", "location", "r_value", "width", "url"]
            )
            writer.writeheader()

            # Iterate through the extracted product data
            for product_id, data in all_product_data.items():
                # Only process variations, not the parent product if it exists in the dataLayer
                # Check 'is_variation' key which is True for variations
                if data.get("is_variation"):
                    # The 'variant' string needs parsing
                    variant_str = data.get("variant", "")
                    location = ""
                    r_value = ""
                    width = ""

                    # Parse the variant string "Location: ..., R-value: ..., Width: ..."
                    parts = variant_str.split(' | ')
                    for part in parts:
                        if part.lower().startswith("location:"):
                            location = part.split(':', 1)[1].strip()
                        elif part.lower().startswith("r-value:"):
                            r_value = part.split(':', 1)[1].strip()
                        elif part.lower().startswith("width:"):
                            width = part.split(':', 1)[1].strip()

                    writer.writerow({
                        "id": data.get("id"),
                        "sku": data.get("sku"),
                        "name": data.get("name"),
                        "price": data.get("price"),
                        "location": location,
                        "r_value": r_value,
                        "width": width,
                        "url": PRODUCT_URL # Base URL for the product page
                    })
                    print(f"✔️ ID: {data.get('id')} | SKU: {data.get('sku')} | {location} | {r_value} | {width} → {data.get('price')}")

        await browser.close()
        print("✅ Done! Wrote variants.csv")

if __name__ == "__main__":
    asyncio.run(main())
