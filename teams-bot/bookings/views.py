import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .nlp_service import parse_booking_request
from .models import Room, Booking
from datetime import datetime, time
import pytz

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
    "• อนุมัติ #5 — อนุมัติ booking ID 5\n"
    "• ปฏิเสธ #5 เหตุผล... — ปฏิเสธพร้อมเหตุผล"
)


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

        # Admin commands: อนุมัติ #5 / ปฏิเสธ #5 เหตุผล
        admin_match = re.match(r'^(อนุมัติ|ปฏิเสธ)\s+#?(\d+)(?:\s+(.+))?$', clean_text.strip())
        if admin_match:
            action, booking_id, reason = admin_match.group(1), int(admin_match.group(2)), admin_match.group(3) or ''
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
        if room_id and date_str and start_time_str and end_time_str:
            try:
                room = Room.objects.get(room_id=room_id)
                start_dt = TZ.localize(datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M"))
                end_dt = TZ.localize(datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M"))

                conflicts = Booking.objects.filter(
                    room=room,
                    status__in=['APPROVED', 'PENDING'],
                    start_time__lt=end_dt,
                    end_time__gt=start_dt
                )

                if conflicts.exists():
                    save_status = "conflict"
                else:
                    Booking.objects.create(
                        room=room,
                        user_name=username,
                        start_time=start_dt,
                        end_time=end_dt,
                        purpose=purpose,
                        status='PENDING',
                        teams_service_url=teams_context.get('service_url', ''),
                        teams_conversation_id=teams_context.get('conversation_id', ''),
                        teams_activity_id=teams_context.get('activity_id', ''),
                    )
                    save_status = "success"
            except Room.DoesNotExist:
                save_status = "room_not_found"
            except Exception:
                save_status = "error"

        if save_status == "success":
            msg = f"✅ **จองห้องสำเร็จ (รออนุมัติ)**\n\n"
        elif save_status == "conflict":
            msg = f"❌ **จองไม่สำเร็จ: ห้องไม่ว่าง**\n\n"
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
            rooms = Room.objects.all()
            msg = f"🔍 **รายการห้องว่างวันที่ {date_str}**\n\n"

            for room in rooms:
                day_start = TZ.localize(datetime.combine(target_date, time(8, 0)))
                day_end = TZ.localize(datetime.combine(target_date, time(18, 0)))
                bookings = Booking.objects.filter(
                    room=room,
                    status__in=['APPROVED', 'PENDING'],
                    start_time__date=target_date
                ).order_by('start_time')

                free_slots = []
                current_time = day_start
                for b in bookings:
                    b_start = b.start_time.astimezone(TZ)
                    if b_start > current_time:
                        free_slots.append(f"{current_time.strftime('%H:%M')}-{b_start.strftime('%H:%M')}")
                    current_time = max(current_time, b.end_time.astimezone(TZ))
                if current_time < day_end:
                    free_slots.append(f"{current_time.strftime('%H:%M')}-{day_end.strftime('%H:%M')}")

                slots_text = ", ".join(free_slots) if free_slots else "❌ เต็มทุกช่วงเวลา"
                msg += f"🚪 **ห้อง {room.room_id}**: {slots_text}\n\n"

            return Response({"type": "message", "text": msg})
        except Exception as e:
            return Response({"type": "message", "text": f"⚠️ เกิดข้อผิดพลาด: {str(e)}"})

    def handle_check_room(self, result):
        room_id = result.get('room_id')
        date_str = result.get('date')

        if not room_id or not date_str:
            return Response({"type": "message", "text": "❓ กรุณาระบุเลขห้องและวันที่ครับ เช่น 'ห้อง 406-3 พรุ่งนี้ว่างช่วงไหนบ้าง'"})

        try:
            room = Room.objects.get(room_id=room_id)
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            day_start = TZ.localize(datetime.combine(target_date, time(8, 0)))
            day_end = TZ.localize(datetime.combine(target_date, time(18, 0)))

            bookings = Booking.objects.filter(
                room=room,
                status__in=['APPROVED', 'PENDING'],
                start_time__date=target_date
            ).order_by('start_time')

            free_slots = []
            current_time = day_start
            for b in bookings:
                b_start = b.start_time.astimezone(TZ)
                if b_start > current_time:
                    free_slots.append(f"{current_time.strftime('%H:%M')}-{b_start.strftime('%H:%M')}")
                current_time = max(current_time, b.end_time.astimezone(TZ))
            if current_time < day_end:
                free_slots.append(f"{current_time.strftime('%H:%M')}-{day_end.strftime('%H:%M')}")

            msg = f"🚪 **ห้อง {room_id}** วันที่ {date_str}\n\n"
            if free_slots:
                msg += "**ช่วงที่ว่าง:**\n\n" + "\n\n".join(f"✅ {s}" for s in free_slots)
            else:
                msg += "❌ เต็มทุกช่วงเวลา (08:00-18:00)"

            if bookings.exists():
                msg += "\n\n**ช่วงที่จองแล้ว:**\n\n"
                msg += "\n\n".join(
                    f"🔴 {b.start_time.astimezone(TZ).strftime('%H:%M')}-{b.end_time.astimezone(TZ).strftime('%H:%M')} ({b.purpose or '-'})"
                    for b in bookings
                )

            return Response({"type": "message", "text": msg})
        except Room.DoesNotExist:
            return Response({"type": "message", "text": f"❓ ไม่พบห้อง {room_id} ในระบบครับ"})
        except Exception as e:
            return Response({"type": "message", "text": f"⚠️ เกิดข้อผิดพลาด: {str(e)}"})

    def handle_my_bookings(self, username):
        now = datetime.now(TZ)
        bookings = Booking.objects.filter(
            user_name=username,
            end_time__gte=now,
            status__in=['PENDING', 'APPROVED']
        ).order_by('start_time')[:10]

        if not bookings.exists():
            return Response({"type": "message", "text": f"📋 ไม่พบการจองที่ค้างอยู่ของคุณครับ"})

        msg = f"📋 **การจองของ {username}**\n\n"
        for b in bookings:
            start_local = b.start_time.astimezone(TZ)
            end_local = b.end_time.astimezone(TZ)
            icon = "⏳" if b.status == 'PENDING' else "✅"
            msg += (
                f"{icon} **#{b.id}** ห้อง **{b.room.room_id}**\n"
                f"   📅 {start_local.strftime('%d/%m/%Y')}  ⏰ {start_local.strftime('%H:%M')}-{end_local.strftime('%H:%M')}\n"
                f"   📌 {b.purpose or '-'}  ({b.get_status_display()})\n\n"
            )
        return Response({"type": "message", "text": msg.strip()})

    def handle_cancel_booking(self, result, username):
        room_id = result.get('room_id')
        date_str = result.get('date')

        if not room_id or not date_str:
            return Response({"type": "message", "text": "❓ กรุณาระบุห้องและวันที่ที่ต้องการยกเลิกครับ เช่น 'ยกเลิกการจองห้อง 406-3 พรุ่งนี้'"})

        try:
            bookings = Booking.objects.filter(
                room__room_id=room_id,
                user_name=username,
                start_time__date=date_str,
                status__in=['PENDING', 'APPROVED']
            )
            if not bookings.exists():
                return Response({"type": "message", "text": f"❓ ไม่พบการจองห้อง **{room_id}** วันที่ **{date_str}** ของคุณครับ"})

            count = bookings.count()
            bookings.delete()
            return Response({"type": "message", "text": f"✅ ยกเลิกการจองห้อง **{room_id}** วันที่ **{date_str}** แล้วครับ ({count} รายการ)"})
        except Exception as e:
            return Response({"type": "message", "text": f"⚠️ เกิดข้อผิดพลาด: {str(e)}"})

    def handle_admin_action(self, booking_id, new_status, reason, admin_name):
        try:
            booking = Booking.objects.get(id=booking_id)
            booking.status = new_status
            booking.save()

            status_text = "✅ อนุมัติแล้ว" if new_status == 'APPROVED' else "❌ ปฏิเสธแล้ว"
            start_local = booking.start_time.astimezone(TZ)
            end_local = booking.end_time.astimezone(TZ)

            msg = (
                f"{status_text} **Booking #{booking_id}**\n\n"
                f"👤 ผู้จอง: {booking.user_name}\n\n"
                f"🏢 ห้อง: {booking.room.room_id}\n\n"
                f"📅 วันที่: {start_local.strftime('%d/%m/%Y')}\n\n"
                f"⏰ เวลา: {start_local.strftime('%H:%M')}-{end_local.strftime('%H:%M')}\n\n"
                f"📌 วัตถุประสงค์: {booking.purpose or '-'}\n\n"
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
