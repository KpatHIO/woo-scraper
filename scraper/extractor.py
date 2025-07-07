import time
from playwright.sync_api import sync_playwright

def extract_variants(page_url: str, rate_limit: float):
    """
    Visit a WooCommerce product page, select each variant in turn,
    and record (variant_name, price). Returns (product_name, list).
    """
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(page_url)
        # brief pause to let JS render
        time.sleep(1 / rate_limit)

        # 1. Get the product name
        title_el = page.query_selector("h1.product_title")  # adjust selector if needed
        product_name = title_el.inner_text().strip() if title_el else page_url

        # 2. Find the first <select> inside the variations form
        select = page.query_selector("form.variations_form select")
        if select:
            options = select.query_selector_all("option")
            for opt in options:
                value = opt.get_attribute("value")
                # skip the “Choose an option” entry
                if not value or value.startswith("default"):
                    continue

                # select this variant
                select.select_option(value=value)
                # wait for price to update
                page.wait_for_selector(".woocommerce-Price-amount")
                time.sleep(0.2)  # slight buffer

                # read price
                price_el = page.query_selector(".woocommerce-Price-amount")
                price = price_el.inner_text().strip() if price_el else ""

                # record variant name + price
                variant_name = opt.inner_text().strip()
                results.append((variant_name, price))
        else:
            # no variants; grab the single price
            price_el = page.query_selector(".woocommerce-Price-amount")
            price = price_el.inner_text().strip() if price_el else ""
            results.append(("Default", price))

        browser.close()

    return product_name, results
