from django.contrib import admin
from .models import Room, UserProfile, Booking, BookingLog, BlackoutPeriod


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'type', 'capacity', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('code', 'name')
    ordering = ('code',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('username', 'tu_uid', 'role')
    list_filter = ('role',)
    search_fields = ('username', 'tu_uid')
    ordering = ('username',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('room', 'booker_name', 'purpose_type', 'start_date', 'start_time', 'end_time', 'status', 'created_at')
    list_filter = ('status', 'purpose_type', 'start_date', 'room')
    search_fields = ('booker_name', 'booker_id', 'course_code', 'course_name', 'training_title')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')

    fieldsets = (
        ('Basic Info', {
            'fields': ('room', 'booker_id', 'booker_name', 'purpose_type')
        }),
        ('Course/Training Details', {
            'fields': ('course_code', 'course_name', 'training_title'),
            'classes': ('collapse',)
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'start_time', 'end_time', 'recurring_pattern', 'days_of_week')
        }),
        ('Status & Approval', {
            'fields': ('status', 'notes', 'approval_by', 'approval_at')
        }),
        ('Teams Integration', {
            'fields': ('teams_service_url', 'teams_conversation_id', 'teams_activity_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BookingLog)
class BookingLogAdmin(admin.ModelAdmin):
    list_display = ('booking', 'action', 'actor', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('booking__room__code', 'actor')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')


@admin.register(BlackoutPeriod)
class BlackoutPeriodAdmin(admin.ModelAdmin):
    list_display = ('title', 'room', 'start_date', 'end_date', 'created_by', 'created_at')
    list_filter = ('start_date', 'end_date', 'created_at')
    search_fields = ('title', 'reason', 'created_by')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at')
