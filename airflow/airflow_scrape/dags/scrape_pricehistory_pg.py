import os
from dotenv import load_dotenv
from selenium import webdriver
import re, base64, json, pandas as pd
import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

load_dotenv()

PRODUCT_URL = os.getenv("PRODUCT_URL") 
MAX_WAIT = 10

DATABASE_URL = os.getenv("DATABASE_URL") 

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
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
        print("Cannot find required JS variables")
        return pd.DataFrame()

    key = key_match.group(1)
    blob = blob_match.group(1)

    raw = base64.b64decode(blob)
    dec = bytes([raw[i] ^ ord(key[i % len(key)]) for i in range(len(raw))]).decode("utf-8")

    json_data = json.loads(dec)
    pts = json_data["History"]["Price"]

    df = pd.DataFrame(pts)
    df = df.rename(columns={"x": "date", "y": "price_inr"})
    df["price_thb"] = df["price_inr"] * 0.44

    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    full_dates = pd.date_range(df['date'].min(), pd.Timestamp.today())
    df = df.set_index('date').reindex(full_dates)
    df.index.name = 'date'

    df['price_inr'] = df['price_inr'].ffill()
    df['price_thb'] = df['price_thb'].ffill()

    df = df.reset_index()
    return df[["date", "price_inr", "price_thb"]]

def connect_db():
    return psycopg2.connect(DATABASE_URL)

def insert_to_postgres(df):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pricehistory (
            id SERIAL PRIMARY KEY,
            date TEXT UNIQUE,
            price_inr NUMERIC,
            price_thb NUMERIC
        )
    """)

    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO pricehistory (date, price_inr, price_thb)
            VALUES (%s, %s, %s)
            ON CONFLICT (date) DO NOTHING;
        """, (row["date"], row["price_inr"], row["price_thb"]))

    conn.commit()
    cur.close()
    conn.close()

def scrape_main():
    df = scrape_pricehistory(PRODUCT_URL)
    if df.empty:
        print("No data scraped")
        return
    insert_to_postgres(df)
    print(f"Inserted {len(df)} rows into PostgreSQL")

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "scrape_pricehistory_pg",
    default_args=default_args,
    schedule_interval='@once',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["scraping", "postgres"],
) as dag:

    scrape_task = PythonOperator(
        task_id="scrape_to_postgres",
        python_callable=scrape_main,
    )
