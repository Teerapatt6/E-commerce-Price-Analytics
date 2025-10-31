from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
}

def validate_latest_csv():
    import pandas as pd
    import glob

    folder = "/home/airflow/airflow/data"
    files = sorted(glob.glob(f"{folder}/products_*.csv"))
    if not files:
        raise ValueError("No CSV file found!")

    latest_file = files[-1]
    df = pd.read_csv(latest_file)

    if df.empty:
        raise ValueError("CSV file is empty!")

    if df["name"].isnull().any() or df["price"].isnull().any():
        raise ValueError("Some records missing name or price!")

    print(f"Validation passed for {latest_file}")

with DAG(
    'scrape_products_daily',
    default_args=default_args,
    description='Scrape product data every 6 hours and validate output',
    schedule_interval='@once', # for test
    # schedule_interval='@weekly',
    start_date=datetime(2025, 10, 21),
    catchup=False,
    tags=['scraping', 'production'],
) as dag:

    scrape_task = BashOperator(
        task_id='scrape_products',
        bash_command='python /opt/airflow/dags/scripts/scrape_products.py'
    )

    validate_task = PythonOperator(
        task_id='validate_csv',
        python_callable=validate_latest_csv
    )

    scrape_task >> validate_task
