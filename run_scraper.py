import csv
from scraper.config import get_settings
from scraper.crawler import get_product_urls
from scraper.extractor import extract_variants

def main():
    # Load BASE_URL and RATE_LIMIT from env (or GitHub secrets)
    base_url, rate_limit = get_settings()
    print(f"Starting scrape of {base_url} at {rate_limit} req/s")

    # 1. Crawl listing pages for all product URLs
    product_urls = get_product_urls(base_url, rate_limit)

    # 2. For each product, extract variants & prices
    rows = []
    for url in product_urls:
        product_name, variants = extract_variants(url, rate_limit)
        for variant_name, price in variants:
            rows.append({
                "Product": product_name,
                "Variant": variant_name,
                "Price": price,
                "URL": url
            })

    # 3. Write out to CSV
    fieldnames = ["Product", "Variant", "Price", "URL"]
    with open("products.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done! Scraped {len(rows)} variant prices into products.csv")

if __name__ == "__main__":
    main()
