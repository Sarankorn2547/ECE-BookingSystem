import logging
from datetime import timedelta, date, time
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Booking, BlackoutPeriod, UserProfile

logger = logging.getLogger(__name__)


def check_booking_conflict(room, start_date, end_date, start_time, end_time, days_of_week=None, exclude_booking_id=None):
    """
    Checks if a proposed booking overlaps with any active BlackoutPeriod or existing APPROVED/PENDING Booking.
    Returns a description string if there is a conflict, or None otherwise.
    """
    # 1. Check against Blackout Periods
    blackouts = BlackoutPeriod.objects.filter(
        Q(room=room) | Q(room__isnull=True),
        start_date__lte=end_date,
        end_date__gte=start_date
    )

    if days_of_week:
        proposed_days = set(int(d) for d in days_of_week)
    else:
        proposed_days = None

    for bp in blackouts:
        o_start = max(start_date, bp.start_date)
        o_end = min(end_date, bp.end_date)

        has_active_date = False
        if proposed_days:
            curr = o_start
            while curr <= o_end:
                curr_js_day = (curr.weekday() + 1) % 7
                if curr_js_day in proposed_days:
                    has_active_date = True
                    break
                curr += timedelta(days=1)
        else:
            if o_start <= start_date <= o_end:
                has_active_date = True

        if has_active_date:
            bp_start_time = bp.start_time or time(0, 0)
            bp_end_time = bp.end_time or time(23, 59, 59)
            if max(start_time, bp_start_time) < min(end_time, bp_end_time):
                return f"ชนกับช่วงเวลาปิดปรับปรุง/วันหยุด: {bp.title}"

    # 2. Check against existing PENDING/APPROVED bookings
    bookings = Booking.objects.filter(
        room=room,
        status__in=[Booking.Status.PENDING, Booking.Status.APPROVED],
        start_date__lte=end_date,
        end_date__gte=start_date
    )
    if exclude_booking_id:
        bookings = bookings.exclude(id=exclude_booking_id)

    for b in bookings:
        o_start = max(start_date, b.start_date)
        o_end = min(end_date, b.end_date)

        b_days = set(b.days_of_week) if b.days_of_week else None

        has_active_date = False
        curr = o_start
        while curr <= o_end:
            proposed_active = (not proposed_days) or ((curr.weekday() + 1) % 7 in proposed_days)
            existing_active = (not b_days) or ((curr.weekday() + 1) % 7 in b_days)

            if proposed_active and existing_active:
                has_active_date = True
                break
            curr += timedelta(days=1)

        if has_active_date:
            if max(start_time, b.start_time) < min(end_time, b.end_time):
                desc = f"{b.course_code or ''} {b.course_name or b.training_title or ''}".strip()
                return f"ชนกับการจองที่มีอยู่แล้วของ {b.booker_name or b.booker_id} ({desc or 'ไม่มีชื่อวิชา/หัวข้อ'}) ช่วง {b.start_time.strftime('%H:%M')}-{b.end_time.strftime('%H:%M')}"

    return None


def send_booking_notification_to_admin(booking):
    subject = f"[ECE Booking] คำขอจองห้องใหม่: {booking.room.code}"
    message = (
        f"มีคำขอจองห้องใหม่ในระบบ\n\n"
        f"ผู้จอง: {booking.booker_name} ({booking.booker_id})\n"
        f"ห้อง: {booking.room.code} - {booking.room.name}\n"
        f"วันที่: {booking.start_date} ถึง {booking.end_date}\n"
        f"เวลา: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
    )
    if booking.days_of_week:
        days_names = ['อาทิตย์', 'จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์']
        days_str = ", ".join(days_names[d] for d in booking.days_of_week)
        message += f"วันในสัปดาห์: {days_str}\n"

    purpose_desc = f"สอนวิชา {booking.course_code} {booking.course_name}" if booking.purpose_type == Booking.PurposeType.COURSE else f"อบรมหัวข้อ {booking.training_title}"
    message += f"วัตถุประสงค์: {purpose_desc}\n"
    message += f"หมายเหตุ: {booking.notes or '-'}\n\n"
    message += f"กรุณาเข้าสู่ระบบเพื่อดำเนินการอนุมัติหรือปฏิเสธคำขอได้ที่: http://localhost:8000/admin/approvals/\n"

    admin_emails = [u.email for u in User.objects.filter(is_superuser=True) if u.email]
    admin_profiles = UserProfile.objects.filter(role=UserProfile.Role.ADMIN)
    for profile in admin_profiles:
        try:
            user = User.objects.get(username=profile.tu_uid)
            if user.email and user.email not in admin_emails:
                admin_emails.append(user.email)
        except User.DoesNotExist:
            pass

    if not admin_emails:
        admin_emails = [settings.DEFAULT_FROM_EMAIL] if hasattr(settings, 'DEFAULT_FROM_EMAIL') else ['admin@ece.engr.tu.ac.th']

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@ece.engr.tu.ac.th',
            admin_emails,
            fail_silently=True
        )
    except Exception as e:
        logger.error(f"Failed to send email to admin: {str(e)}")


