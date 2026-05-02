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
| 🔲 Template Only | **UC-03: อนุมัติ/ปฏิเสธการจอง** | หน้าอนุมัติ (มี template แล้ว ยังไม่มี backend) |
| 🔲 Template Only | **UC-04: ดูปฏิทินห้องว่าง** | ปฏิทินห้อง (มี template แล้ว ยังไม่มี backend) |
| 🔲 Template Only | **UC-05: ดูรายงานสถิติ** | รายงานการใช้ห้อง (มี template แล้ว ยังไม่มี backend) |
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
- [x] Sidebar navigation (all links present)
- [x] Top header with user name and department
- [x] Quick action cards (จองห้อง, การจองของฉัน, ปฏิทินห้อง)
- [x] Recent bookings table (empty state)

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

#### 🔲 Module 5 — Calendar (Template Only)

- [x] Template: `calendar.html`
- [ ] Django view and URL route
- [ ] FullCalendar integration with booking data
- [ ] Filter by room
- [ ] Weekly/monthly view

#### 🔲 Module 6 — Admin Approvals (Template Only)

- [x] Template: `admin-approvals.html`
- [ ] Django view and URL route
- [ ] List pending bookings
- [ ] Approve / Reject with reason
- [ ] Update booking status
- [ ] Admin role check

#### 🔲 Module 7 — Admin Reports (Template Only)

- [x] Template: `admin-reports.html`
- [ ] Django view and URL route
- [ ] Usage statistics per room
- [ ] Utilization rate
- [ ] Filter by date range and category

#### 🔲 Module 8 — Admin System Management (Template Only)

- [x] Template: `admin-system.html`
- [ ] Django view and URL route
- [ ] Add/Edit/Delete rooms
- [ ] User management
- [ ] System settings

#### 🔲 Module 9 — Email Notifications (Not Started)

- [ ] SMTP configuration (Gmail)
- [ ] Email on booking created → Admin
- [ ] Email on booking approved/rejected → Lecturer
- [ ] Email on booking cancelled → Admin

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
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

# Configure environment
# Create .env file with your TU REST API key
echo TU_REST_API=your_application_key_here > .env

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

### Access

- **Login:** http://127.0.0.1:8000/login/
- **Dashboard:** http://127.0.0.1:8000/dashboard/
- **Admin Panel:** http://127.0.0.1:8000/admin/

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
│   ├── views.py              # Login, Logout, Dashboard views
│   ├── urls.py               # App URL routing
│   ├── models.py             # (empty — models TBD)
│   ├── templates/booking/    # HTML templates
│   │   ├── login.html              ✅ Connected
│   │   ├── dashboard.html          ✅ Connected
│   │   ├── booking-form.html       🔲 Template only
│   │   ├── my-bookings.html        🔲 Template only
│   │   ├── calendar.html           🔲 Template only
│   │   ├── admin-approvals.html    🔲 Template only
│   │   ├── admin-reports.html      🔲 Template only
│   │   └── admin-system.html       🔲 Template only
│   └── static/booking/
│       └── styles.css        # TU design system (red/gold theme)
├── .env                      # TU_REST_API key (not committed)
├── requirements.txt
├── manage.py
└── db.sqlite3
```

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