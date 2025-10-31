$DAGS_DIR = "D:\Network project\dags"
$AIRFLOW_DB_DIR = "D:\Network project\airflow_db"
$DATA_DIR = "D:\Network project\data"  # เก็บ CSV
$IMAGE_NAME = "DNDS-airflow"
$WEBSERVER_NAME = "DNDS-airflow-webserver"
$SCHEDULER_NAME = "DNDS-airflow-scheduler"

docker rm -f $WEBSERVER_NAME -ErrorAction SilentlyContinue
docker rm -f $SCHEDULER_NAME -ErrorAction SilentlyContinue

docker run --rm -v "${DAGS_DIR}:/opt/airflow/dags" `
    -v "${AIRFLOW_DB_DIR}:/opt/airflow" `
    $IMAGE_NAME db init

docker run --rm -v "${DAGS_DIR}:/opt/airflow/dags" `
    -v "${AIRFLOW_DB_DIR}:/opt/airflow" `
    $IMAGE_NAME users create `
        --username admin `
        --firstname Admin `
        --lastname User `
        --role Admin `
        --email admin@acskmutt.com `
        --password admin

docker run -d -p 8080:8080 `
    -v "${DAGS_DIR}:/opt/airflow/dags" `
    -v "${AIRFLOW_DB_DIR}:/opt/airflow" `
    -v "${DATA_DIR}:/home/airflow/airflow/data" `
    --name $WEBSERVER_NAME `
    $IMAGE_NAME webserver

docker run -d `
    -v "${DAGS_DIR}:/opt/airflow/dags" `
    -v "${AIRFLOW_DB_DIR}:/opt/airflow" `
    -v "${DATA_DIR}:/home/airflow/airflow/data" `
    --name $SCHEDULER_NAME `
    $IMAGE_NAME scheduler

Write-Host "Airflow webserver running at http://localhost:8080"
Write-Host "DAGs folder: $DAGS_DIR"
Write-Host "Airflow DB folder: $AIRFLOW_DB_DIR"
Write-Host "Data folder: $DATA_DIR"