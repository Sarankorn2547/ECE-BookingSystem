import uuid
from django.db import models


class Room(models.Model):
    class RoomType(models.TextChoices):
        MEETING = 'MEETING', 'ห้องประชุม'
        LECTURE = 'LECTURE', 'ห้องเรียน'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=RoomType.choices)
    capacity = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class UserProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        LECTURER = 'LECTURER', 'Lecturer'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tu_uid = models.CharField(max_length=100, unique=True)
    username = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=Role.choices, blank=True, default='')

    def __str__(self):
        return f"{self.username} ({self.role or 'no role'})"


class BlackoutPeriod(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # null = applies to all rooms
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True, related_name='blackout_periods')
    title = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    reason = models.TextField(blank=True)
    created_by = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        scope = self.room.code if self.room else 'ทุกห้อง'
        return f"{self.title} ({scope}: {self.start_date} - {self.end_date})"


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'รอการอนุมัติ'
        APPROVED = 'APPROVED', 'อนุมัติแล้ว'
        REJECTED = 'REJECTED', 'ปฏิเสธ'
        CANCELLED = 'CANCELLED', 'ยกเลิก'

    class PurposeType(models.TextChoices):
        COURSE = 'COURSE', 'สอนวิชา'
        TRAINING = 'TRAINING', 'ฝึกอบรม'

    class ProgramType(models.TextChoices):
        BACHELOR = 'BACHELOR', 'ปริญญาตรีภาคปกติ'
        MASTER = 'MASTER', 'ปริญญาโท'
        TEP_TEPE = 'TEP_TEPE', 'TEP-TEPE'
        TU_PINE = 'TU_PINE', 'TU-PINE'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='bookings')
    booker_id = models.CharField(max_length=100)
    booker_name = models.CharField(max_length=200, blank=True)
    purpose_type = models.CharField(max_length=20, choices=PurposeType.choices, default=PurposeType.COURSE)
    course_code = models.CharField(max_length=50, blank=True, null=True)
    course_name = models.CharField(max_length=200, blank=True, null=True)
    program = models.CharField(max_length=20, choices=ProgramType.choices, blank=True, null=True)
    training_title = models.CharField(max_length=200, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    recurring_pattern = models.JSONField(null=True, blank=True)
    days_of_week = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    approval_by = models.CharField(max_length=100, blank=True)
    approval_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Teams Bot context for proactive reply
    teams_service_url = models.CharField(max_length=500, blank=True, default='')
    teams_conversation_id = models.CharField(max_length=500, blank=True, default='')
    teams_activity_id = models.CharField(max_length=200, blank=True, default='')

    def __str__(self):
        return f"{self.room.code} by {self.booker_name or self.booker_id} ({self.start_date})"


class BookingLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=50)  # CREATED, APPROVED, REJECTED, CANCELLED
    actor = models.CharField(max_length=100)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} on booking {self.booking_id} by {self.actor}"