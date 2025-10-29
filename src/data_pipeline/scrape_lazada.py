"""
src/data_pipeline/scrape_lazada.py
Simple skeleton script for scraping (example).
Run locally for testing: python -m src.data_pipeline.scrape_lazada
"""
import os
import argparse
import logging
import csv
from datetime import datetime

# configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_DIR = os.getenv("DATA_RAW_DIR", "data/raw")

def fetch_example():
    """
    Replace this function with real scraper or sample CSV loader.
    For PoC, we return list of dict rows.
    """
    now = datetime.utcnow().isoformat()
    sample = [
        {"product_id": "P001", "product_name": "Sample A", "price": 100.0, "timestamp": now, "platform": "lazada"},
        {"product_id": "P002", "product_name": "Sample B", "price": 200.0, "timestamp": now, "platform": "lazada"},
    ]
    return sample

def save_csv(rows, filename=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if filename is None:
        filename = f"lazada_sample_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    path = os.path.join(OUTPUT_DIR, filename)
    keys = rows[0].keys()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    logger.info(f"Saved {len(rows)} rows to {path}")
    return path

def main():
    rows = fetch_example()
    save_csv(rows)

if __name__ == "__main__":
    main()
