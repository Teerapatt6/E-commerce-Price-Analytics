## ขั้นตอนการรัน Airflow ด้วย Docker

### 1. Build Docker Image
เปิด PowerShell ในโฟลเดอร์โปรเจกต์ แล้วรัน:
```powershell
docker build -t dnds-airflow .
```

### 2. รัน Airflow
```powershell
./start-airflow.ps1
```

### 3. เข้าสู่ระบบ Airflow
เปิดเว็บเบราว์เซอร์ไปที่: http://localhost:8080  
Login ด้วย username/password: admin/admin

---

### 4. Pause / Unpause DAGs
Pause DAG:
```powershell
docker exec -it dnds-airflow-webserver airflow dags pause scrape_products_daily
```

Unpause DAG:
```powershell
docker exec -it dnds-airflow-webserver airflow dags unpause scrape_products_daily
```

### 5. ตรวจสอบ DAG logs
```powershell
docker logs -f dnds-airflow-webserver
```

### 6. ปิด Airflow
หยุด container ทั้งหมด:
```powershell
docker stop dnds-airflow-webserver dnds-airflow-scheduler
```
ลบ container (ถ้าต้องการ):
```powershell
docker rm -f dnds-airflow-webserver dnds-airflow-scheduler
```