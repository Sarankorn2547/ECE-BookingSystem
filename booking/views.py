import json
import logging
from functools import wraps

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Booking, BlackoutPeriod, BookingLog, Room, UserProfile
from .emails import (
    notify_booking_created,
    notify_booking_approved,
    notify_booking_rejected,
    notify_booking_cancelled,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_admin(request):
    try:
        profile = UserProfile.objects.get(tu_uid=request.user.username)
        return profile.role == UserProfile.Role.ADMIN
    except UserProfile.DoesNotExist:
        return False


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not _is_admin(request):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def _base_context(request):
    """Common context variables shared by all authenticated views."""
    tu_profile = request.session.get("tu_profile", {})
    return {
        "tu_profile": tu_profile,
        "display_name": (
            tu_profile.get("display_name_th")
            or tu_profile.get("display_name_en")
            or request.user.username
        ),
        "department": tu_profile.get("department", ""),
        "faculty": tu_profile.get("faculty", ""),
        "tu_status": tu_profile.get("tu_status", ""),
        "is_admin": _is_admin(request),
    }


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def index_view(request):
    if request.user.is_authenticated:
        return redirect("booking:dashboard")
    return redirect("booking:login")


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("booking:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:
            messages.error(request, "กรุณากรอกชื่อผู้ใช้และรหัสผ่าน")
            return render(request, "booking/login.html")

        tu_api_key = settings.TU_REST_API_KEY
        try:
            response = requests.post(
                "https://restapi.tu.ac.th/api/v1/auth/Ad/verify",
                headers={
                    "Content-Type": "application/json",
                    "Application-Key": tu_api_key,
                },
                json={"UserName": username, "PassWord": password},
                timeout=15,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status", False):
                    display_name_th = data.get("displayname_th", "")
                    display_name_en = data.get("displayname_en", "")
                    email = data.get("email", "")
                    department = data.get("department", "")
                    faculty = data.get("faculty", "")
                    tu_status = data.get("type", "")

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
                    messages.error(request, data.get("message", "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"))
            elif response.status_code == 400:
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
    logout(request)
    messages.info(request, "ออกจากระบบเรียบร้อยแล้ว")
    return redirect("booking:login")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard_view(request):
    booker_id = request.session.get("tu_profile", {}).get("username", request.user.username)
    recent_bookings = (
        Booking.objects.filter(booker_id=booker_id)
        .exclude(status=Booking.Status.CANCELLED)
        .select_related("room")
        .order_by("-created_at")[:5]
    )
    context = {
        **_base_context(request),
        "active_page": "dashboard",
        "recent_bookings": recent_bookings,
    }
    return render(request, "booking/dashboard.html", context)


# ---------------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------------

@login_required
def booking_form_view(request):
    from django.utils.dateparse import parse_date, parse_time

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
                status__in=[Booking.Status.PENDING, Booking.Status.APPROVED],
            ).filter(conflict_filter)

            if conflicts.exists():
                messages.error(request, f"ห้อง {room.code} มีการใช้งานแล้วในช่วงเวลานี้")
                return redirect("booking:booking_form")

            days_of_week = [int(v) for v in days_of_week_values if v.isdigit()]
            recurring_pattern = {"type": "weekly", "days_of_week": days_of_week} if days_of_week else None

            tu_profile = request.session.get("tu_profile", {})
            new_booking = Booking.objects.create(
                room=room,
                booker_id=tu_profile.get("username", request.user.username),
                booker_name=tu_profile.get("display_name_th", request.user.username),
                purpose_type=purpose_type,
                course_code=course_code or None,
                course_name=course_name or None,
                training_title=training_title or None,
                start_date=start_date,
                end_date=start_date,
                start_time=start_time,
                end_time=end_time,
                recurring_pattern=recurring_pattern,
                days_of_week=days_of_week or None,
                notes=notes,
                status=Booking.Status.PENDING,
            )
            notify_booking_created(new_booking)
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

    context = {
        **_base_context(request),
        "rooms": Room.objects.all().order_by("code"),
        "active_page": "booking",
    }
    return render(request, "booking/booking-form.html", context)


@login_required
def my_bookings_view(request):
    booker_id = request.session.get("tu_profile", {}).get("username", request.user.username)
    status_filter = request.GET.get("status", "")
    search_query = request.GET.get("q", "").strip()

    bookings = (
        Booking.objects.filter(booker_id=booker_id)
        .exclude(status=Booking.Status.CANCELLED)
        .select_related("room")
    )

    valid_statuses = [s.value for s in Booking.Status]
    if status_filter in valid_statuses:
        bookings = bookings.filter(status=status_filter)

    if search_query:
        bookings = bookings.filter(
            Q(room__code__icontains=search_query)
            | Q(course_code__icontains=search_query)
            | Q(course_name__icontains=search_query)
            | Q(training_title__icontains=search_query)
        )

    bookings = bookings.order_by("-created_at")
    context = {
        **_base_context(request),
        "active_page": "my_bookings",
        "bookings": bookings,
        "status_filter": status_filter,
        "search_query": search_query,
    }
    return render(request, "booking/my-bookings.html", context)


@login_required
@require_http_methods(["POST"])
def cancel_booking_view(request, booking_id):
    booker_id = request.session.get("tu_profile", {}).get("username", request.user.username)
    try:
        booking = Booking.objects.get(id=booking_id, booker_id=booker_id)
    except Booking.DoesNotExist:
        messages.error(request, "ไม่พบรายการจองนี้")
        return redirect("booking:my_bookings")

    if booking.status not in [Booking.Status.PENDING, Booking.Status.APPROVED]:
        messages.error(request, "ไม่สามารถยกเลิกการจองที่มีสถานะนี้ได้")
        return redirect("booking:my_bookings")

    booking.status = Booking.Status.CANCELLED
    booking.save()
    BookingLog.objects.create(booking=booking, action="CANCELLED", actor=booker_id)
    notify_booking_cancelled(booking)
    messages.success(request, "ยกเลิกการจองเรียบร้อยแล้ว")
    return redirect("booking:my_bookings")


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

@login_required
def calendar_view(request):
    context = {
        **_base_context(request),
        "active_page": "calendar",
        "rooms": Room.objects.all().order_by("code"),
    }
    return render(request, "booking/calendar.html", context)


@login_required
def calendar_events_api(request):
    from datetime import datetime, date, timedelta

    start_str = request.GET.get("start", "")
    end_str = request.GET.get("end", "")
    room_code = request.GET.get("room", "").strip()

    try:
        range_start = datetime.fromisoformat(start_str[:10]).date() if start_str else date.today()
        range_end = datetime.fromisoformat(end_str[:10]).date() if end_str else date.today() + timedelta(days=30)
    except (ValueError, AttributeError):
        range_start = date.today()
        range_end = date.today() + timedelta(days=30)

    bookings = Booking.objects.filter(
        status__in=[Booking.Status.PENDING, Booking.Status.APPROVED],
        start_date__lte=range_end,
        end_date__gte=range_start,
    ).select_related("room")

    if room_code:
        bookings = bookings.filter(room__code=room_code)

    events = []
    for booking in bookings:
        is_approved = booking.status == Booking.Status.APPROVED
        bg = "#6FDFFE" if is_approved else "#4A2D8C"
        border = "#4dbcd4" if is_approved else "#4A2D8C"
        text = "#1a1a2e" if is_approved else "#ffffff"

        if booking.purpose_type == Booking.PurposeType.COURSE:
            parts = [p for p in [booking.course_code, booking.course_name] if p]
            label = " ".join(parts) or "การเรียนการสอน"
        else:
            label = booking.training_title or "การฝึกอบรม"

        title = f"{label} ({booking.room.code})"
        start_t = booking.start_time.strftime("%H:%M:%S")
        end_t = booking.end_time.strftime("%H:%M:%S")

        days_of_week = booking.days_of_week
        effective_start = max(booking.start_date, range_start)
        effective_end = min(booking.end_date, range_end)

        if days_of_week:
            from datetime import timedelta as td
            current = effective_start
            while current <= effective_end:
                if current.weekday() in days_of_week:
                    events.append({
                        "title": title,
                        "start": f"{current.isoformat()}T{start_t}",
                        "end": f"{current.isoformat()}T{end_t}",
                        "backgroundColor": bg,
                        "borderColor": border,
                        "textColor": text,
                    })
                current += td(days=1)
        else:
            events.append({
                "title": title,
                "start": f"{booking.start_date.isoformat()}T{start_t}",
                "end": f"{booking.start_date.isoformat()}T{end_t}",
                "backgroundColor": bg,
                "borderColor": border,
                "textColor": text,
            })

    return JsonResponse(events, safe=False)


# ---------------------------------------------------------------------------
# Admin — Approvals
# ---------------------------------------------------------------------------

@login_required
@admin_required
def approval_queue_view(request):
    pending_bookings = (
        Booking.objects.filter(status=Booking.Status.PENDING)
        .select_related("room")
        .order_by("created_at")
    )
    context = {
        **_base_context(request),
        "active_page": "admin_approvals",
        "bookings": pending_bookings,
        "pending_count": pending_bookings.count(),
    }
    return render(request, "booking/admin-approvals.html", context)


@login_required
@admin_required
@require_http_methods(["POST"])
def approve_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, status=Booking.Status.PENDING)
    booking.status = Booking.Status.APPROVED
    booking.approval_by = request.user.username
    booking.approval_at = timezone.now()
    booking.save()
    BookingLog.objects.create(booking=booking, action="APPROVED", actor=request.user.username)
    notify_booking_approved(booking)
    messages.success(request, f"อนุมัติการจองของ {booking.booker_name or booking.booker_id} เรียบร้อยแล้ว")
    return redirect("booking:approval_queue")


@login_required
@admin_required
@require_http_methods(["POST"])
def reject_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, status=Booking.Status.PENDING)
    reason = request.POST.get("reason", "").strip()
    booking.status = Booking.Status.REJECTED
    booking.approval_by = request.user.username
    booking.approval_at = timezone.now()
    booking.save()
    BookingLog.objects.create(
        booking=booking,
        action="REJECTED",
        actor=request.user.username,
        metadata={"reason": reason},
    )
    notify_booking_rejected(booking, reason)
    messages.success(request, f"ปฏิเสธการจองของ {booking.booker_name or booking.booker_id} เรียบร้อยแล้ว")
    return redirect("booking:approval_queue")


