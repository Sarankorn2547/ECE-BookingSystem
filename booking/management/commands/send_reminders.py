from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.models import User
from booking.models import Booking

class Command(BaseCommand):
    help = "Send email reminders to users with bookings tomorrow"

    def handle(self, *args, **options):
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_js_day = (tomorrow.weekday() + 1) % 7

        bookings = Booking.objects.filter(
            status__iexact=Booking.Status.APPROVED,
            start_date__lte=tomorrow,
            end_date__gte=tomorrow
        ).select_related('room')

        reminded_count = 0
        for b in bookings:
            # Check if booking actually occurs tomorrow
            occurs_tomorrow = False
            if not b.days_of_week:
                if b.start_date == tomorrow:
                    occurs_tomorrow = True
            else:
                b_days = [int(d) for d in b.days_of_week]
                if tomorrow_js_day in b_days:
                    occurs_tomorrow = True

            if occurs_tomorrow:
                # Find user email
                try:
                    user = User.objects.get(username=b.booker_id)
                    email = user.email
                except User.DoesNotExist:
                    email = None

                if not email:
                    self.stdout.write(self.style.WARNING(f"Skipped reminder for Booking #{b.id}: booker email not found."))
                    continue

                # Send email
                subject = f"[ECE Booking] แจ้งเตือน: สิทธิ์การเข้าใช้งานห้อง {b.room.code} ในวันพรุ่งนี้"
                purpose_desc = f"วิชา {b.course_code} {b.course_name}" if b.purpose_type == Booking.PurposeType.COURSE else f"อบรมหัวข้อ {b.training_title}"
                body = (
                    f"เรียน {b.booker_name or b.booker_id},\n\n"
                    f"นี่คือการแจ้งเตือนล่วงหน้า 1 วันสำหรับการเข้าใช้งานห้องที่ได้รับการอนุมัติของท่าน:\n\n"
                    f"ห้อง: {b.room.code} - {b.room.name}\n"
                    f"วันที่: {tomorrow.strftime('%d/%m/%Y')} (พรุ่งนี้)\n"
                    f"เวลา: {b.start_time.strftime('%H:%M')} - {b.end_time.strftime('%H:%M')}\n"
                    f"วัตถุประสงค์: {purpose_desc}\n"
                    f"หมายเหตุ: {b.notes or '-'}\n\n"
                    f"ขอบคุณที่ใช้บริการ ระบบจองห้อง ECE"
                )

                try:
                    send_mail(
                        subject=subject,
                        message=body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False
                    )
                    self.stdout.write(self.style.SUCCESS(f"Sent reminder to {email} for Booking #{b.id}"))
                    reminded_count += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Failed to send email to {email}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Finished sending reminders. Total sent: {reminded_count}"))
