$CURRENT_DIR = (Get-Location).Path
$DAGS_DIR = Join-Path $CURRENT_DIR "dags"
$AIRFLOW_DB_DIR = Join-Path $CURRENT_DIR "airflow_db"
$IMAGE_NAME = "dnds-airflow"
$WEBSERVER_NAME = "dnds-airflow-webserver"
$SCHEDULER_NAME = "dnds-airflow-scheduler"

docker rm -f $WEBSERVER_NAME -ErrorAction SilentlyContinue
docker rm -f $SCHEDULER_NAME -ErrorAction SilentlyContinue

docker run --rm `
    -v "${DAGS_DIR}:/opt/airflow/dags" `
    -v "${AIRFLOW_DB_DIR}:/opt/airflow" `
    $IMAGE_NAME db init

docker run --rm `
    -v "${DAGS_DIR}:/opt/airflow/dags" `
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
    --name $WEBSERVER_NAME `
    $IMAGE_NAME webserver

docker run -d `
    -v "${DAGS_DIR}:/opt/airflow/dags" `
    -v "${AIRFLOW_DB_DIR}:/opt/airflow" `
    --name $SCHEDULER_NAME `
    $IMAGE_NAME scheduler

Write-Host ""
Write-Host "Airflow webserver running at http://localhost:8080"
Write-Host "DAGs folder: $DAGS_DIR"
Write-Host "Airflow DB folder: $AIRFLOW_DB_DIR"