import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'room_booking.settings')
django.setup()

from bookings.models import Room

rooms = [
    {'room_id': '406-3', 'name': 'ห้องประชุม 1', 'capacity': 60},
    {'room_id': '406-5', 'name': 'ห้องประชุม 2', 'capacity': 15},
    {'room_id': '408-1', 'name': 'ห้องประชุม 3', 'capacity': 10},
    {'room_id': '408-2/1', 'name': 'ห้องบรรยาย 1', 'capacity': 20},
    {'room_id': '408-2/2', 'name': 'ห้องบรรยาย 2', 'capacity': 20},
]

for r in rooms:
    obj, created = Room.objects.get_or_create(
        room_id=r['room_id'],
        defaults={'name': r['name'], 'capacity': r['capacity']}
    )
    if created:
        print(f"Created room: {r['room_id']}")
    else:
        print(f"Room already exists: {r['room_id']}")
