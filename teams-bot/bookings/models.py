from django.db import models
from django.contrib.auth.models import User

class Room(models.Model):
    room_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    room_type = models.CharField(max_length=50)
    capacity = models.IntegerField()

    def __str__(self):
        return f"{self.room_id} - {self.name}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'รอการอนุมัติ'),
        ('APPROVED', 'อนุมัติแล้ว'),
        ('REJECTED', 'ปฏิเสธ'),
    ]

    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    user_name = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    purpose = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    # Teams context for proactive reply when admin approves/rejects
    teams_service_url = models.CharField(max_length=500, blank=True, default='')
    teams_conversation_id = models.CharField(max_length=500, blank=True, default='')
    teams_activity_id = models.CharField(max_length=200, blank=True, default='')

    def __str__(self):
        return f"{self.room} by {self.user_name} ({self.start_time})"
