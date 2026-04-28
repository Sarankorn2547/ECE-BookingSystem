import json
import logging

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
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
    }
    return render(request, "booking/dashboard.html", context)


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

@login_required
def profile_view(request):
    tu_profile = request.session.get("tu_profile", {})
    return render(request, "booking/profile.html", {"tu_profile": tu_profile})


@login_required
def user_list_view(request):
    # TODO: admin only — list users + roles
    return render(request, "booking/admin-users.html")


@login_required
def set_user_role_view(request, pk):
    # TODO: POST only — update UserProfile.role
    return redirect("booking:user-list")


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

@login_required
def room_list_view(request):
    # TODO: admin only
    return render(request, "booking/room-list.html")


@login_required
def room_add_view(request):
    return render(request, "booking/room-form.html")


@login_required
def room_edit_view(request, pk):
    return render(request, "booking/room-form.html")


@login_required
def blackout_view(request):
    return render(request, "booking/blackout.html")


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

@login_required
def booking_list_view(request):
    return render(request, "booking/my-bookings.html")


@login_required
def booking_create_view(request):
    return render(request, "booking/booking-form.html")


@login_required
def booking_detail_view(request, pk):
    return render(request, "booking/booking-detail.html")


@login_required
def booking_cancel_view(request, pk):
    # TODO: POST only — cancel if before start_date
    return redirect("booking:booking-list")


@login_required
def recurring_booking_view(request):
    return render(request, "booking/booking-recurring.html")


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------

@login_required
def approval_queue_view(request):
    return render(request, "booking/admin-approvals.html")


@login_required
def approve_view(request, pk):
    # TODO: POST only — approve + email notify
    return redirect("booking:approval-queue")


@login_required
def reject_view(request, pk):
    # TODO: POST only — reject with reason + email notify
    return redirect("booking:approval-queue")


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

@login_required
def calendar_view(request):
    return render(request, "booking/calendar.html")


@login_required
def calendar_monthly_view(request):
    return render(request, "booking/calendar.html", {"view_mode": "monthly"})


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@login_required
def reports_view(request):
    return render(request, "booking/admin-reports.html")


@login_required
def utilization_view(request):
    return render(request, "booking/admin-reports.html", {"report_type": "utilization"})


@login_required
def export_csv_view(request):
    # TODO: stream CSV response
    from django.http import HttpResponse
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="bookings.csv"'
    return response


# ---------------------------------------------------------------------------
# Teams Bot NLP API
# ---------------------------------------------------------------------------

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import re as _re

@csrf_exempt
@require_POST
def nlp_parse_view(request):
    """Teams Bot outgoing webhook endpoint — proxied from room_booking_nlp."""
    import json as _json
    try:
        data = _json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    text = data.get("text", "")
    from_data = data.get("from", {})
    username = from_data.get("name", "Unknown User")

    clean_text = _re.sub(r"<at>.*?</at>", "", text)
    clean_text = _re.sub(r"RoomBot", "", clean_text, flags=_re.IGNORECASE)
    clean_text = _re.sub(r"<[^>]+>", "", clean_text)
    clean_text = clean_text.replace("&nbsp;", " ").strip()

    if not clean_text:
        return JsonResponse({"error": "No text"}, status=400)

    # TODO: wire up NLP service and booking logic (ported from room_booking_nlp)
    return JsonResponse({"type": "message", "text": f"🚧 NLP endpoint พร้อมแล้ว (ยังไม่ได้ต่อ logic): {clean_text}"})
