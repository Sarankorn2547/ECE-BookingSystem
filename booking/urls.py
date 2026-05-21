from django.urls import path
from . import views

app_name = "booking"

urlpatterns = [
    # Core
    path("", views.index_view, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),

    # Booking (Lecturer)
    path("booking/", views.booking_form_view, name="booking_form"),
    path("my-bookings/", views.my_bookings_view, name="my_bookings"),
    path("my-bookings/<uuid:booking_id>/cancel/", views.cancel_booking_view, name="cancel_booking"),

    # Calendar
    path("calendar/", views.calendar_view, name="calendar"),
    path("api/calendar-events/", views.calendar_events_api, name="calendar_events"),

    # Admin — Approvals
    path("admin/approvals/", views.approval_queue_view, name="approval_queue"),
    path("admin/approvals/<uuid:booking_id>/approve/", views.approve_view, name="approve"),
    path("admin/approvals/<uuid:booking_id>/reject/", views.reject_view, name="reject"),

    # Admin — Reports & System
    path("admin/reports/", views.admin_reports_view, name="admin_reports"),
    path("admin/system/", views.admin_system_view, name="admin_system"),
]
