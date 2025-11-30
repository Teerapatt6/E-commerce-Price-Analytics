# E-commerce Price Analytics & Forecasting System
**Case Study: Samsung Galaxy S24 (Amazon India)**

## 🔎 Overview
โปรเจกต์นี้เป็นส่วนหนึ่งของวิชา CSS342 Data Science & Data Engineering โดยมีวัตถุประสงค์เพื่อพัฒนาระบบอัตโนมัติ (Automated Pipeline) สำหรับติดตามและพยากรณ์ราคาสมาร์ทโฟน Samsung Galaxy S24 บนแพลตฟอร์ม Amazon India

ระบบสามารถดึงข้อมูลราคาประจำวัน ทำความสะอาดข้อมูล และใช้โมเดล Machine Learning (XGBoost) พยากรณ์แนวโน้มราคาล่วงหน้า 30 วัน เพื่อช่วยให้ผู้บริโภคตัดสินใจซื้อในช่วงเวลาที่คุ้มค่าที่สุด

## 📌 Key Features
- **Automated Data Pipeline:** ดึงข้อมูลอัตโนมัติทุกวันด้วย Apache Airflow และ Selenium
- **Advanced Scraping:** เทคนิค Headless Chrome และ Data Decoding (Base64/XOR) เพื่อจัดการข้อมูลจาก Pricehistory.app
- **Robust Storage:** จัดเก็บข้อมูลแบบ Time-series ลงใน PostgreSQL (Upsert Logic)
- **Feature Engineering:** สร้างตัวแปร Lag Features, Rolling Statistics, และ EWMA เพื่อจับ Pattern ราคา
- **High Accuracy Forecasting:** โมเดล XGBoost ให้ผลแม่นยำสูงสุด (RMSE 241.30)
- **Prediction API:** รองรับการดึงผลพยากรณ์ผ่าน REST API

## 🏗️ System Architecture
1. **Data Ingestion:** Python + Selenium (Headless) ดึงข้อมูลจาก Client-side Rendering

2. **Orchestration:** Apache Airflow จัดการ Workflow และ Retry Policy

3. **Storage:** PostgreSQL เก็บข้อมูล Raw และ Processed Data

4. **Modeling:** เปรียบเทียบ 6 โมเดล (Statistical vs DL vs Ensemble)

5. **Deployment:** Model Serving ผ่าน API

## 🛠️ Tech Stack
## Data Engineering
- **Orchestration:** Apache Airflow
- **Scraping:** Selenium WebDriver, Google Chrome (Headless)
- **Database:** PostgreSQL
- **Containerization:** Docker

## Data Science
- **Language:** Python
- **Data Processing:** Pandas, NumPy
- **Machine Learning:** XGBoost, Scikit-learn
- **Deep Learning:** TensorFlow/Keras (1D-CNN, GRU)
- **Statistical:** Statsmodels (ARIMA, SARIMA)

## 👥 Team Roles
- Project Manager / Analyst: Tee
- Data Scientist: Mai
- Data Engineer: Namsai
- Data Scientist/Engineer: Tee (2)

**Disclaimer:** ข้อมูลราคาสินค้าใช้เพื่อการศึกษาและวิจัยเท่านั้น
