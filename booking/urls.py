from django.urls import path
from . import views

app_name = "booking"

urlpatterns = [
    path("", views.index_view, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("booking/", views.booking_form_view, name="booking_form"),
    path("my-bookings/", views.my_bookings_view, name="my_bookings"),
    path("calendar/", views.calendar_view, name="calendar"),
]

