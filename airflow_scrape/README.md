## ขั้นตอนการรัน Airflow ด้วย Docker

### 1. Build Docker Image
เปิด PowerShell ในโฟลเดอร์โปรเจกต์ แล้วรัน:
```powershell
docker build -t DNDS-airflow .
```

### 2. ปรับ path ใน start-airflow.ps1
แก้ค่าตัวแปรให้ตรงกับเครื่องที่รัน:
```powershell
$DAGS_DIR = "D:\Network project\dags"
$AIRFLOW_DB_DIR = "D:\Network project\airflow_db"
$DATA_DIR = "D:\Network project\data"
```

### 3. รัน Airflow
```powershell
./start-airflow.ps1
```

### 4. เข้าสู่ระบบ Airflow
เปิดเว็บเบราว์เซอร์ไปที่: http://localhost:8080  
Login ด้วย username/password: admin/admin

---

### 5. Pause / Unpause DAGs
Pause DAG:
```powershell
docker exec -it DNDS-airflow-webserver airflow dags pause scrape_products_daily
```

Unpause DAG:
```powershell
docker exec -it DNDS-airflow-webserver airflow dags unpause scrape_products_daily
```

### 6. ตรวจสอบ DAG logs
```powershell
docker logs -f DNDS-airflow-webserver
```

### 7. ปิด Airflow
หยุด container ทั้งหมด:
```powershell
docker stop DNDS-airflow-webserver DNDS-airflow-scheduler
```
ลบ container (ถ้าต้องการ):
```powershell
docker rm -f DNDS-airflow-webserver DNDS-airflow-scheduler
```