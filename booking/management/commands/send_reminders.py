from datetime import date, timedelta

from django.core.management.base import BaseCommand

from booking.emails import notify_booking_reminder
from booking.models import Booking


class Command(BaseCommand):
    help = "Send 1-day-ahead reminder emails for all approved bookings occurring tomorrow"

    def handle(self, *args, **options):
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_dow = (tomorrow.weekday() + 1) % 7  # 0=Sun, 1=Mon … 6=Sat

        bookings = Booking.objects.filter(
            status__iexact=Booking.Status.APPROVED,
            start_date__lte=tomorrow,
            end_date__gte=tomorrow,
        ).select_related("room")

        sent = 0
        for b in bookings:
            if b.days_of_week:
                if tomorrow_dow not in [int(d) for d in b.days_of_week]:
                    continue
            else:
                if b.start_date != tomorrow:
                    continue

            notify_booking_reminder(b, tomorrow)
            self.stdout.write(self.style.SUCCESS(
                f"Reminded {b.booker_id} — {b.room.code} {tomorrow}"
            ))
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Done. {sent} reminder(s) sent."))
