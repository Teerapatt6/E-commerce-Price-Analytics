## SUMMARY
ไฟล์นี้คือข้อมูลราคาของโทรศัพท์รุ่น s24 จากแพลตฟอร์มเดียว ผ่านการ clean, เติม feature และจัดเรียงเรียบร้อยแล้ว สามารถใช้ต่อกับ Dashboard, Forecast Model ได้ทันที
> จำนวนฟิลด์ทั้งหมด: 7 columns

## Field-Level Details
1. `price_inr`
* Type: float
* Example: `79999.0`
* Description: ราคาสินค้าในสกุลเงิน INR (อินเดียรูปี) ค่านี้ไม่ถูกใช้ใน EDA หลัก แต่เก็บไว้เพื่อ reference กรณีต้องการแปลงค่าเงินหรือเปรียบเทียบสกุลเงินในอนาคต
* Source: Raw Data
2. `date`
* Type: datetime
* Example: `2024-01-20 10:08:12`
* Description: วันที่ & เวลา ของการเก็บข้อมูลราคาใช้เป็น index หลักสำหรับ price trend, moving averages
* Cleaning Applied:
    * แปลงเป็น datetime
    * เรียงตามลำดับเวลา (sort)
3. `price_thb`
* Type: float
* Example: `35199.56`
* Description: ราคาสินค้าของวันนั้นในสกุลเงินบาท (THB) เป็นตัวแปรหลักสำคัญ ใช้เป็น input สำหรับ EDA, distribution, trend และ forecasting
* Cleaning Applied:
    * remove price ≤ 0
    * remove duplicates
4. `price_diff`
* Type: float
* Example: `0.0`
* Description: ส่วนต่างของราคาระหว่างวันนี้และวันก่อนหน้าใช้ดูพฤติกรรมการขึ้น–ลงของราคาแบบรายวัน
* Calculation:
```
price_diff = price_today - price_yesterday
```
* Usage:
    * detect days with sudden price drops
    * identify campaign/promotion periods

5. `pct_change`
* Type: float (percentage)
* Example: `0.0`
* Description: เปอร์เซ็นต์ `%` การเปลี่ยนแปลงของราคาแบบวันต่อวันใช้วิเคราะห์ความผันผวน (volatility) ของสินค้า
* Calculation:
```
pct_change = (price_diff / price_yesterday) * 100
```
* Usage:
    * detect price spikes
    * detect flash sale days
6. `MA7`
* Type: float
* Example: `NaN` (ช่วงแรกไม่มีค่าจนครบ 7 จุด)
* Description: ค่าเฉลี่ยแบบเคลื่อนที่ 7 วัน ใช้เพื่อมอง trend ระยะสั้นของราคาทำให้กราฟราคาเนียนขึ้นและอ่านง่ายขึ้น
* Calculation:
```
MA7 = rolling mean(window=7)
```
* Usage:
    * compare actual vs trend
    * identify best-buy windows
7. `MA14`
* Type: float
* Example: `NaN`
* Description: ค่าเฉลี่ยแบบเคลื่อนที่ 14 วัน ใช้หาแนวโน้มราคาระยะกลาง (medium-term trend)
* Calculation:
```
MA14 = rolling mean(window=14)
```
* Usage:
    * best-buy algorithm
    * support forecast smoothing

## Pipeline Origin
| Field | Source | Created in Pipeline | Purpose |
| :--- | :--- | :--- | :--- |
| price_inr | Raw | No | Currency reference |
| date | Raw | No (cleaned only) | Timeline index |
| price_thb | Raw | No (cleaned only) | Main analysis variable |
| price_diff | Derived | Yes | Daily price movement |
| pct_change | Derived | Yes | Daily volatility |
| MA7 | Derived | Yes | Trend smoothing |
| MA14 | Derived | Yes | Trend smoothing |






