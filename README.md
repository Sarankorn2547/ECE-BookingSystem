# ECE Room Booking System — CN334 HW1

## ข้อมูลกลุ่ม

| บทบาท | รหัสนักศึกษา | ชื่อ-สกุล |
|--------|-------------|-----------|
| หัวหน้า | 6610525013 | ณัฐรวี ช่วยวัง |
| สมาชิก | 6610545011 | ศรัญย์กร พงศ์อัศวชัย |
| สมาชิก | 6610625011 | ชุติกาญจน์ กีดคำ |
| สมาชิก | 6610625037 | อาแฟนดี่ย์ แวอุเซ็ง |
| สมาชิก | 6610685304 | รัชชานนท์ ม่วงวิเชียร |

## การแบ่งหน้าที่

| รหัสนักศึกษา | ชื่อ-สกุล | ความรับผิดชอบ |
|-------------|----------|--------------|
| 6610545011 | ศรัญย์กร พงศ์อัศวชัย | P1 — Team Lead / Backend: Authentication (TU REST API), UserProfile model, Session, Role assignment |
| 6610685304 | รัชชานนท์ ม่วงวิเชียร | P2 — Approval & Notify: Approve/Reject booking, Approval log, Email notifications (SMTP) |
| 6610525013 | ณัฐรวี ช่วยวัง | P3 — Frontend / Calendar: FullCalendar integration, Room filter, UI/UX, CSS |
| 6610625011 | ชุติกาญจน์ กีดคำ | P4 — Admin & Reports: Room model, BlackoutPeriod, Usage report, Utilization rate, Export CSV |
| 6610625037 | อาแฟนดี่ย์ แวอุเซ็ง | P5 — DevOps / QA: Base templates, Permission mixins, Context processors, Settings (base/prod) |

## สิ่งที่ต้องติดตั้งก่อนรันโปรเจกต์

