# ECE Room Booking System

ระบบจองห้องประชุมและห้องเรียน ภาควิชาวิศวกรรมไฟฟ้าและคอมพิวเตอร์  
คณะวิศวกรรมศาสตร์ มหาวิทยาลัยธรรมศาสตร์

> Django Web Application สำหรับการจองห้องประชุมและห้องเรียนจำนวน 5 ห้องภายในภาควิชา  
> รองรับการยืนยันตัวตนผ่าน TU REST API

---

## 📋 SRS Reference

Based on [SRS Document v1.0](https://wachira.ece.engr.tu.ac.th/share/webapp/SRS_Room_Booking_std.html) — 7 เมษายน 2569

---

## 🛠️ Tech Stack

| Layer     | Technology                                     |
| --------- | ---------------------------------------------- |
| Backend   | Django 5.x (Python)                            |
| Frontend  | Bootstrap 5, Font Awesome, HTMX               |
| Database  | SQLite (development)                           |
| Auth      | TU REST API (`restapi.tu.ac.th`)               |
| Fonts     | Sarabun, Noto Sans Thai (Google Fonts)         |

---

## ✅ Development Progress

### Use Cases from SRS

| Status | Use Case | Description |
| :----: | -------- | ----------- |
| ✅ Done | **UC-01: Login** | เข้าสู่ระบบผ่าน TU REST API |
| ✅ Done | **UC-02: จองห้อง** | ฟอร์มจองห้องพร้อม backend |
| ✅ Done | **UC-03: อนุมัติ/ปฏิเสธการจอง** | Admin อนุมัติหรือปฏิเสธพร้อมเหตุผล |
| ✅ Done | **UC-04: ดูปฏิทินห้องว่าง** | ปฏิทินห้องพร้อม FullCalendar และ API |
| ✅ Done | **UC-05: ดูรายงานสถิติ** | รายงานการใช้ห้องดึงข้อมูลจาก DB จริง |
| ✅ Done | **UC-06: ยกเลิกการจอง** | ยกเลิกการจอง |

### Module Breakdown

#### ✅ Module 1 — Authentication (Done)

- [x] Login page with TU REST API integration
- [x] Session management with TU profile data (name, department, faculty, type)
- [x] Auto-create/update Django User on successful TU authentication
- [x] Logout with session cleanup
- [x] `@login_required` protection on dashboard
- [x] Error handling — invalid credentials, timeout, connection errors
- [x] Django messages framework with Bootstrap alert styling
- [x] Loading spinner on form submit

#### ✅ Module 2 — Dashboard (Done)

- [x] Dashboard page with dynamic user info from TU profile
- [x] Welcome banner with user's Thai display name
- [x] Navbar navigation with admin-only menu items (role-aware)
- [x] Top header with user name and department
- [x] Quick action cards (จองห้อง, การจองของฉัน, ปฏิทินห้อง)
- [x] Recent bookings table — แสดง 5 รายการล่าสุดจาก DB

#### ✅ Module 3 — Booking Form (Done)

- [x] Template: `booking-form.html`
- [x] Django view and URL route
- [x] Room model (5 rooms)
- [x] Booking model (room, user, date, time, purpose, status)
- [x] Time slot conflict detection
- [x] Form validation
- [x] Save booking with Pending status

#### ✅ Module 4 — My Bookings (Done)

- [x] Template: `my-bookings.html`
- [x] Django view and URL route
- [x] List user's bookings with status filters
- [x] Cancel booking functionality (UC-06)

#### ✅ Module 5 — Calendar (Done)

- [x] Template: `calendar.html`
- [x] Django view and URL route
- [x] FullCalendar integration with booking data
- [x] Filter by room
- [x] Weekly/monthly view

#### ✅ Module 6 — Admin Approvals (Done)

- [x] Template: `admin-approvals.html` — แปลงเป็น Django template จริง
- [x] Django view (`approval_queue_view`) และ URL route `/admin/approvals/`
- [x] แสดง PENDING bookings ทั้งหมดจาก DB พร้อม booker info
- [x] Approve — POST `/admin/approvals/<id>/approve/` บันทึก approval_by, approval_at
- [x] Reject — POST `/admin/approvals/<id>/reject/` พร้อมรับเหตุผลจาก modal form
- [x] บันทึก BookingLog ทุกการตัดสินใจ
- [x] `admin_required` decorator — ป้องกันด้วย UserProfile.role = ADMIN

#### ✅ Module 7 — Admin Reports (Done)

- [x] Template: `admin-reports.html` — แปลงเป็น Django template จริง
- [x] Django view (`admin_reports_view`) และ URL route `/admin/reports/`
- [x] Summary cards: ยอดรวม, รออนุมัติ, อนุมัติแล้ว, ปฏิเสธ (ดึงจาก DB)
- [x] ตารางการใช้งานแต่ละห้อง เรียงจากมากไปน้อย

#### ✅ Module 8 — Admin System Management (Done)

- [x] Template: `admin-system.html` — แปลงเป็น Django template จริง
- [x] Django view (`admin_system_view`) และ URL route `/admin/system/`
- [x] Tab "จัดการห้อง" — แสดงห้องทั้งหมดจาก DB
- [x] Tab "สิทธิ์ผู้ใช้งาน" — แสดง UserProfile ทั้งหมด, เปลี่ยน role ผ่าน dropdown (submit ทันที)
- [x] Tab "ปิดปรับปรุง / วันหยุด" — เพิ่ม/ลบ BlackoutPeriod จาก DB

#### ✅ Module 9 — Email Notifications (Done)

- [x] SMTP configuration ผ่าน environment variables (Gmail-ready)
- [x] `booking/emails.py` — email helper functions แยกออกจาก views
- [x] Email เมื่อจองใหม่ (`notify_booking_created`) → แจ้ง Admin
- [x] Email เมื่ออนุมัติ (`notify_booking_approved`) → แจ้ง Lecturer
- [x] Email เมื่อปฏิเสธ (`notify_booking_rejected`) พร้อมเหตุผล → แจ้ง Lecturer
- [x] Email เมื่อยกเลิก (`notify_booking_cancelled`) → แจ้ง Admin
- [x] Email error ไม่ทำให้ระบบหลักพัง (log แทน raise)

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10–3.13 (แนะนำ 3.13 — Python 3.14 ยังไม่รองรับ Django 5.x อย่างเป็นทางการ)
- TU REST API Application-Key (register at [restapi.tu.ac.th](https://restapi.tu.ac.th))

### Installation

```bash
# Clone the repository
git clone https://github.com/Sarankorn2547/ECE-BookingSystem.git
cd ECE-BookingSystem

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment — สร้างไฟล์ .env
# (ดูตัวอย่างทั้งหมดได้ที่หัวข้อ Environment Variables ด้านล่าง)
echo TU_REST_API=your_application_key_here > .env

# Run migrations
python manage.py migrate

# Load room seed data (5 ห้องตาม SRS)
python manage.py loaddata booking/fixtures/rooms.json

# Start development server
python manage.py runserver
```

### Access

- **Login:** http://127.0.0.1:8000/login/
- **Dashboard:** http://127.0.0.1:8000/dashboard/
- **Admin Panel:** http://127.0.0.1:8000/admin/approvals/
- **Django Built-in Admin:** http://127.0.0.1:8000/django-admin/

### Dev Login (ทดสอบโดยไม่ต้องใช้ TU REST API)

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin1234` | ADMIN |
| `testuser` | `test1234` | LECTURER |

> หมายเหตุ: `psycopg2` ต้องไม่ติดตั้งอยู่ในเครื่อง หากติดตั้งไว้ Django จะพยายามต่อ PostgreSQL แทน SQLite  
> แก้ด้วย: `pip uninstall psycopg2`

---

## 🔐 Environment Variables

สร้างไฟล์ `.env` ที่ root ของโปรเจกต์ (อย่า commit ไฟล์นี้):

```env
# TU REST API (required)
TU_REST_API=your_tu_application_key_here

# Email — Gmail SMTP (required for Module 9)
EMAIL_HOST_USER=your_gmail@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
DEFAULT_FROM_EMAIL=your_gmail@gmail.com
ADMIN_EMAIL=admin_who_receives_notifications@gmail.com

# Optional overrides (ค่า default ใช้ได้เลย)
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.gmail.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
```

> **หมายเหตุ Gmail:** ต้องใช้ **App Password** (ไม่ใช่ password ปกติ)  
> ไปที่ Google Account → Security → 2-Step Verification → App passwords → สร้าง password ใหม่สำหรับ "Mail"

---

## 📁 Project Structure

```
ECE-BookingSystem/
├── ece_booking/              # Django project config
│   ├── settings.py           # Settings with .env, TU API, message tags
│   ├── urls.py               # Root URL routing
│   ├── wsgi.py
│   └── asgi.py
├── booking/                  # Main booking app
│   ├── views.py              # All views (auth, booking, calendar, admin)
│   ├── urls.py               # App URL routing (14 routes)
│   ├── models.py             # Room, Booking, BookingLog, BlackoutPeriod, UserProfile
│   ├── admin.py              # Django admin registration
│   ├── migrations/           # DB migrations
│   ├── templates/booking/    # HTML templates
│   │   ├── navbar.html             ✅ Role-aware (แสดง admin menu เฉพาะ Admin)
│   │   ├── login.html              ✅ Connected
│   │   ├── dashboard.html          ✅ Connected + recent bookings จาก DB
│   │   ├── booking-form.html       ✅ Connected
│   │   ├── my-bookings.html        ✅ Connected
│   │   ├── calendar.html           ✅ Connected + FullCalendar API
│   │   ├── admin-approvals.html    ✅ Connected (approve/reject จาก DB)
│   │   ├── admin-reports.html      ✅ Connected (สถิติจาก DB)
│   │   └── admin-system.html       ✅ Connected (rooms, users, blackouts จาก DB)
│   └── static/booking/
│       └── styles.css        # TU design system (red/gold theme)
├── .env                      # TU_REST_API key (not committed)
├── requirements.txt
├── manage.py
└── db.sqlite3
```

### URL Routes

| Method | URL | View | สิทธิ์ |
| ------ | --- | ---- | ------ |
| GET/POST | `/login/` | login_view | — |
| GET | `/logout/` | logout_view | Login |
| GET | `/dashboard/` | dashboard_view | Login |
| GET/POST | `/booking/` | booking_form_view | Login |
| GET | `/my-bookings/` | my_bookings_view | Login |
| POST | `/my-bookings/<id>/cancel/` | cancel_booking_view | Login |
| GET | `/calendar/` | calendar_view | Login |
| GET | `/api/calendar-events/` | calendar_events_api | Login |
| GET | `/admin/approvals/` | approval_queue_view | **Admin** |
| POST | `/admin/approvals/<id>/approve/` | approve_view | **Admin** |
| POST | `/admin/approvals/<id>/reject/` | reject_view | **Admin** |
| GET | `/admin/reports/` | admin_reports_view | **Admin** |
| GET | `/admin/reports/export/` | admin_reports_export_view | **Admin** |
| GET/POST | `/admin/system/` | admin_system_view | **Admin** |
| — | `/django-admin/` | Django built-in admin | Superuser |

---

## 📌 Notes

- ระบบรองรับเฉพาะบุคลากรภายในภาควิชาเท่านั้น (ไม่เปิดให้ภายนอก)
- ไม่มีระบบชำระเงินค่าห้อง
- ห้องทั้ง 5 ห้องเป็นข้อมูลเริ่มต้น แต่ Admin สามารถเพิ่ม/แก้ไขภายหลังได้
- การแจ้งเตือนให้ใช้อีเมล @gmail.com ในระหว่างพัฒนา

---

## 👥 External Systems

| System | Purpose |
| ------ | ------- |
| **TU REST API** | ยืนยันตัวตนผู้ใช้ (Authentication) |
| **Email Server (SMTP)** | ส่งอีเมลแจ้งเตือนและยืนยันการจอง |