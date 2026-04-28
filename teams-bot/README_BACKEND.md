# 🤖 RoomBot NLP Backend Documentation

ส่วนนี้คือระบบ Backend ที่ทำหน้าที่เป็นตัวกลางระหว่าง **Microsoft Teams** และ **ระบบจองห้องพัก** โดยใช้ AI (Gemini) ในการวิเคราะห์ภาษาธรรมชาติ (NLP)

## 🏗️ Architecture Overview

1.  **Microsoft Teams (Outgoing Webhook)**: เมื่อมีคนพิมพ์หา Bot ใน Teams, ข้อมูลจะถูกส่งมาที่ HTTPS Endpoint ของเรา
2.  **Nginx (Caddy)**: ทำหน้าที่เป็น Reverse Proxy และจัดการ HTTPS (SSL)
3.  **Django (REST Framework)**: รับ Request เข้ามาที่ `/api/nlp/`
4.  **Gemini AI (NLP Service)**: วิเคราะห์ประโยคภาษาไทยให้กลายเป็นข้อมูล JSON (ห้อง, วันที่, เวลา)
5.  **Database (SQLite)**: บันทึกรายการจองลงในฐานข้อมูล

---

## 🛠️ Tech Stack หลัก

-   **Language**: Python 3.11
-   **Framework**: Django + Django REST Framework
-   **AI**: Google Generative AI (Gemini 2.5 Flash / 3.1 Flash Lite)
-   **Deployment**: Docker Compose (Web + Caddy)

---

## 📂 ไฟล์สำคัญที่ควรรู้

-   `bookings/views.py`: ตัวรับ Request จาก Teams และสั่งการบันทึกลงฐานข้อมูล
-   `bookings/nlp_service.py`: หัวใจหลักที่คุยกับ Gemini เพื่อแปลภาษาคนให้เป็นข้อมูลเครื่อง
-   `room_booking/settings.py`: การตั้งค่าระบบ รวมถึงการอนุญาต Host (`ALLOWED_HOSTS`)
-   `deploy.sh`: สคริปต์สำหรับส่ง Code ขึ้น VPS และสั่ง Restart Docker อัตโนมัติ

---

## 🚀 วิธีการทำงาน (Workflow)

1.  **User Message**: `@RoomBot จองห้อง 406-3 พรุ่งนี้ 9 โมง`
2.  **Cleansing**: ระบบจะตัด Tag HTML และชื่อ `@RoomBot` ออกให้เหลือแค่คำสั่ง
3.  **NLP Analysis**: Gemini จะวิเคราะห์และคืนค่ามาเป็น:
    ```json
    {
      "intent": "create_booking",
      "room_id": "406-3",
      "date": "2026-04-28",
      "start_time": "09:00",
      "end_time": "10:00"
    }
    ```
4.  **Database Check**: ระบบเช็คในฐานข้อมูลว่าห้องว่างหรือไม่ (Status: APPROVED/PENDING)
5.  **Response**: ส่งข้อความกลับไปที่ Teams เพื่อยืนยันการจอง

---

## 📡 การ Deploy

หากมีการแก้ไข Code ให้รันสคริปต์นี้เพื่ออัปเดตขึ้น VPS ทันที:
```bash
./deploy.sh
```

---

## ⚠️ ข้อควรระวัง
-   **API Key**: ต้องระบุ `GEMINI_API_KEY` ในไฟล์ `.env` เสมอ
-   **HTTPS**: Teams บังคับว่าต้องเรียกผ่าน HTTPS เท่านั้น (Caddy จัดการให้แล้ว)
-   **Whitelist**: หาก Deploy บน Server ใหม่ ต้องไปเพิ่ม IP ใน Microsoft Teams Webhook ด้วย
