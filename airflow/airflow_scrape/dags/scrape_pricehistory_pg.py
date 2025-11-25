import os
from dotenv import load_dotenv
from selenium import webdriver
import re, base64, json, pandas as pd
import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
import numpy as np

load_dotenv()

PRODUCT_URL = os.getenv("PRODUCT_URL") 
MAX_WAIT = 10
DATABASE_URL = os.getenv("DATABASE_URL") 

# ----------------- Web Scraping -----------------
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
    return df.reset_index()[["date", "price_inr", "price_thb"]]

# ----------------- DB -----------------
def connect_db():
    return psycopg2.connect(DATABASE_URL)

def insert_to_postgres(df):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pricehistory (
            id SERIAL PRIMARY KEY,
            date DATE UNIQUE,
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

# ----------------- Feature Engineering -----------------
def create_features():
    conn = connect_db()
    df = pd.read_sql("SELECT date, price_inr, price_thb FROM pricehistory ORDER BY date ASC", conn)
    df['date'] = pd.to_datetime(df['date'])
    price_series = df['price_inr'].astype(float)
    price_thb_series = df['price_thb'].astype(float)

    # ---------------- Clean by PCT change ----------------
    price_series = df['price_inr'].astype(float)
    price_thb_series = df['price_thb'].astype(float)
    
    threshold = 0.1
    data_scaled = (price_series - price_series.min()) / (price_series.max() - price_series.min())
    pct_change = data_scaled.pct_change().abs().fillna(0)
    
    keep_idx = pct_change <= threshold

    price_series_clean = price_series.copy()
    price_thb_series_clean = price_thb_series.copy()

    price_series_clean[~keep_idx] = np.nan
    price_thb_series_clean[~keep_idx] = np.nan

    price_series_clean = price_series_clean.ffill()
    price_thb_series_clean = price_thb_series_clean.ffill()

    dates_clean = df['date']

    # ----------------- Feature Creation ----------------
    price_diff_series = price_series_clean.diff(1)
    price_thb_diff_series = price_thb_series_clean.diff(1)

    X_feat = pd.DataFrame()
    lags = [1,2,3,5,7,10,14,21,30]

    # --- 1. Lagged Price Level Feature ---
    X_feat['price_lag_1'] = price_series_clean.shift(1)

    # --- 2. Lagged Price Difference Features ---
    for lag in lags[1:]:
        X_feat[f'diff_lag_{lag}'] = price_diff_series.shift(lag)

    # --- 3. Rolling Mean/Std (Moving Averages & Volatility) Features ---
    X_feat['diff_rolling7_mean'] = price_diff_series.rolling(7).mean().bfill() 
    X_feat['diff_rolling30_mean'] = price_diff_series.rolling(30).mean().bfill() 
    X_feat['diff_rolling7_std'] = price_diff_series.rolling(7).std().bfill() 
    X_feat['diff_rolling30_std'] = price_diff_series.rolling(30).std().bfill() 

    # --- 4. Exponentially Weighted Moving Average (EWMA) Features ---
    alphas = [0.1,0.3,0.5,0.7]
    for a in alphas:
        col_name = f"ewma_diff_alpha_{str(a).replace('.', '_')}"
        X_feat[col_name] = price_diff_series.ewm(alpha=a, adjust=False).mean()

    # --- 5. Features from THB Price (Multivariate) ---
    X_feat['thb_diff_lag_1'] = price_thb_diff_series.shift(1) 
    X_feat['thb_diff_rolling7'] = price_thb_diff_series.rolling(7).mean().bfill() 

    # --- 6. Date/Calendar Features ---
    X_feat['dayofweek'] = dates_clean.dt.dayofweek.astype(float) # วันในสัปดาห์ (0=จันทร์, 6=อาทิตย์)
    X_feat['dayofyear'] = dates_clean.dt.dayofyear.astype(float) # วันที่ของปี (1-365)
    X_feat['dayofmonth'] = dates_clean.dt.day.astype(float) # วันที่ของเดือน (1-31)

    X_feat = X_feat.fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_feat)
    X_scaled_df = pd.DataFrame(X_scaled, columns=X_feat.columns)
    X_scaled_df['date'] = dates_clean  

    # ---------------- SQL ----------------
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS price_features (
            date DATE UNIQUE,
            price_lag_1 FLOAT,
            diff_lag_2 FLOAT,
            diff_lag_3 FLOAT,
            diff_lag_5 FLOAT,
            diff_lag_7 FLOAT,
            diff_lag_10 FLOAT,
            diff_lag_14 FLOAT,
            diff_lag_21 FLOAT,
            diff_lag_30 FLOAT,
            diff_rolling7_mean FLOAT,
            diff_rolling30_mean FLOAT,
            diff_rolling7_std FLOAT,
            diff_rolling30_std FLOAT,
            ewma_diff_alpha_0_1 FLOAT,
            ewma_diff_alpha_0_3 FLOAT,
            ewma_diff_alpha_0_5 FLOAT,
            ewma_diff_alpha_0_7 FLOAT,
            thb_diff_lag_1 FLOAT,
            thb_diff_rolling7 FLOAT,
            dayofweek FLOAT,
            dayofyear FLOAT,
            dayofmonth FLOAT
        )
    """)
    for _, row in X_scaled_df.iterrows():
        row_vals = [row['date']] + [float(row[c]) for c in X_feat.columns]
        cur.execute("""
            INSERT INTO price_features (
                date, price_lag_1, diff_lag_2, diff_lag_3, diff_lag_5, diff_lag_7,
                diff_lag_10, diff_lag_14, diff_lag_21, diff_lag_30,
                diff_rolling7_mean, diff_rolling30_mean, diff_rolling7_std, diff_rolling30_std,
                ewma_diff_alpha_0_1, ewma_diff_alpha_0_3, ewma_diff_alpha_0_5, ewma_diff_alpha_0_7,
                thb_diff_lag_1, thb_diff_rolling7, dayofweek, dayofyear, dayofmonth
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (date) DO NOTHING;
        """, tuple(row_vals))
    conn.commit()
    cur.close()
    conn.close()
    print(f"Feature storage updated: {len(X_scaled_df)} rows")

# ----------------- DAG -----------------
def scrape_and_create_features():
    df = scrape_pricehistory(PRODUCT_URL)
    if not df.empty:
        insert_to_postgres(df)
    create_features()

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "scrape_pricehistory_pg_features_clean",
    default_args=default_args,
    schedule_interval='@once',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["scraping", "postgres", "features", "cleaned"],
) as dag:

    task = PythonOperator(
        task_id="scrape_and_feature_storage",
        python_callable=scrape_and_create_features,
    )