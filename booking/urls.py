from django.urls import path
from . import views

app_name = "booking"

urlpatterns = [
    # Core
    path("", views.index_view, name="index"),
    path("dashboard/", views.dashboard_view, name="dashboard"),

    # Accounts
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("accounts/profile/", views.profile_view, name="profile"),
    path("admin-panel/users/", views.user_list_view, name="user-list"),
    path("admin-panel/users/<uuid:pk>/role/", views.set_user_role_view, name="set-user-role"),

    # Rooms (Admin only)
    path("rooms/", views.room_list_view, name="room-list"),
    path("rooms/add/", views.room_add_view, name="room-add"),
    path("rooms/<uuid:pk>/edit/", views.room_edit_view, name="room-edit"),
    path("rooms/blackout/", views.blackout_view, name="blackout"),

    # Bookings (Lecturer)
    path("bookings/", views.booking_list_view, name="booking-list"),
    path("bookings/create/", views.booking_create_view, name="booking-create"),
    path("bookings/recurring/", views.recurring_booking_view, name="booking-recurring"),
    path("bookings/<uuid:pk>/", views.booking_detail_view, name="booking-detail"),
    path("bookings/<uuid:pk>/cancel/", views.booking_cancel_view, name="booking-cancel"),

    # Approvals (Admin)
    path("approvals/", views.approval_queue_view, name="approval-queue"),
    path("approvals/<uuid:pk>/approve/", views.approve_view, name="approve"),
    path("approvals/<uuid:pk>/reject/", views.reject_view, name="reject"),

    # Calendar (All)
    path("calendar/", views.calendar_view, name="calendar"),
    path("calendar/monthly/", views.calendar_monthly_view, name="calendar-monthly"),

    # Reports (Admin)
    path("reports/", views.reports_view, name="reports"),
    path("reports/utilization/", views.utilization_view, name="utilization"),
    path("reports/export/csv/", views.export_csv_view, name="export-csv"),

    # Teams Bot NLP API (moved from room_booking_nlp)
    path("api/nlp/", views.nlp_parse_view, name="nlp-parse"),
]
