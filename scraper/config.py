import os
from dotenv import load_dotenv

load_dotenv()  # reads .env when running locally

def get_settings():
    """
    Returns:
      base_url (str): the WooCommerce category to scrape
      rate_limit (float): requests per second
    """
    base_url = os.getenv("BASE_URL")
    if not base_url:
        raise ValueError("BASE_URL is not set in environment")
    try:
        rate = float(os.getenv("RATE_LIMIT", "1"))
    except ValueError:
        rate = 1.0
    return base_url, rate
