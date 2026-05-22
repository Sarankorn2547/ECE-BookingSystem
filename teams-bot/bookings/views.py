import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .nlp_service import parse_booking_request
from .models import Room, Booking, BlackoutPeriod, BookingLog
from datetime import datetime, time, timedelta
import pytz
from django.db.models import Q

TZ = pytz.timezone('Asia/Bangkok')

HELP_TEXT = (
    "🤖 **คำสั่งที่ใช้ได้ครับ**\n\n"
    "**📅 เช็คห้องว่าง**\n"
    "• พรุ่งนี้ห้องไหนว่างบ้าง\n"
    "• วันมะรื่นนี้มีห้องว่างไหม\n"
    "• ห้อง 406-3 พรุ่งนี้ว่างช่วงไหนบ้าง\n\n"
    "**📝 จองห้อง**\n"
    "• จองห้อง 406-3 พรุ่งนี้ 9 โมงถึง 10 โมง สอนวิชา CN332\n\n"
    "**📋 การจองของฉัน**\n"
    "• ดูการจองของฉัน\n\n"
    "**❌ ยกเลิกการจอง**\n"
    "• ยกเลิกการจองห้อง 406-3 พรุ่งนี้\n\n"
    "**🔑 Admin**\n"
    "• อนุมัติ #รหัส — อนุมัติ booking ID (ระบุรหัสเต็มหรือท้ายรหัสให้ไม่ซ้ำ)\n"
    "• ปฏิเสธ #รหัส เหตุผล... — ปฏิเสธพร้อมเหตุผล"
)


def check_booking_conflict(room, start_date, end_date, start_time, end_time, days_of_week=None, exclude_booking_id=None):
    # 1. Check against Blackout Periods
    blackouts = BlackoutPeriod.objects.filter(
        Q(room=room) | Q(room__isnull=True),
        start_date__lte=end_date,
        end_date__gte=start_date
    )

    if days_of_week:
        proposed_days = set(int(d) for d in days_of_week)
    else:
        proposed_days = None

    for bp in blackouts:
        o_start = max(start_date, bp.start_date)
        o_end = min(end_date, bp.end_date)

        has_active_date = False
        if proposed_days:
            curr = o_start
            while curr <= o_end:
                curr_js_day = (curr.weekday() + 1) % 7
                if curr_js_day in proposed_days:
                    has_active_date = True
                    break
                curr += timedelta(days=1)
        else:
            if o_start <= start_date <= o_end:
                has_active_date = True

        if has_active_date:
            bp_start_time = bp.start_time or time(0, 0)
            bp_end_time = bp.end_time or time(23, 59, 59)
            if max(start_time, bp_start_time) < min(end_time, bp_end_time):
                return f"ชนกับช่วงเวลาปิดปรับปรุง/วันหยุด: {bp.title}"

    # 2. Check against existing PENDING/APPROVED bookings
    bookings = Booking.objects.filter(
        room=room,
        status__in=['PENDING', 'APPROVED'],
        start_date__lte=end_date,
        end_date__gte=start_date
    )
    if exclude_booking_id:
        bookings = bookings.exclude(id=exclude_booking_id)

    for b in bookings:
        o_start = max(start_date, b.start_date)
        o_end = min(end_date, b.end_date)

        b_days = set(b.days_of_week) if b.days_of_week else None

        has_active_date = False
        curr = o_start
        while curr <= o_end:
            proposed_active = (not proposed_days) or ((curr.weekday() + 1) % 7 in proposed_days)
            existing_active = (not b_days) or ((curr.weekday() + 1) % 7 in b_days)

            if proposed_active and existing_active:
                has_active_date = True
                break
            curr += timedelta(days=1)

        if has_active_date:
            if max(start_time, b.start_time) < min(end_time, b.end_time):
                desc = f"{b.course_code or ''} {b.course_name or b.training_title or ''}".strip()
                return f"ชนกับการจองที่มีอยู่แล้วของ {b.booker_name or b.booker_id} ({desc or 'ไม่มีชื่อวิชา/หัวข้อ'}) ช่วง {b.start_time.strftime('%H:%M')}-{b.end_time.strftime('%H:%M')}"

    return None


