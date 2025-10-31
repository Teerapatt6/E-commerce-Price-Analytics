from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv, os
from datetime import datetime

SEARCH_TERMS = ["mobile phone", "smartphone", "iPhone", "Android phone"]
OUT_DIR = "/home/airflow/airflow/data"
MAX_WAIT = 10  

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage") 
    options.add_argument("window-size=1920,1080")
    
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        raise RuntimeError(f"Cannot start Chrome driver: {e}")
    return driver

def scrape_lazada(search_query):
    driver = create_driver()
    url = f"https://www.lazada.co.th/catalog/?q={search_query}"
    driver.get(url)

    try:
        WebDriverWait(driver, MAX_WAIT).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.Bm3ON"))
        )
    except:
        print(f"No products found for Lazada search: {search_query}")
        driver.quit()
        return []

    products = driver.find_elements(By.CSS_SELECTOR, "div.Bm3ON")
    results = []

    for p in products[:50]:
        try:
            name = p.find_element(By.CSS_SELECTOR, "div.RfADt a").text.strip()
        except:
            name = None
        try:
            price = p.find_element(By.CSS_SELECTOR, "div.aBrP0 span").text.strip()
        except:
            price = None
        if name and price:
            results.append({
                "platform": "Lazada",
                "search_term": search_query,
                "name": name,
                "price": price
            })

    print(f"Lazada: Found {len(results)} products for '{search_query}'")
    driver.quit()
    return results

def scrape_ebay(search_query):
    driver = create_driver()
    url = f"https://www.ebay.com/sch/i.html?_nkw={search_query}"
    driver.get(url)

    try:
        WebDriverWait(driver, MAX_WAIT).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.s-item"))
        )
    except:
        print(f"No products found for eBay search: {search_query}")
        driver.quit()
        return []

    products = driver.find_elements(By.CSS_SELECTOR, "li.s-item")
    results = []

    for p in products[:50]:
        try:
            name = p.find_element(By.CSS_SELECTOR, "h3.s-item__title").text.strip()
        except:
            name = None
        try:
            price = p.find_element(By.CSS_SELECTOR, "span.s-item__price").text.strip()
        except:
            price = None
        if name and price:
            results.append({
                "platform": "eBay",
                "search_term": search_query,
                "name": name,
                "price": price
            })

    print(f"eBay: Found {len(results)} products for '{search_query}'")
    driver.quit()
    return results

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d_%H-%M")
    file_path = os.path.join(OUT_DIR, f"products_{today}.csv")

    all_results = []
    for term in SEARCH_TERMS:
        all_results.extend(scrape_lazada(term))
        all_results.extend(scrape_ebay(term))

    valid = [r for r in all_results if r["name"] and r["price"]]
    if not valid:
        raise ValueError("No valid records scraped.")

    keys = ["platform", "search_term", "name", "price"]
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(valid)

    print(f"Saved {len(valid)} records to {file_path}")

if __name__ == "__main__":
    main()