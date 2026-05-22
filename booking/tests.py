from datetime import date, time, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from .models import Room, UserProfile, Booking, BlackoutPeriod, BookingLog
from .utils import check_booking_conflict

class RoomModelTest(TestCase):
    def test_room_creation_and_str(self):
        room = Room.objects.create(
            code="406-3",
            name="ห้องประชุม 1",
            type=Room.RoomType.MEETING,
            capacity=60
        )
        self.assertEqual(str(room), "406-3 - ห้องประชุม 1")

class UserProfileModelTest(TestCase):
    def test_user_profile_creation_and_str(self):
        profile = UserProfile.objects.create(
            tu_uid="testuser",
            username="testuser",
            role=UserProfile.Role.LECTURER
        )
        self.assertEqual(str(profile), "testuser (LECTURER)")

class ConflictDetectionTest(TestCase):
    def setUp(self):
        self.room = Room.objects.create(
            code="406-3",
            name="ห้องประชุม 1",
            type=Room.RoomType.MEETING,
            capacity=60
        )

    def test_no_conflict_different_times(self):
        # Existing booking: 09:00 - 11:00
        Booking.objects.create(
            room=self.room,
            booker_id="user1",
            booker_name="User 1",
            purpose_type=Booking.PurposeType.COURSE,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            status=Booking.Status.APPROVED
        )

        # Proposed booking: 11:00 - 13:00 (no overlap on boundary)
        conflict = check_booking_conflict(
            room=self.room,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            start_time=time(11, 0),
            end_time=time(13, 0)
        )
        self.assertIsNone(conflict)

    def test_conflict_overlapping_times(self):
        # Existing booking: 09:00 - 11:00
        Booking.objects.create(
            room=self.room,
            booker_id="user1",
            booker_name="User 1",
            purpose_type=Booking.PurposeType.COURSE,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            status=Booking.Status.APPROVED
        )

        # Proposed booking: 10:00 - 12:00 (overlaps 10:00-11:00)
        conflict = check_booking_conflict(
            room=self.room,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            start_time=time(10, 0),
            end_time=time(12, 0)
        )
        self.assertIsNotNone(conflict)
        self.assertIn("ชนกับการจองที่มีอยู่แล้ว", conflict)

    def test_conflict_recurring(self):
        # Existing weekly recurring booking on Tuesday (weekday = 1, so (Tuesday(1) + 1)%7 = 2. Python Tuesday is 1. FullCalendar Tuesday is 2)
        # Note: python weekday: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
        # utils.py uses: curr_js_day = (curr.weekday() + 1) % 7
        # For Tuesday, curr.weekday() is 1, so (1 + 1) % 7 = 2
        Booking.objects.create(
            room=self.room,
            booker_id="user1",
            booker_name="User 1",
            purpose_type=Booking.PurposeType.COURSE,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
            start_time=time(9, 0),
            end_time=time(11, 0),
            days_of_week=[2],  # Tuesday (js index: Sunday=0, Monday=1, Tuesday=2)
            status=Booking.Status.APPROVED
        )

        # Proposed: 2026-06-09 (Tuesday) 10:00-12:00
        conflict = check_booking_conflict(
            room=self.room,
            start_date=date(2026, 6, 9),
            end_date=date(2026, 6, 9),
            start_time=time(10, 0),
            end_time=time(12, 0)
        )
        self.assertIsNotNone(conflict)

    def test_blackout_period_conflict(self):
        # Blackout period: all rooms closed on 2026-06-15
        BlackoutPeriod.objects.create(
            title= "วันหยุดชดเชย",
            start_date=date(2026, 6, 15),
            end_date=date(2026, 6, 15)
        )

        conflict = check_booking_conflict(
            room=self.room,
            start_date=date(2026, 6, 15),
            end_date=date(2026, 6, 15),
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
        self.assertIsNotNone(conflict)
        self.assertIn("ชนกับช่วงเวลาปิดปรับปรุง/วันหยุด", conflict)

class ViewAuthAndBookingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.room = Room.objects.create(
            code="406-3",
            name="ห้องประชุม 1",
            type=Room.RoomType.MEETING,
            capacity=60
        )

    def test_mock_login_lecturer(self):
        response = self.client.post(reverse('booking:login'), {
            'username': 'testuser',
            'password': 'test1234'
        })
        self.assertRedirects(response, reverse('booking:dashboard'))
        
        # Verify User and UserProfile created
        user = User.objects.get(username='testuser')
        self.assertEqual(user.username, 'testuser')
        profile = UserProfile.objects.get(tu_uid='testuser')
        self.assertEqual(profile.role, UserProfile.Role.LECTURER)

    def test_mock_login_admin(self):
        response = self.client.post(reverse('booking:login'), {
            'username': 'admin',
            'password': 'admin1234'
        })
        self.assertRedirects(response, reverse('booking:dashboard'))
        
        profile = UserProfile.objects.get(tu_uid='admin')
        self.assertEqual(profile.role, UserProfile.Role.ADMIN)

    def test_unauthenticated_redirect(self):
        response = self.client.get(reverse('booking:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_booking_submission(self):
        # Login first
        self.client.post(reverse('booking:login'), {
            'username': 'testuser',
            'password': 'test1234'
        })

        # Submit booking
        response = self.client.post(reverse('booking:booking_form'), {
            'room': str(self.room.id),
            'start_date': '2026-06-01',
            'end_date': '2026-06-01',
            'start_time': '09:00',
            'end_time': '11:00',
            'purpose_type': 'COURSE',
            'course_code': 'CN334',
            'course_name': 'Web App Development',
            'program': 'BACHELOR',
            'notes': 'Normal Lecture'
        })
        self.assertRedirects(response, reverse('booking:dashboard'))
        
        # Verify booking created
        bookings = Booking.objects.filter(room=self.room)
        self.assertEqual(bookings.count(), 1)
        booking = bookings.first()
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(booking.booker_id, 'testuser')
        self.assertEqual(booking.course_code, 'CN334')

    def test_invalid_date_range(self):
        # Login first
        self.client.post(reverse('booking:login'), {
            'username': 'testuser',
            'password': 'test1234'
        })

        # Submit booking with end_date before start_date
        response = self.client.post(reverse('booking:booking_form'), {
            'room': str(self.room.id),
            'start_date': '2026-06-05',
            'end_date': '2026-06-01',
            'start_time': '09:00',
            'end_time': '11:00',
            'purpose_type': 'COURSE',
            'course_code': 'CN334',
            'course_name': 'Web App Development',
            'program': 'BACHELOR',
            'notes': 'Normal Lecture'
        })
        self.assertRedirects(response, reverse('booking:booking_form'))
        
        # Verify no booking was created
        bookings = Booking.objects.filter(room=self.room)
        self.assertEqual(bookings.count(), 0)

    def test_single_day_ignores_recurring(self):
        # Login first
        self.client.post(reverse('booking:login'), {
            'username': 'testuser',
            'password': 'test1234'
        })

        # Submit booking with same start/end date but days_of_week checked
        response = self.client.post(reverse('booking:booking_form'), {
            'room': str(self.room.id),
            'start_date': '2026-06-01',
            'end_date': '2026-06-01',
            'start_time': '09:00',
            'end_time': '11:00',
            'purpose_type': 'COURSE',
            'course_code': 'CN334',
            'course_name': 'Web App Development',
            'program': 'BACHELOR',
            'days_of_week': ['1', '2'], # Monday, Tuesday
            'notes': 'Normal Lecture'
        })
        self.assertRedirects(response, reverse('booking:dashboard'))
        
        # Verify booking created but days_of_week and recurring_pattern are null
        bookings = Booking.objects.filter(room=self.room)
        self.assertEqual(bookings.count(), 1)
        booking = bookings.first()
        self.assertIsNone(booking.days_of_week)
        self.assertIsNone(booking.recurring_pattern)

from django.core.management import call_command
from django.core import mail

class SendRemindersCommandTest(TestCase):
    def setUp(self):
        self.room = Room.objects.create(
            code="406-3",
            name="ห้องประชุม 1",
            type=Room.RoomType.MEETING,
            capacity=60
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpassword"
        )
        UserProfile.objects.create(
            tu_uid="testuser",
            username="testuser",
            role=UserProfile.Role.LECTURER
        )

    def test_send_reminders_command(self):
        tomorrow = date.today() + timedelta(days=1)
        # Create an approved booking for tomorrow
        Booking.objects.create(
            room=self.room,
            booker_id="testuser",
            booker_name="Test User",
            purpose_type=Booking.PurposeType.COURSE,
            start_date=tomorrow,
            end_date=tomorrow,
            start_time=time(9, 0),
            end_time=time(11, 0),
            status=Booking.Status.APPROVED
        )

        # Clear outbox
        mail.outbox = []

        # Run command
        call_command('send_reminders')

        # Assert email sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("แจ้งเตือน: สิทธิ์การเข้าใช้งานห้อง 406-3 ในวันพรุ่งนี้", email.subject)
        self.assertEqual(email.to, ["testuser@example.com"])

class AdminReportsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.room = Room.objects.create(
            code="406-3",
            name="ห้องประชุม 1",
            type=Room.RoomType.MEETING,
            capacity=60
        )
        self.user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpassword"
        )
        UserProfile.objects.create(
            tu_uid="admin",
            username="admin",
            role=UserProfile.Role.ADMIN
        )

    def test_admin_reports_view_populates_stats(self):
        # Login admin via mock login
        self.client.post(reverse('booking:login'), {
            'username': 'admin',
            'password': 'admin1234'
        })

        # Create some bookings in the range of the current month
        today = date.today()
        # Approved Course booking
        Booking.objects.create(
            room=self.room,
            booker_id="testuser",
            booker_name="Test User",
            purpose_type=Booking.PurposeType.COURSE,
            program=Booking.ProgramType.BACHELOR,
            start_date=today,
            end_date=today,
            start_time=time(9, 0),
            end_time=time(11, 0),
            status=Booking.Status.APPROVED
        )
        # Approved Training booking
        Booking.objects.create(
            room=self.room,
            booker_id="testuser2",
            booker_name="Test User 2",
            purpose_type=Booking.PurposeType.TRAINING,
            start_date=today,
            end_date=today,
            start_time=time(13, 0),
            end_time=time(15, 0),
            status=Booking.Status.APPROVED
        )

        response = self.client.get(reverse('booking:admin_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('purpose_stats', response.context)
        self.assertIn('program_stats', response.context)
        self.assertEqual(response.context['purpose_stats']['COURSE'], 1)
        self.assertEqual(response.context['purpose_stats']['TRAINING'], 1)
        self.assertEqual(response.context['program_stats']['BACHELOR'], 1)


class TULoginWhitelistTest(TestCase):
    """Test TU type whitelist and initial admin auto-assignment features."""

    def setUp(self):
        self.client = Client()
        self.login_url = reverse('booking:login')

    def _mock_tu_response(self, tu_type='lecturer', username='teststaff'):
        """Return a mock TU REST API successful response dict."""
        return {
            "status": True,
            "displayname_th": "ทดสอบ ผู้ใช้",
            "displayname_en": "Test User",
            "email": f"{username}@tu.ac.th",
            "department": "ECE",
            "faculty": "Engineering",
            "type": tu_type,
        }

    def test_whitelist_blocks_unlisted_type(self):
        """User with type 'alumni' should be blocked when whitelist is student,staff,lecturer."""
        from unittest.mock import patch, MagicMock
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_tu_response(tu_type='alumni', username='alum001')

        with patch('booking.views.requests.post', return_value=mock_resp):
            with self.settings(ALLOWED_TU_TYPES=['student', 'staff', 'lecturer']):
                response = self.client.post(self.login_url, {
                    'username': 'alum001',
                    'password': 'anypassword',
                })
        # Should stay on login page with an error message
        self.assertEqual(response.status_code, 200)
        messages_list = list(response.wsgi_request._messages)
        self.assertTrue(any('ไม่มีสิทธิ์' in str(m) for m in messages_list))

    def test_whitelist_allows_listed_type(self):
        """User with type 'lecturer' should be allowed through whitelist."""
        from unittest.mock import patch, MagicMock
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_tu_response(tu_type='lecturer', username='lec001')

        with patch('booking.views.requests.post', return_value=mock_resp):
            with self.settings(ALLOWED_TU_TYPES=['student', 'staff', 'lecturer'],
                               INITIAL_ADMIN_USERNAMES=[]):
                response = self.client.post(self.login_url, {
                    'username': 'lec001',
                    'password': 'anypassword',
                })
        # Should redirect to dashboard
        self.assertRedirects(response, '/dashboard/', fetch_redirect_response=False)

    def test_empty_whitelist_allows_all_types(self):
        """Empty ALLOWED_TU_TYPES should not block any user type."""
        from unittest.mock import patch, MagicMock
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_tu_response(tu_type='external', username='ext001')

        with patch('booking.views.requests.post', return_value=mock_resp):
            with self.settings(ALLOWED_TU_TYPES=[], INITIAL_ADMIN_USERNAMES=[]):
                response = self.client.post(self.login_url, {
                    'username': 'ext001',
                    'password': 'anypassword',
                })
        self.assertRedirects(response, '/dashboard/', fetch_redirect_response=False)

    def test_initial_admin_gets_admin_role_on_first_login(self):
        """Username in INITIAL_ADMIN_USERNAMES should get ADMIN role on first login."""
        from unittest.mock import patch, MagicMock
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_tu_response(tu_type='staff', username='sairags')

        with patch('booking.views.requests.post', return_value=mock_resp):
            with self.settings(ALLOWED_TU_TYPES=[], INITIAL_ADMIN_USERNAMES=['sairags']):
                self.client.post(self.login_url, {
                    'username': 'sairags',
                    'password': 'anypassword',
                })

        profile = UserProfile.objects.get(tu_uid='sairags')
        self.assertEqual(profile.role, UserProfile.Role.ADMIN)

    def test_non_initial_admin_gets_no_role_on_first_login(self):
        """Username NOT in INITIAL_ADMIN_USERNAMES should get empty role on first login."""
        from unittest.mock import patch, MagicMock
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_tu_response(tu_type='lecturer', username='random001')

        with patch('booking.views.requests.post', return_value=mock_resp):
            with self.settings(ALLOWED_TU_TYPES=[], INITIAL_ADMIN_USERNAMES=['sairags']):
                self.client.post(self.login_url, {
                    'username': 'random001',
                    'password': 'anypassword',
                })

        profile = UserProfile.objects.get(tu_uid='random001')
        self.assertEqual(profile.role, '')  # ไม่มี role

    def test_initial_admin_existing_empty_role_gets_promoted(self):
        """Username in INITIAL_ADMIN_USERNAMES with an existing empty-role profile gets promoted."""
        from unittest.mock import patch, MagicMock
        # Pre-create profile with empty role
        User.objects.create_user(username='wachira', password='test')
        UserProfile.objects.create(tu_uid='wachira', username='wachira', role='')

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._mock_tu_response(tu_type='staff', username='wachira')

        with patch('booking.views.requests.post', return_value=mock_resp):
            with self.settings(ALLOWED_TU_TYPES=[], INITIAL_ADMIN_USERNAMES=['wachira']):
                self.client.post(self.login_url, {
                    'username': 'wachira',
                    'password': 'anypassword',
                })

        profile = UserProfile.objects.get(tu_uid='wachira')
        self.assertEqual(profile.role, UserProfile.Role.ADMIN)