# ---------------------------------------------------------------------------
# Admin — Reports
# ---------------------------------------------------------------------------

@login_required
@admin_required
def admin_reports_view(request):
    status_counts = {
        item["status"]: item["count"]
        for item in Booking.objects.values("status").annotate(count=Count("id"))
    }
    room_usage = (
        Booking.objects.filter(status=Booking.Status.APPROVED)
        .values("room__code")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    total_bookings = Booking.objects.count()
    context = {
        **_base_context(request),
        "active_page": "admin_reports",
        "status_counts": status_counts,
        "room_usage": room_usage,
        "total_bookings": total_bookings,
        "pending_count": status_counts.get("PENDING", 0),
        "approved_count": status_counts.get("APPROVED", 0),
        "rejected_count": status_counts.get("REJECTED", 0),
        "cancelled_count": status_counts.get("CANCELLED", 0),
    }
    return render(request, "booking/admin-reports.html", context)


# ---------------------------------------------------------------------------
# Admin — System Management
# ---------------------------------------------------------------------------

@login_required
@admin_required
def admin_system_view(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_blackout":
            title = request.POST.get("title", "").strip()
            start_date = request.POST.get("start_date")
            end_date = request.POST.get("end_date")
            room_id = request.POST.get("room_id") or None

            if not title or not start_date or not end_date:
                messages.error(request, "กรุณากรอกข้อมูลให้ครบถ้วน")
            else:
                room = Room.objects.get(id=room_id) if room_id else None
                BlackoutPeriod.objects.create(
                    title=title,
                    start_date=start_date,
                    end_date=end_date,
                    room=room,
                    created_by=request.user.username,
                )
                messages.success(request, f"เพิ่มช่วงเวลาปิด '{title}' เรียบร้อยแล้ว")
            return redirect("booking:admin_system")

        if action == "delete_blackout":
            blackout_id = request.POST.get("blackout_id")
            BlackoutPeriod.objects.filter(id=blackout_id).delete()
            messages.success(request, "ลบช่วงเวลาปิดเรียบร้อยแล้ว")
            return redirect("booking:admin_system")

        if action == "set_role":
            tu_uid = request.POST.get("tu_uid", "").strip()
            role = request.POST.get("role", "").strip()
            if tu_uid and role in [UserProfile.Role.ADMIN, UserProfile.Role.LECTURER, ""]:
                UserProfile.objects.update_or_create(
                    tu_uid=tu_uid,
                    defaults={"username": tu_uid, "role": role},
                )
                messages.success(request, f"อัปเดตสิทธิ์ผู้ใช้ {tu_uid} เรียบร้อยแล้ว")
            return redirect("booking:admin_system")

    rooms = Room.objects.all().order_by("code")
    blackouts = BlackoutPeriod.objects.all().select_related("room").order_by("start_date")
    user_profiles = UserProfile.objects.all().order_by("username")
    context = {
        **_base_context(request),
        "active_page": "admin_system",
        "rooms": rooms,
        "blackouts": blackouts,
        "user_profiles": user_profiles,
    }
    return render(request, "booking/admin-system.html", context)
