from selenium import webdriver
import re, base64, json, pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

PRODUCT_URLS = [
    "https://pricehistory.app/p/samsung-galaxy-s24-5g-ai-smartphone-cobalt-6pOg3s2h"
]
MAX_WAIT = 10 
SHEET_KEY = "19_PDN8T2OjMV49tQTTblBPPtt6C_9oWg-yeSjqRYjFA" 
SERVICE_ACCOUNT_FILE = "/opt/airflow/dags/quixotic-strand-453812-r2-275fa3e318d7.json" 

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=1920,1080")
    return webdriver.Chrome(options=options)

def scrape_pricehistory(url):
    driver = create_driver()
    driver.get(url)
    driver.implicitly_wait(MAX_WAIT)

    html = driver.page_source
    driver.quit()

    key_match = re.search(r"let CachedKey\s*=\s*'([^']+)'", html)
    blob_match = re.search(r'PagePriceHistoryDataSet\s*=\s*"([^"]+)"', html)
    
    if not key_match or not blob_match:
        print(f"Cannot find CachedKey or PagePriceHistoryDataSet in {url}")
        return pd.DataFrame()

    key = key_match.group(1)
    blob = blob_match.group(1)

    raw = base64.b64decode(blob)
    dec = bytes([raw[i] ^ ord(key[i % len(key)]) for i in range(len(raw))]).decode("utf-8")

    prices_json = json.loads(dec)
    pts = prices_json["History"]["Price"]

    df = pd.DataFrame(pts).rename(columns={"x": "date", "y": "price_inr"})
    df["price_thb"] = df["price_inr"] * 0.44
    df["url"] = url

    return df[["url", "date", "price_inr", "price_thb"]]

def connect_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_KEY).sheet1
    return sheet

def sheet_to_df(sheet):
    data = sheet.get_all_values()
    expected_columns = ["url", "date", "price_inr", "price_thb"]

    if not data or len(data) < 2:
        return pd.DataFrame(columns=expected_columns)

    header = data[0]
    rows = data[1:]

    df = pd.DataFrame(rows, columns=expected_columns)
    df["price_inr"] = pd.to_numeric(df["price_inr"], errors="coerce")
    df["price_thb"] = pd.to_numeric(df["price_thb"], errors="coerce")
    return df

def df_to_sheet(sheet, df):
    sheet.clear()
    sheet.update("A1", [df.columns.tolist()])
    sheet.update("A2", df.values.tolist())

def scrape_main():
    sheet = connect_sheet()
    existing_df = sheet_to_df(sheet)

    for url in PRODUCT_URLS:
        df_new = scrape_pricehistory(url)
        if df_new.empty:
            continue

        combined = pd.concat([existing_df, df_new]).drop_duplicates(subset=["url", "date"], keep="first")
        if len(combined) > len(existing_df):
            df_to_sheet(sheet, combined)
            print(f"Updated Google Sheet with {len(combined) - len(existing_df)} new records")
            existing_df = combined
        else:
            print(f"No new records to update for {url}")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

with DAG(
    'scrape_pricehistory_daily',
    default_args=default_args,
    description='Scrape price history and update Google Sheet daily at 8 AM',
    # schedule_interval='@daily',
    schedule_interval='@once',
    # schedule_interval='0 8 * * *',
    start_date=datetime(2025, 10, 21),
    catchup=False,
    tags=['scraping', 'production'],
) as dag:

    scrape_task = PythonOperator(
        task_id='scrape_pricehistory',
        python_callable=scrape_main,
    )