def send_status_update_to_user(booking):
    subject = f"[ECE Booking] ผลการพิจารณาคำขอจองห้อง {booking.room.code}: {booking.get_status_display()}"
    status_text = "อนุมัติเรียบร้อยแล้ว" if booking.status == Booking.Status.APPROVED else "ถูกปฏิเสธ"

    message = (
        f"เรียน {booking.booker_name},\n\n"
        f"คำขอจองห้องของคุณได้รับการพิจารณาแล้ว โดยมีรายละเอียดดังนี้:\n\n"
        f"สถานะ: {booking.get_status_display()} ({status_text})\n"
        f"ห้อง: {booking.room.code} - {booking.room.name}\n"
        f"วันที่: {booking.start_date} ถึง {booking.end_date}\n"
        f"เวลา: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
    )
    if booking.days_of_week:
        days_names = ['อาทิตย์', 'จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์']
        days_str = ", ".join(days_names[d] for d in booking.days_of_week)
        message += f"วันในสัปดาห์: {days_str}\n"

    purpose_desc = f"สอนวิชา {booking.course_code} {booking.course_name}" if booking.purpose_type == Booking.PurposeType.COURSE else f"อบรมหัวข้อ {booking.training_title}"
    message += f"วัตถุประสงค์: {purpose_desc}\n"

    if booking.status == Booking.Status.REJECTED:
        latest_log = booking.logs.filter(action="REJECTED").order_by("-created_at").first()
        reason = latest_log.metadata.get("reason", "") if latest_log and latest_log.metadata else ""
        message += f"เหตุผลการปฏิเสธ: {reason or '-'}\n"

    message += f"\nคุณสามารถตรวจสอบการจองทั้งหมดของคุณได้ที่: http://localhost:8000/my-bookings/\n"

    user_email = None
    try:
        user = User.objects.get(username=booking.booker_id)
        user_email = user.email
    except User.DoesNotExist:
        pass

    if not user_email:
        return

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@ece.engr.tu.ac.th',
            [user_email],
            fail_silently=True
        )
    except Exception as e:
        logger.error(f"Failed to send email to user: {str(e)}")


def send_cancellation_notification_to_admin(booking):
    subject = f"[ECE Booking] มีการยกเลิกคำขอจองห้อง: {booking.room.code}"
    message = (
        f"ผู้จองได้ยกเลิกคำขอจองห้องดังต่อไปนี้\n\n"
        f"ผู้จอง: {booking.booker_name} ({booking.booker_id})\n"
        f"ห้อง: {booking.room.code} - {booking.room.name}\n"
        f"วันที่: {booking.start_date} ถึง {booking.end_date}\n"
        f"เวลา: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
    )
    if booking.days_of_week:
        days_names = ['อาทิตย์', 'จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์']
        days_str = ", ".join(days_names[d] for d in booking.days_of_week)
        message += f"วันในสัปดาห์: {days_str}\n"

    purpose_desc = f"สอนวิชา {booking.course_code} {booking.course_name}" if booking.purpose_type == Booking.PurposeType.COURSE else f"อบรมหัวข้อ {booking.training_title}"
    message += f"วัตถุประสงค์: {purpose_desc}\n"

    admin_emails = [u.email for u in User.objects.filter(is_superuser=True) if u.email]
    admin_profiles = UserProfile.objects.filter(role=UserProfile.Role.ADMIN)
    for profile in admin_profiles:
        try:
            user = User.objects.get(username=profile.tu_uid)
            if user.email and user.email not in admin_emails:
                admin_emails.append(user.email)
        except User.DoesNotExist:
            pass

    if not admin_emails:
        admin_emails = [settings.DEFAULT_FROM_EMAIL] if hasattr(settings, 'DEFAULT_FROM_EMAIL') else ['admin@ece.engr.tu.ac.th']

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@ece.engr.tu.ac.th',
            admin_emails,
            fail_silently=True
        )
    except Exception as e:
        logger.error(f"Failed to send email to admin: {str(e)}")
