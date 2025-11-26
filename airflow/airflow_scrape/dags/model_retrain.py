import os
from airflow import DAG
from airflow.providers.http.operators.http import SimpleHttpOperator
from datetime import datetime, timedelta

BASE_URL = os.getenv("BASE_URL") 
HTTP_CONN_ID = 'price_prediction_api' 

SCHEDULE_INTERVAL = '0 9 * * *' 

with DAG(
    dag_id='s24_price_predictor_retrain_daily_10am',
    start_date=datetime(2023, 1, 1),
    # schedule_interval=SCHEDULE_INTERVAL,
    schedule_interval="@once",
    catchup=False,
    default_args={
        'owner': 'airflow',
        'depends_on_past': False,
        'email_on_failure': False,
        'email_on_retry': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    tags=['ml', 'prediction', 'retrain'],
) as dag:
    retrain_task = SimpleHttpOperator(
        task_id='trigger_model_retrain',
        http_conn_id=HTTP_CONN_ID,
        endpoint='/retrain', 
        method='GET', 
        headers={"Content-Type": "application/json"},
        log_response=True,
        response_check=lambda response: response.json().get('status') == 'success',
        extra_options={"timeout": 600} 
    )