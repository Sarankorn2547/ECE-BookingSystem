# 🤖 RoomBot — Teams Bot NLP Backend

ส่วนนี้คือ Backend ที่ทำหน้าที่รับข้อความจาก **Microsoft Teams** แปลงด้วย AI แล้วจัดการการจองห้องของภาควิชา ECE

---

## 🏗️ Architecture Overview

```
Microsoft Teams
      │  (Outgoing Webhook POST)
      ▼
Caddy (HTTPS Reverse Proxy)
      │  booking.vivaclubs.site/api/nlp/
      ▼
Django REST Framework  (/api/nlp/)
      │
      ├── OpenTyphoon AI  →  แปลงข้อความภาษาไทยเป็น JSON intent
      └── PostgreSQL (server-db-1)  →  บันทึกการจอง
```

---

## 🛠️ Tech Stack

| Component | รายละเอียด |
|-----------|-----------|
| Language | Python 3.11 |
| Framework | Django 4.2 + Django REST Framework |
| AI / NLP | OpenTyphoon AI (`typhoon-v2.5-30b-a3b-instruct`) |
| Database | PostgreSQL (shared `server-db-1` container) |
| Reverse Proxy | Caddy (auto HTTPS) |
| Deployment | Docker Compose |

---

## 📂 ไฟล์สำคัญ

| ไฟล์ | หน้าที่ |
|------|--------|
| `bookings/views.py` | รับ request จาก Teams, จัดการทุก intent |
| `bookings/nlp_service.py` | เรียก Typhoon AI แปลงข้อความเป็น JSON |
| `bookings/models.py` | โมเดล Room และ Booking |
| `room_booking/settings.py` | Django settings (ALLOWED_HOSTS, DB, etc.) |
| `docker-compose.yml` | รัน web + caddy container |
| `.env` | Environment variables (ไม่อยู่ใน git) |

---

## 🗣️ คำสั่งที่รองรับ

| Intent | ตัวอย่าง |
|--------|---------|
| `create_booking` | จองห้อง 406-3 พรุ่งนี้ 9 โมงถึง 10 โมง สอนวิชา CN332 |
| `check_availability` | พรุ่งนี้ห้องไหนว่างบ้าง |
| `check_room` | ห้อง 406-3 พรุ่งนี้ว่างช่วงไหน |
| `my_bookings` | ดูการจองของฉัน |
| `cancel_booking` | ยกเลิกการจองห้อง 406-3 พรุ่งนี้ |
| `help` | help |
| Admin | อนุมัติ #5 / ปฏิเสธ #5 เหตุผล... |

---

## 🚀 Workflow

```
1. User พิมพ์ใน Teams:  @RoomBot จองห้อง 406-3 พรุ่งนี้ 9 โมง
2. Teams ส่ง POST → https://booking.vivaclubs.site/api/nlp/
3. Django ตัด HTML tag (<at>, <p>, &nbsp;) ออก
4. Typhoon AI แปลงข้อความ → JSON intent
5. views.py จัดการตาม intent (สร้างจอง / เช็คว่าง / ยกเลิก ฯลฯ)
6. ตอบกลับ Teams ทันที (response body = reply message)
```

---

## ⚠️ ข้อควรระวัง

- **HTTPS บังคับ**: Teams Outgoing Webhook ส่งได้เฉพาะ HTTPS เท่านั้น
- **API Key**: ต้องมี `TYPHOON_API_KEY` ในไฟล์ `.env` เสมอ
- **การ deploy**: ดูขั้นตอนใน `DEVELOPER_GUIDE.md`
