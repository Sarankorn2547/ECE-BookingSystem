import json
import logging

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


def index_view(request):
    """Root redirect — send authenticated users to dashboard, others to login."""
    if request.user.is_authenticated:
        return redirect("booking:dashboard")
    return redirect("booking:login")


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Authenticate via TU REST API and create/update a local Django user."""
    if request.user.is_authenticated:
        return redirect("booking:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:
            messages.error(request, "กรุณากรอกชื่อผู้ใช้และรหัสผ่าน")
            return render(request, "booking/login.html")

        # Call TU REST API
        tu_api_key = settings.TU_REST_API_KEY
        try:
            response = requests.post(
                "https://restapi.tu.ac.th/api/v1/auth/Ad/verify",
                headers={
                    "Content-Type": "application/json",
                    "Application-Key": tu_api_key,
                },
                json={
                    "UserName": username,
                    "PassWord": password,
                },
                timeout=15,
            )

            if response.status_code == 200:
                data = response.json()
                status = data.get("status", False)

                if status:
                    # Extract user info from TU API response
                    display_name_th = data.get("displayname_th", "")
                    display_name_en = data.get("displayname_en", "")
                    email = data.get("email", "")
                    department = data.get("department", "")
                    faculty = data.get("faculty", "")
                    tu_status = data.get("type", "")  # e.g. student, employee

                    # Create or update Django user
                    user, created = User.objects.get_or_create(
                        username=username,
                        defaults={
                            "email": email,
                            "first_name": display_name_en[:30] if display_name_en else "",
                        },
                    )
                    if not created:
                        user.email = email
                        user.save()

                    # Store TU profile data in session
                    request.session["tu_profile"] = {
                        "username": username,
                        "display_name_th": display_name_th,
                        "display_name_en": display_name_en,
                        "email": email,
                        "department": department,
                        "faculty": faculty,
                        "tu_status": tu_status,
                    }

                    login(request, user)
                    messages.success(request, f"ยินดีต้อนรับ, {display_name_th or display_name_en or username}")
                    return redirect("booking:dashboard")
                else:
                    msg = data.get("message", "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
                    messages.error(request, msg)
            elif response.status_code == 400:
                # TU API returns 400 for invalid credentials
                messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            else:
                messages.error(request, "ไม่สามารถเชื่อมต่อระบบยืนยันตัวตนได้ กรุณาลองใหม่อีกครั้ง")
                logger.error("TU REST API returned status %s", response.status_code)

        except requests.exceptions.Timeout:
            messages.error(request, "การเชื่อมต่อ TU REST API หมดเวลา กรุณาลองใหม่อีกครั้ง")
        except requests.exceptions.ConnectionError:
            messages.error(request, "ไม่สามารถเชื่อมต่อ TU REST API ได้ กรุณาตรวจสอบอินเทอร์เน็ต")
        except Exception as e:
            messages.error(request, "เกิดข้อผิดพลาดในระบบ กรุณาลองใหม่อีกครั้ง")
            logger.exception("Unexpected error during TU auth: %s", e)

    return render(request, "booking/login.html")


def logout_view(request):
    """Clear session and log the user out."""
    logout(request)
    messages.info(request, "ออกจากระบบเรียบร้อยแล้ว")
    return redirect("booking:login")


@login_required
def dashboard_view(request):
    """Dashboard page — requires login."""
    tu_profile = request.session.get("tu_profile", {})
    context = {
        "tu_profile": tu_profile,
        "display_name": tu_profile.get("display_name_th") or tu_profile.get("display_name_en") or request.user.username,
        "department": tu_profile.get("department", ""),
        "faculty": tu_profile.get("faculty", ""),
        "tu_status": tu_profile.get("tu_status", ""),
        "active_page": "dashboard",
    }
    return render(request, "booking/dashboard.html", context)


@login_required
def booking_form_view(request):
    """Booking form page — requires login."""
    from .models import Room, Booking
    from django.utils.dateparse import parse_date, parse_time
    from django.db.models import Q

    if request.method == "POST":
        room_id = request.POST.get("room")
        start_date_str = request.POST.get("date")
        start_time_str = request.POST.get("start_time")
        end_time_str = request.POST.get("end_time")
        purpose_type = request.POST.get("purpose_type", "").strip()
        course_code = request.POST.get("course_code", "").strip()
        course_name = request.POST.get("course_name", "").strip()
        training_title = request.POST.get("training_title", "").strip()
        notes = request.POST.get("notes", "").strip()
        days_of_week_values = request.POST.getlist("days_of_week")
        full_pattern = request.POST.get("dayFull")

        if full_pattern:
            days_of_week_values = ["0", "1", "2", "3", "4", "5", "6"]

        if not all([room_id, start_date_str, start_time_str, end_time_str, purpose_type]):
            messages.error(request, "กรุณากรอกข้อมูลให้ครบถ้วน")
            return redirect("booking:booking_form")

        if purpose_type not in [Booking.PurposeType.COURSE, Booking.PurposeType.TRAINING]:
            messages.error(request, "ประเภทวัตถุประสงค์ไม่ถูกต้อง")
            return redirect("booking:booking_form")

        if purpose_type == Booking.PurposeType.COURSE and not (course_code or course_name):
            messages.error(request, "กรุณาใส่รหัสหรือชื่อวิชา")
            return redirect("booking:booking_form")

        if purpose_type == Booking.PurposeType.TRAINING and not training_title:
            messages.error(request, "กรุณาใส่หัวข้อการฝึกอบรม")
            return redirect("booking:booking_form")

        try:
            room = Room.objects.get(id=room_id)
            start_date = parse_date(start_date_str)
            end_date = start_date
            start_time = parse_time(start_time_str)
            end_time = parse_time(end_time_str)

            if not start_date or not start_time or not end_time:
                raise ValueError("Invalid date/time format")

            if start_time >= end_time:
                messages.error(request, "เวลาเริ่มต้นต้องน้อยกว่าเวลาสิ้นสุด")
                return redirect("booking:booking_form")

            conflict_filter = Q(start_time__lt=end_time, end_time__gt=start_time)
            conflicts = Booking.objects.filter(
                room=room,
                start_date=start_date,
                status__in=[Booking.BookingStatus.PENDING, Booking.BookingStatus.APPROVED]
            ).filter(conflict_filter)

            if conflicts.exists():
                messages.error(request, f"ห้อง {room.code} มีการใช้งานแล้วในช่วงเวลานี้")
                return redirect("booking:booking_form")

            days_of_week = []
            for value in days_of_week_values:
                if value.isdigit():
                    days_of_week.append(int(value))

            recurring_pattern = None
            if days_of_week:
                recurring_pattern = {
                    "type": "weekly",
                    "days_of_week": days_of_week,
                }

            Booking.objects.create(
                room=room,
                booker_id=request.session.get("tu_profile", {}).get("username", request.user.username),
                booker_name=request.session.get("tu_profile", {}).get("display_name_th", request.user.username),
                purpose_type=purpose_type,
                course_code=course_code or None,
                course_name=course_name or None,
                training_title=training_title or None,
                start_date=start_date,
                end_date=end_date,
                start_time=start_time,
                end_time=end_time,
                recurring_pattern=recurring_pattern,
                days_of_week=days_of_week or None,
                notes=notes,
                status=Booking.BookingStatus.PENDING,
            )

            messages.success(request, "ส่งคำขอจองเรียบร้อยแล้ว กรุณารอการอนุมัติ")
            return redirect("booking:dashboard")

        except Room.DoesNotExist:
            messages.error(request, "ห้องไม่ถูกต้อง")
        except ValueError as e:
            messages.error(request, f"ข้อมูลไม่ถูกต้อง: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected booking error: %s", e)
            messages.error(request, "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง")
            return redirect("booking:booking_form")

    rooms = Room.objects.all().order_by("code")
    tu_profile = request.session.get("tu_profile", {})
    context = {
        "rooms": rooms,
        "tu_profile": tu_profile,
        "display_name": tu_profile.get("display_name_th") or tu_profile.get("display_name_en") or request.user.username,
        "active_page": "booking",
    }
    return render(request, "booking/booking-form.html", context)


@login_required
def my_bookings_view(request):
    """My bookings page — requires login."""
    tu_profile = request.session.get("tu_profile", {})
    context = {
        "tu_profile": tu_profile,
        "display_name": tu_profile.get("display_name_th") or tu_profile.get("display_name_en") or request.user.username,
        "active_page": "my_bookings",
    }
    return render(request, "booking/my-bookings.html", context)


@login_required
def calendar_view(request):
    """Calendar page — requires login."""
    tu_profile = request.session.get("tu_profile", {})
    context = {
        "tu_profile": tu_profile,
        "display_name": tu_profile.get("display_name_th") or tu_profile.get("display_name_en") or request.user.username,
        "active_page": "calendar",
    }
    return render(request, "booking/calendar.html", context)