class NLPParseView(APIView):
    def post(self, request):
        text = request.data.get('text', '')
        from_data = request.data.get('from', {})
        username = from_data.get('name', 'Unknown User')

        teams_context = {
            'service_url': request.data.get('serviceUrl', ''),
            'conversation_id': request.data.get('conversation', {}).get('id', ''),
            'activity_id': request.data.get('id', ''),
        }

        clean_text = re.sub(r'<at>.*?</at>', '', text)
        clean_text = re.sub(r'RoomBot', '', clean_text, flags=re.IGNORECASE)
        # Strip remaining HTML tags and decode common entities
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        clean_text = clean_text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').strip()

        if not clean_text:
            return Response({"error": "No text provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Help command — handle directly without Gemini
        if re.match(r'^help$', clean_text, flags=re.IGNORECASE):
            return Response({"type": "message", "text": HELP_TEXT})

        # Admin commands: อนุมัติ #id / ปฏิเสธ #id เหตุผล
        admin_match = re.match(r'^(อนุมัติ|ปฏิเสธ)\s+#?([a-fA-F0-9\-]+)(?:\s+(.+))?$', clean_text.strip())
        if admin_match:
            action, booking_id, reason = admin_match.group(1), admin_match.group(2).strip(), admin_match.group(3) or ''
            new_status = 'APPROVED' if action == 'อนุมัติ' else 'REJECTED'
            return self.handle_admin_action(booking_id, new_status, reason, username)

        print(f"DEBUG: View calling parse_booking_request with: {clean_text}", flush=True)
        result = parse_booking_request(clean_text)
        print(f"DEBUG: View received result: {result}", flush=True)
        intent = result.get('intent')

        if intent == 'create_booking':
            return self.handle_create_booking(result, username, teams_context)
        elif intent == 'check_availability':
            return self.handle_check_availability(result)
        elif intent == 'check_room':
            return self.handle_check_room(result)
        elif intent == 'my_bookings':
            return self.handle_my_bookings(username)
        elif intent == 'cancel_booking':
            return self.handle_cancel_booking(result, username)
        elif intent == 'help':
            return Response({"type": "message", "text": HELP_TEXT})
        else:
            return Response({
                "type": "message",
                "text": "🤖 ไม่เข้าใจคำสั่งนี้ครับ พิมพ์ **help** เพื่อดูคำสั่งทั้งหมด"
            })

    def handle_create_booking(self, result, username, teams_context):
        room_id = result.get('room_id')
        date_str = result.get('date')
        start_time_str = result.get('start_time')
        end_time_str = result.get('end_time')
        purpose = result.get('purpose', '')

        save_status = "error"
        conflict_msg = ""
        if room_id and date_str and start_time_str and end_time_str:
            try:
                room = Room.objects.get(code=room_id)
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                start_time = datetime.strptime(start_time_str, "%H:%M").time()
                end_time = datetime.strptime(end_time_str, "%H:%M").time()

                conflict_msg = check_booking_conflict(
                    room=room,
                    start_date=target_date,
                    end_date=target_date,
                    start_time=start_time,
                    end_time=end_time
                )

                if conflict_msg:
                    save_status = "conflict"
                else:
                    # Auto-parse course code from purpose
                    purpose_type = 'TRAINING'
                    course_code = None
                    course_name = None
                    training_title = None
                    
                    course_match = re.search(r'([A-Z]{2,3})\s*(\d{3})', purpose, re.IGNORECASE)
                    if course_match:
                        purpose_type = 'COURSE'
                        course_code = f"{course_match.group(1).upper()}{course_match.group(2)}"
                        course_name = purpose
                    else:
                        training_title = purpose or "จองผ่าน Teams Bot"

                    booking = Booking.objects.create(
                        room=room,
                        booker_id=username,
                        booker_name=username,
                        purpose_type=purpose_type,
                        course_code=course_code,
                        course_name=course_name,
                        training_title=training_title,
                        start_date=target_date,
                        end_date=target_date,
                        start_time=start_time,
                        end_time=end_time,
                        notes=purpose,
                        status='PENDING',
                        teams_service_url=teams_context.get('service_url', ''),
                        teams_conversation_id=teams_context.get('conversation_id', ''),
                        teams_activity_id=teams_context.get('activity_id', ''),
                    )
                    
                    # Create log
                    BookingLog.objects.create(
                        booking=booking,
                        action="CREATED",
                        actor=username
                    )
                    save_status = "success"
            except Room.DoesNotExist:
                save_status = "room_not_found"
            except Exception as e:
                print(f"DEBUG Error in create booking: {str(e)}", flush=True)
                save_status = "error"

        if save_status == "success":
            msg = f"✅ **จองห้องสำเร็จ (รออนุมัติ)**\n\n"
        elif save_status == "conflict":
            msg = f"❌ **จองไม่สำเร็จ: {conflict_msg}**\n\n"
        elif save_status == "room_not_found":
            msg = f"❌ **จองไม่สำเร็จ: ไม่พบห้อง {room_id}**\n\n"
        else:
            msg = f"⚠️ **จองไม่สำเร็จ: ข้อมูลไม่ครบถ้วน**\n\n"

        msg += (
            f"👤 **ผู้จอง:** {username}\n\n"
            f"🏢 **ห้อง:** {room_id or '-'}\n\n"
            f"📅 **วันที่:** {date_str or '-'}\n\n"
            f"⏰ **เวลา:** {start_time_str or '-'} - {end_time_str or '-'}"
        )
        return Response({"type": "message", "text": msg})

    def handle_check_availability(self, result):
        date_str = result.get('date')
        if not date_str:
            return Response({"type": "message", "text": "📅 กรุณาระบุวันที่ด้วยครับ เช่น 'พรุ่งนี้ห้องไหนว่างบ้าง'"})

        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            rooms = Room.objects.all().order_by('code')
            msg = f"🔍 **รายการห้องว่างวันที่ {date_str}**\n\n"

            for room in rooms:
                day_start = time(8, 0)
                day_end = time(18, 0)
                
                # Check blackout periods affecting this day
                blackouts = BlackoutPeriod.objects.filter(
                    Q(room=room) | Q(room__isnull=True),
                    start_date__lte=target_date,
                    end_date__gte=target_date
                )
                
                # Check bookings active on this day
                bookings = Booking.objects.filter(
                    room=room,
                    status__in=['APPROVED', 'PENDING'],
                    start_date__lte=target_date,
                    end_date__gte=target_date
                ).order_by('start_time')

                blocked_intervals = []
                # Add blackouts as blocked intervals
                for bp in blackouts:
                    bp_start = bp.start_time or time(0, 0)
                    bp_end = bp.end_time or time(23, 59, 59)
                    blocked_intervals.append((bp_start, bp_end, f"ปิดปรับปรุง: {bp.title}"))
                
                # Add bookings as blocked intervals
                for b in bookings:
                    desc = f"{b.course_code or ''} {b.course_name or b.training_title or ''}".strip() or "จองแล้ว"
                    blocked_intervals.append((b.start_time, b.end_time, desc))

                # Sort blocked intervals by start time
                blocked_intervals.sort(key=lambda x: x[0])

                free_slots = []
                current_time = day_start
                for start, end, label in blocked_intervals:
                    if start > current_time:
                        free_slots.append(f"{current_time.strftime('%H:%M')}-{start.strftime('%H:%M')}")
                    current_time = max(current_time, end)
                if current_time < day_end:
                    free_slots.append(f"{current_time.strftime('%H:%M')}-{day_end.strftime('%H:%M')}")

                slots_text = ", ".join(free_slots) if free_slots else "❌ เต็มทุกช่วงเวลา"
                msg += f"🚪 **ห้อง {room.code}**: {slots_text}\n\n"

            return Response({"type": "message", "text": msg})
        except Exception as e:
            return Response({"type": "message", "text": f"⚠️ เกิดข้อผิดพลาด: {str(e)}"})

    def handle_check_room(self, result):
        room_id = result.get('room_id')
        date_str = result.get('date')

        if not room_id or not date_str:
            return Response({"type": "message", "text": "❓ กรุณาระบุเลขห้องและวันที่ครับ เช่น 'ห้อง 406-3 พรุ่งนี้ว่างช่วงไหนบ้าง'"})

        try:
            room = Room.objects.get(code=room_id)
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            day_start = time(8, 0)
            day_end = time(18, 0)

            # Check blackout periods affecting this day
            blackouts = BlackoutPeriod.objects.filter(
                Q(room=room) | Q(room__isnull=True),
                start_date__lte=target_date,
                end_date__gte=target_date
            )

            # Check bookings active on this day
            bookings = Booking.objects.filter(
                room=room,
                status__in=['APPROVED', 'PENDING'],
                start_date__lte=target_date,
                end_date__gte=target_date
            ).order_by('start_time')

            blocked_intervals = []
            for bp in blackouts:
                bp_start = bp.start_time or time(0, 0)
                bp_end = bp.end_time or time(23, 59, 59)
                blocked_intervals.append((bp_start, bp_end, f"ปิดปรับปรุง: {bp.title}"))
            for b in bookings:
                desc = f"{b.course_code or ''} {b.course_name or b.training_title or ''}".strip() or "จองแล้ว"
                blocked_intervals.append((b.start_time, b.end_time, desc))

            blocked_intervals.sort(key=lambda x: x[0])

            free_slots = []
            current_time = day_start
            for start, end, label in blocked_intervals:
                if start > current_time:
                    free_slots.append(f"{current_time.strftime('%H:%M')}-{start.strftime('%H:%M')}")
                current_time = max(current_time, end)
            if current_time < day_end:
                free_slots.append(f"{current_time.strftime('%H:%M')}-{day_end.strftime('%H:%M')}")

            msg = f"🚪 **ห้อง {room_id}** วันที่ {date_str}\n\n"
            if free_slots:
                msg += "**ช่วงที่ว่าง:**\n\n" + "\n\n".join(f"✅ {s}" for s in free_slots)
            else:
                msg += "❌ เต็มทุกช่วงเวลา (08:00-18:00)"

            if blocked_intervals:
                msg += "\n\n**ช่วงที่ไม่ว่าง:**\n\n"
                msg += "\n\n".join(
                    f"🔴 {start.strftime('%H:%M')}-{end.strftime('%H:%M')} ({label})"
                    for start, end, label in blocked_intervals
                )

            return Response({"type": "message", "text": msg})
        except Room.DoesNotExist:
            return Response({"type": "message", "text": f"❓ ไม่พบห้อง {room_id} ในระบบครับ"})
        except Exception as e:
            return Response({"type": "message", "text": f"⚠️ เกิดข้อผิดพลาด: {str(e)}"})

    def handle_my_bookings(self, username):
        now = datetime.now(TZ)
        current_date = now.date()
        current_time = now.time()
        
        # We want bookings where end_date > current_date OR (end_date == current_date and end_time >= current_time)
        bookings = Booking.objects.filter(
            booker_id=username,
            status__in=['PENDING', 'APPROVED']
        ).filter(
            Q(end_date__gt=current_date) | Q(end_date=current_date, end_time__gte=current_time)
        ).order_by('start_date', 'start_time')[:10]

        if not bookings.exists():
            return Response({"type": "message", "text": f"📋 ไม่พบการจองที่ค้างอยู่ของคุณครับ"})

        msg = f"📋 **การจองของ {username}**\n\n"
        for b in bookings:
            icon = "⏳" if b.status == 'PENDING' else "✅"
            desc = f"{b.course_code or ''} {b.course_name or b.training_title or ''}".strip() or "-"
            msg += (
                f"{icon} **#{b.id}** ห้อง **{b.room.code}**\n"
                f"   📅 {b.start_date.strftime('%d/%m/%Y')}  ⏰ {b.start_time.strftime('%H:%M')}-{b.end_time.strftime('%H:%M')}\n"
                f"   📌 {desc}  ({b.get_status_display()})\n\n"
            )
        return Response({"type": "message", "text": msg.strip()})

    def handle_cancel_booking(self, result, username):
        room_id = result.get('room_id')
        date_str = result.get('date')

        if not room_id or not date_str:
            return Response({"type": "message", "text": "❓ กรุณาระบุห้องและวันที่ที่ต้องการยกเลิกครับ เช่น 'ยกเลิกการจองห้อง 406-3 พรุ่งนี้'"})

        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            bookings = Booking.objects.filter(
                room__code=room_id,
                booker_id=username,
                start_date=target_date,
                status__in=['PENDING', 'APPROVED']
            )
            if not bookings.exists():
                return Response({"type": "message", "text": f"❓ ไม่พบการจองห้อง **{room_id}** วันที่ **{date_str}** ของคุณครับ"})

            count = bookings.count()
            for b in bookings:
                b.status = 'CANCELLED'
                b.save()
                
                # Log action
                BookingLog.objects.create(
                    booking=b,
                    action="CANCELLED",
                    actor=username
                )
            return Response({"type": "message", "text": f"✅ ยกเลิกการจองห้อง **{room_id}** วันที่ **{date_str}** แล้วครับ ({count} รายการ)"})
        except Exception as e:
            return Response({"type": "message", "text": f"⚠️ เกิดข้อผิดพลาด: {str(e)}"})

    def handle_admin_action(self, booking_id, new_status, reason, admin_name):
        try:
            # Handle UUID or partial UUID matching
            if len(booking_id) < 36:
                bookings = Booking.objects.filter(id__icontains=booking_id)
                if bookings.count() == 1:
                    booking = bookings.first()
                elif bookings.count() > 1:
                    return Response({"type": "message", "text": f"❓ พบหลาย Booking ที่ตรงกับ #{booking_id} กรุณาระบุรหัสเต็ม"})
                else:
                    return Response({"type": "message", "text": f"❓ ไม่พบ Booking #{booking_id} ครับ"})
            else:
                booking = Booking.objects.get(id=booking_id)

            booking.status = new_status
            booking.save()

            # Create log
            BookingLog.objects.create(
                booking=booking,
                action=new_status,
                actor=admin_name,
                metadata={"reason": reason} if reason else None
            )

            status_text = "✅ อนุมัติแล้ว" if new_status == 'APPROVED' else "❌ ปฏิเสธแล้ว"
            msg = (
                f"{status_text} **Booking #{booking.id}**\n\n"
                f"👤 ผู้จอง: {booking.booker_name or booking.booker_id}\n\n"
                f"🏢 ห้อง: {booking.room.code}\n\n"
                f"📅 วันที่: {booking.start_date.strftime('%d/%m/%Y')}\n\n"
                f"⏰ เวลา: {booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}\n\n"
                f"📌 วัตถุประสงค์: {booking.course_code or booking.training_title or '-'}\n\n"
                f"👨‍💼 โดย: {admin_name}"
            )
            if reason:
                msg += f"\n\n💬 เหตุผล: {reason}"

            # Proactive reply to original booking message in Teams
            if booking.teams_service_url and booking.teams_conversation_id:
                self._send_teams_reply(booking, msg)

            return Response({"type": "message", "text": msg})
        except Booking.DoesNotExist:
            return Response({"type": "message", "text": f"❓ ไม่พบ Booking #{booking_id} ครับ"})
        except Exception as e:
            return Response({"type": "message", "text": f"⚠️ เกิดข้อผิดพลาด: {str(e)}"})

    def _send_teams_reply(self, booking, msg):
        """Send a proactive reply to the original booking message thread."""
        try:
            url = (
                f"{booking.teams_service_url.rstrip('/')}"
                f"/v3/conversations/{booking.teams_conversation_id}"
                f"/activities/{booking.teams_activity_id}"
            )
            payload = {
                "type": "message",
                "text": msg,
                "replyToId": booking.teams_activity_id,
            }
            # Outgoing webhooks don't support proactive auth — log for now
            print(f"DEBUG: Would send Teams reply to {url}", flush=True)
            print(f"DEBUG: Payload: {payload}", flush=True)
        except Exception as e:
            print(f"DEBUG: Teams reply failed: {str(e)}", flush=True)