- Python 3.10–3.13 (แนะนำ 3.13 — Python 3.14 ยังไม่รองรับ Django 5.x อย่างเป็นทางการ)
- TU REST API Application-Key (register at [restapi.tu.ac.th](https://restapi.tu.ac.th))
- Port 8000 ต้องว่างอยู่

## วิธีรันโปรเจกต์

```bash
# 1. Clone the repository
git clone https://github.com/Sarankorn2547/ECE-BookingSystem.git
cd ECE-BookingSystem

# 2. สร้าง virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# 3. ติดตั้ง dependencies
pip install -r requirements.txt

# 4. สร้างไฟล์ .env และใส่ Application-Key
echo TU_REST_API=your_application_key_here > .env

# 5. รัน migrations
python manage.py migrate

# 6. โหลดข้อมูลห้อง (5 ห้องตาม SRS)
python manage.py loaddata booking/fixtures/rooms.json

# 7. เปิดในเบราว์เซอร์
python manage.py runserver
# → http://localhost:8000
```

## บัญชีสำหรับทดสอบ

| บทบาท | Username | Password |
|--------|----------|----------|
| Admin | `admin` | `admin1234` |
| ผู้ใช้งาน | `testuser` | `test1234` |

> บัญชีเหล่านี้ใช้สำหรับ Dev Login (ไม่ต้องผ่าน TU REST API) — สร้างผ่าน Django built-in admin ที่ `/django-admin/`

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.x (Python) |
| Frontend | Bootstrap 5, Font Awesome |
| Database | SQLite (development) |
| Auth | TU REST API (`restapi.tu.ac.th`) |
| Fonts | Sarabun, Noto Sans Thai (Google Fonts) |

---

## 🔐 Environment Variables

สร้างไฟล์ `.env` ที่ root ของโปรเจกต์ (อย่า commit ไฟล์นี้):

```env
# TU REST API (required)
TU_REST_API=your_tu_application_key_here

# Email — Gmail SMTP (required for Email Notifications)
EMAIL_HOST_USER=your_gmail@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
DEFAULT_FROM_EMAIL=your_gmail@gmail.com
ADMIN_EMAIL=admin_who_receives_notifications@gmail.com
```

> **หมายเหตุ Gmail:** ต้องใช้ **App Password** (ไม่ใช่ password ปกติ)  
> ไปที่ Google Account → Security → 2-Step Verification → App passwords

---

## 📁 Project Structure

```
ECE-BookingSystem/
├── ece_booking/              # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── booking/                  # Main booking app
│   ├── views.py
│   ├── urls.py
│   ├── models.py             # Room, Booking, BookingLog, BlackoutPeriod, UserProfile
│   ├── emails.py             # Email notification helpers
│   ├── fixtures/rooms.json   # Room seed data
│   ├── templates/booking/
│   │   ├── navbar.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── booking-form.html
│   │   ├── my-bookings.html
│   │   ├── calendar.html
│   │   ├── admin-approvals.html
│   │   ├── admin-reports.html
│   │   └── admin-system.html
│   └── static/booking/
│       ├── styles.css
│       ├── motion.css
│       └── motion.js
├── .env                      # ไม่ commit
├── requirements.txt
├── manage.py
└── db.sqlite3
```

### URL Routes

| Method | URL | สิทธิ์ |
|--------|-----|--------|
| GET/POST | `/login/` | — |
| GET | `/logout/` | Login |
| GET | `/dashboard/` | Login |
| GET/POST | `/booking/` | Login |
| GET | `/my-bookings/` | Login |
| POST | `/my-bookings/<id>/cancel/` | Login |
| GET | `/calendar/` | Login |
| GET | `/api/calendar-events/` | Login |
| GET | `/admin/approvals/` | **Admin** |
| POST | `/admin/approvals/<id>/approve/` | **Admin** |
| POST | `/admin/approvals/<id>/reject/` | **Admin** |
| GET | `/admin/reports/` | **Admin** |
| GET | `/admin/reports/export/` | **Admin** |
| GET/POST | `/admin/system/` | **Admin** |

---

## 📋 SRS Reference
ระบบจองห้องประชุมและห้องเรียน ภาควิชาวิศวกรรมไฟฟ้าและคอมพิวเตอร์  
คณะวิศวกรรมศาสตร์ มหาวิทยาลัยธรรมศาสตร์
Based on [SRS Document v1.0](https://wachira.ece.engr.tu.ac.th/share/webapp/SRS_Room_Booking_std.html) — 7 เมษายน 2569

---

## ✅ Development Progress

### Use Cases from SRS

| Status | Use Case | Description |
|:------:|----------|-------------|
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
- [x] Quick action cards (จองห้อง, การจองของฉัน, ปฏิทินห้อง)
- [x] Recent bookings table — แสดง 5 รายการล่าสุดจาก DB

#### ✅ Module 3 — Booking Form (Done)

- [x] Room model (5 rooms), Booking model
- [x] Time slot conflict detection
- [x] Form validation
- [x] Save booking with Pending status

#### ✅ Module 4 — My Bookings (Done)

- [x] List user's bookings with status filters
- [x] Cancel booking functionality (UC-06)

#### ✅ Module 5 — Calendar (Done)

- [x] FullCalendar integration with booking data
- [x] Filter by room
- [x] Weekly/monthly view

#### ✅ Module 6 — Admin Approvals (Done)

- [x] แสดง PENDING bookings ทั้งหมดจาก DB พร้อม booker info
- [x] Approve — POST บันทึก approval_by, approval_at
- [x] Reject — POST พร้อมรับเหตุผลจาก modal form
- [x] บันทึก BookingLog ทุกการตัดสินใจ
- [x] `admin_required` decorator — ป้องกันด้วย UserProfile.role = ADMIN

#### ✅ Module 7 — Admin Reports (Done)

- [x] Summary cards: ยอดรวม, รออนุมัติ, อนุมัติแล้ว, ปฏิเสธ
- [x] ตารางการใช้งานแต่ละห้อง + Utilization rate
- [x] Filter by date range
- [x] Export CSV

#### ✅ Module 8 — Admin System Management (Done)

- [x] Tab จัดการห้อง — แสดงห้องทั้งหมดจาก DB
- [x] Tab สิทธิ์ผู้ใช้งาน — เปลี่ยน role ผ่าน dropdown
- [x] Tab ปิดปรับปรุง/วันหยุด — เพิ่ม/ลบ BlackoutPeriod จาก DB

#### ✅ Module 9 — Email Notifications (Done)

- [x] Email เมื่อจองใหม่ → แจ้ง Admin
- [x] Email เมื่ออนุมัติ → แจ้ง Lecturer
- [x] Email เมื่อปฏิเสธ พร้อมเหตุผล → แจ้ง Lecturer
- [x] Email เมื่อยกเลิก → แจ้ง Admin
- [x] Email error ไม่ทำให้ระบบหลักพัง (log แทน raise)
