"""
Email notification helpers for the booking system.

Triggered by:
- booking_created  → notify Admin
- booking_approved → notify Booker (Lecturer)
- booking_rejected → notify Booker (Lecturer) with reason
- booking_cancelled → notify Admin
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _send(subject: str, body: str, recipient: str) -> None:
    """Send a single email, swallowing errors so they never break the main flow."""
    if not recipient:
        logger.warning("Email skipped — no recipient address for subject: %s", subject)
        return
    if not settings.EMAIL_HOST_USER:
        logger.warning("Email skipped — EMAIL_HOST_USER not configured")
        return
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        logger.info("Email sent to %s | %s", recipient, subject)
    except Exception as exc:
        logger.error("Failed to send email to %s | %s | %s", recipient, subject, exc)


# ---------------------------------------------------------------------------
# Public helpers — one function per event
# ---------------------------------------------------------------------------

def notify_booking_created(booking) -> None:
    """Notify Admin when a new booking request is submitted."""
    admin_email = settings.ADMIN_EMAIL
    if not admin_email:
        return

    if booking.purpose_type == "COURSE":
        detail = f"วิชา: {booking.course_code or ''} {booking.course_name or ''}".strip()
    else:
        detail = f"หัวข้อ: {booking.training_title or ''}"

    subject = f"[จองห้อง] คำขอใหม่จาก {booking.booker_name or booking.booker_id}"
    body = (
        f"มีคำขอจองห้องใหม่รออนุมัติ\n\n"
        f"ผู้จอง  : {booking.booker_name or booking.booker_id} ({booking.booker_id})\n"
        f"ห้อง    : {booking.room.code}\n"
        f"{_format_schedule(booking)}\n"
        f"{detail}\n"
        f"หมายเหตุ: {booking.notes or '-'}\n\n"
        f"กรุณาเข้าสู่ระบบเพื่ออนุมัติหรือปฏิเสธคำขอ"
    )
    _send(subject, body, admin_email)


def notify_booking_approved(booking) -> None:
    """Notify Booker (Lecturer) when their booking is approved."""
    booker_email = _get_booker_email(booking)
    if not booker_email:
        return

    subject = f"[จองห้อง] อนุมัติแล้ว — {booking.room.code} วันที่ {booking.start_date.strftime('%d/%m/%Y')}"
    body = (
        f"การจองของคุณได้รับการอนุมัติแล้ว\n\n"
        f"ห้อง      : {booking.room.code}\n"
        f"{_format_schedule(booking)}\n"
        f"อนุมัติโดย: {booking.approval_by}\n\n"
        f"ขอบคุณที่ใช้บริการ ระบบจองห้อง ECE"
    )
    _send(subject, body, booker_email)


def notify_booking_rejected(booking, reason: str = "") -> None:
    """Notify Booker (Lecturer) when their booking is rejected."""
    booker_email = _get_booker_email(booking)
    if not booker_email:
        return

    subject = f"[จองห้อง] ปฏิเสธคำขอ — {booking.room.code} วันที่ {booking.start_date.strftime('%d/%m/%Y')}"
    body = (
        f"ขออภัย คำขอจองห้องของคุณถูกปฏิเสธ\n\n"
        f"ห้อง   : {booking.room.code}\n"
        f"{_format_schedule(booking)}\n"
        f"เหตุผล : {reason or 'ไม่ได้ระบุเหตุผล'}\n\n"
        f"หากมีข้อสงสัยกรุณาติดต่อเจ้าหน้าที่ภาควิชา"
    )
    _send(subject, body, booker_email)


def notify_booking_cancelled(booking) -> None:
    """Notify Admin when a booking is cancelled by the booker."""
    admin_email = settings.ADMIN_EMAIL
    if not admin_email:
        return

    subject = f"[จองห้อง] ยกเลิกแล้ว — {booking.room.code} วันที่ {booking.start_date.strftime('%d/%m/%Y')}"
    body = (
        f"การจองต่อไปนี้ถูกยกเลิกโดยผู้จอง\n\n"
        f"ผู้จอง  : {booking.booker_name or booking.booker_id} ({booking.booker_id})\n"
        f"ห้อง    : {booking.room.code}\n"
        f"{_format_schedule(booking)}\n"
    )
    _send(subject, body, admin_email)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DAY_NAMES = {0: 'อาทิตย์', 1: 'จันทร์', 2: 'อังคาร', 3: 'พุธ', 4: 'พฤหัสบดี', 5: 'ศุกร์', 6: 'เสาร์'}


def _format_schedule(booking) -> str:
    """Return a human-readable schedule string for the booking.

    Single-day  → "วันที่  : 28/05/2026\nเวลา    : 09:00 - 12:00"
    Recurring   → "ช่วงวันที่: 01/05/2026 - 30/06/2026
                   ทุกวัน   : จันทร์, พุธ, ศุกร์
                   เวลา     : 09:00 - 12:00"
    """
    time_str = f"{booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}"
    if booking.days_of_week and booking.start_date != booking.end_date:
        days = sorted(booking.days_of_week)
        days_str = ', '.join(_DAY_NAMES.get(d, str(d)) for d in days)
        return (
            f"ช่วงวันที่: {booking.start_date.strftime('%d/%m/%Y')} - {booking.end_date.strftime('%d/%m/%Y')}\n"
            f"ทุกวัน   : {days_str}\n"
            f"เวลา     : {time_str}"
        )
    return (
        f"วันที่   : {booking.start_date.strftime('%d/%m/%Y')}\n"
        f"เวลา    : {time_str}"
    )


def _get_booker_email(booking) -> str:
    """Get the booker's email from Django User, falling back to empty string."""
    from django.contrib.auth.models import User
    try:
        user = User.objects.get(username=booking.booker_id)
        return user.email or ""
    except User.DoesNotExist:
        return ""
