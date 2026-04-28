# คู่มือนักพัฒนา — ECE Room Booking System

## 📐 โครงสร้างระบบ

```
ECE-BookingSystem/          ← repo หลัก (GitHub: Sarankorn2547/ECE-BookingSystem)
├── booking/                ← Django app หลัก (UI, approval, calendar)
├── ece_booking/            ← Django project settings
├── teams-bot/              ← Teams Bot NLP (อยู่ใน repo เดียวกัน)
│   ├── bookings/           ← models, views, nlp_service
│   └── docker-compose.yml  ← รัน web + caddy
├── docker-compose.yml      ← รัน ECE web (port 8001)
└── .env                    ← secrets (ไม่อยู่ใน git)
```

---

## 🖥️ Server / Infrastructure

| รายการ | ค่า |
|--------|-----|
| VPS IP | `217.216.108.16` |
| SSH Port | `8822` |
| SSH User | `root` |
| Domain | `booking.vivaclubs.site` |
| Portainer | `portainer.vivaclubs.site` |
| ECE Web Port | `8001` (→ Caddy) |
| Teams Bot Port | `8000` (ภายใน container) |
| Database | PostgreSQL `server-db-1` container |

---

## 🗄️ Database

ทั้งสองระบบใช้ PostgreSQL container ชื่อ `server-db-1` ร่วมกัน

| รายการ | ค่า |
|--------|-----|
| Host | `217.216.108.16` |
| Port | `5432` |
| Database (ECE Web) | `ece_booking` |
| Database (Teams Bot) | `room_booking_db` |
| User | `ece_admin` |
| Password | *(ขอจากทีมผ่าน LINE)* |

### เชื่อมต่อ DB สำหรับพัฒนา (Local)

ใช้ DBeaver / TablePlus / psql เชื่อมตรงได้เลย:

```
Host:     217.216.108.16
Port:     5432
Database: ece_booking
Username: ece_admin
Password: <ขอจากทีม>
```

> พอร์ต 5432 เปิด firewall แล้ว ไม่ต้อง SSH tunnel

---

## 🔐 Environment Variables

### ECE Web (`ECE-BookingSystem/.env`)

```env
DEBUG=False
DJANGO_SECRET_KEY=<strong-secret-key>
ALLOWED_HOSTS=localhost 127.0.0.1 booking.vivaclubs.site

POSTGRES_DB=ece_booking
POSTGRES_USER=ece_admin
POSTGRES_PASSWORD=<password>
SQL_HOST=server-db-1
SQL_PORT=5432

DOMAIN=booking.vivaclubs.site
TU_REST_API=<TU-REST-API-key>
```

### Teams Bot (`teams-bot/.env` บน VPS ที่ `/root/room_booking_nlp/.env`)

```env
TYPHOON_API_KEY=<typhoon-api-key>
SECRET_KEY=<django-secret>
DEBUG=False
ALLOWED_HOSTS=*

DB_NAME=room_booking_db
DB_USER=ece_admin
DB_PASSWORD=<password>
DB_HOST=server-db-1
DB_PORT=5432
```

> **.env ไม่อยู่ใน git** — ขอไฟล์จากทีมโดยตรง

---

## 💻 พัฒนาบน Local

### 1. Clone repo

```bash
git clone https://github.com/Sarankorn2547/ECE-BookingSystem.git
cd ECE-BookingSystem
git checkout develop   # branch สำหรับพัฒนา
```

### 2. สร้าง virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
# หรือ
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 3. ตั้งค่า .env

Copy ตัวอย่างจากด้านบนแล้วแก้ค่าให้ตรง แล้ว save เป็น `.env` ใน root ของ project

### 4. รัน migrate และ server

```bash
python manage.py migrate
python manage.py runserver
```

เปิด browser ที่ `http://localhost:8000`

---

## 🌿 Git Workflow

```
main     ← production (อย่า push ตรงนี้)
deploy   ← auto-deploy ไป VPS ผ่าน GitHub Actions
develop  ← branch สำหรับพัฒนา (ทุกคน branch มาจากนี้)
```

### ขั้นตอนการทำงาน

```bash
# 1. ดึงโค้ดล่าสุด
git checkout develop
git pull origin develop

# 2. สร้าง branch ใหม่สำหรับ feature
git checkout -b feature/ชื่อ-feature

# 3. แก้ไขโค้ด แล้ว commit
git add .
git commit -m "feat: อธิบายสิ่งที่ทำ"

# 4. Push และสร้าง Pull Request
git push origin feature/ชื่อ-feature
# เปิด PR บน GitHub จาก feature/xxx → develop
```

> **อย่า push ตรงไปที่ `deploy` หรือ `main`** — ใช้ PR เสมอ

---

## 🚀 Deploy ขึ้น Production

### วิธีที่ 1: GitHub Actions (อัตโนมัติ)

เมื่อ merge PR เข้า `deploy` branch → GitHub Actions จะ deploy ให้อัตโนมัติ

ต้องตั้งค่า GitHub Secrets ก่อน (Settings → Secrets → Actions):

| Secret | ค่า |
|--------|-----|
| `VPS_HOST` | `217.216.108.16` |
| `VPS_PORT` | `8822` |
| `VPS_USER` | `root` |
| `VPS_SSH_KEY` | Private key (ขอจาก admin) |

### วิธีที่ 2: Manual Deploy (SSH)

```bash
# SSH เข้า VPS
ssh -p 8822 root@217.216.108.16

# ECE Web
cd /root/ece-booking
git pull origin deploy
docker compose up -d --build web
docker compose exec -T web python manage.py migrate --noinput
docker compose exec -T web python manage.py collectstatic --noinput

# Teams Bot (ถ้าแก้ไข teams-bot/)
cp /root/ece-booking/teams-bot/bookings/views.py /root/room_booking_nlp/bookings/views.py
cp /root/ece-booking/teams-bot/bookings/nlp_service.py /root/room_booking_nlp/bookings/nlp_service.py
cd /root/room_booking_nlp
docker compose restart web
```

---

## 🐳 Docker Containers บน VPS

| Container | Stack | Port | หน้าที่ |
|-----------|-------|------|--------|
| `ece-web` | ece-bookingsystem | 8000 (internal) | ECE Web UI (Django) |
| `ece-nginx` | ece-bookingsystem | 8081→80 | Web Entry Point (Nginx) |
| `ece-db` | ece-bookingsystem | 5432 | ECE PostgreSQL 16 |
| `ece-dozzle` | ece-bookingsystem | 8888→8080 | Log Viewer (All Projects) |
| `room_booking_nlp-web-1` | room_booking_nlp | 8000 (internal) | Teams Bot NLP (Django) |
| `room_booking_nlp-caddy-1` | room_booking_nlp | 80, 443 | Teams Bot HTTPS Entry |
| `server-db-1` | server | 5432 | Shared PostgreSQL 15 |
| `portainer` | - | 9000 | Container Management |

ดู container ทั้งหมดผ่าน Portainer: `portainer.vivaclubs.site`

## 🚀 Auto Deployment (GitHub Actions) [STATUS: ACTIVE ✅]

ระบบจะทำการ Deploy อัตโนมัติทุกครั้งที่มีการ Push โค้ดขึ้นไปที่ branch `deploy`

### วิธีตั้งค่าครั้งแรก:
1.  **นำ Private Key ไปใส่ใน GitHub:**
    - ไปที่ Repository ใน GitHub -> **Settings** -> **Secrets and variables** -> **Actions**
    - กด **New repository secret**
    - ตั้งชื่อว่า `SSH_PRIVATE_KEY`
    - ก๊อปปี้เนื้อหาในไฟล์ SSH Private Key ของคุณ (ไฟล์ที่ปกติใช้ Login VPS) มาวางในช่อง Value
2.  **เรียบร้อย!** ครั้งต่อไปที่ใคร Push ขึ้น `deploy` ระบบจะ SSH เข้าไปสั่ง `git pull` และ `docker compose up -d --build` ให้เองที่เครื่อง VPS ครับ

---

## 🔍 Debug / Logs

```bash
# ดู log Teams Bot
ssh -p 8822 root@217.216.108.16
cd /root/room_booking_nlp
docker compose logs -f web

# ดู log ECE Web
cd /root/ece-booking
docker compose logs -f web

# ดู log Caddy
cd /root/room_booking_nlp
docker compose logs -f caddy
```

---

## 📞 ติดต่อ

- **Repository**: https://github.com/Sarankorn2547/ECE-BookingSystem
- **Portainer**: https://portainer.vivaclubs.site
- **Production**: https://booking.vivaclubs.site
