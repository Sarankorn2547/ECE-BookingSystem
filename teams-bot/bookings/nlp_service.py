import os
import json
import sys
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("TYPHOON_API_KEY")
print(f"DEBUG: API Key exists: {bool(api_key)}", file=sys.stderr, flush=True)

try:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.opentyphoon.ai/v1"
    )
    print("DEBUG: Typhoon Client initialized successfully", file=sys.stderr, flush=True)
except Exception as e:
    print(f"DEBUG: Typhoon Client init FAILED: {str(e)}", file=sys.stderr, flush=True)
    client = None

SYSTEM_PROMPT = """คุณเป็น booking assistant ของภาควิชา ECE หน้าที่ของคุณคือแปลงคำขอภาษาไทยเป็น JSON
วันนี้คือ: {current_date}

การแปลงวันที่:
- วันนี้ = today
- พรุ่งนี้ = tomorrow
- มะรืนนี้ / วันมะรื่นนี้ = day after tomorrow
- วันจันทร์ / อังคาร / พุธ / พฤหัส / ศุกร์ / เสาร์ / อาทิตย์ = next occurrence of that weekday

การแปลงเวลา (24 ชั่วโมง):
- X โมงเช้า = 0X:00 (เช่น 9 โมง = 09:00)
- บ่าย X โมง = 1X:00 (เช่น บ่าย 2 โมง = 14:00)
- X ทุ่ม = (X+18):00 (เช่น 1 ทุ่ม = 19:00)
- เที่ยง = 12:00

Intent และ output format (ตอบเป็น JSON เท่านั้น ไม่มีข้อความอื่น):

1. create_booking — ต้องการจองห้อง
{{"intent": "create_booking", "room_id": "string", "date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM", "purpose": "string"}}

2. check_availability — ถามว่าวันนั้นห้องไหนว่างบ้าง (ไม่ระบุห้อง)
{{"intent": "check_availability", "date": "YYYY-MM-DD"}}

3. check_room — ถามว่าห้องที่ระบุว่างช่วงไหน
{{"intent": "check_room", "room_id": "string", "date": "YYYY-MM-DD"}}

4. my_bookings — ดูการจองของตัวเอง
{{"intent": "my_bookings"}}

5. cancel_booking — ยกเลิกการจอง
{{"intent": "cancel_booking", "room_id": "string", "date": "YYYY-MM-DD"}}

6. help — ถามว่า bot ทำอะไรได้บ้าง
{{"intent": "help"}}

7. unknown — ไม่เข้าใจคำสั่ง
{{"intent": "unknown"}}

กฎ:
- ถ้าไม่มี end_time ให้บวก 1 ชั่วโมงจาก start_time
- room_id format: "406-3", "407-1", "408-2/1"
- คำนวณวันที่จริง YYYY-MM-DD จากคำบอกวันที่สัมพัทธ์

ตัวอย่าง:
User: จองห้อง 406-3 พรุ่งนี้ 9 โมงถึง 10 โมง สอนวิชา CN332
Output: {{"intent": "create_booking", "room_id": "406-3", "date": "YYYY-MM-DD", "start_time": "09:00", "end_time": "10:00", "purpose": "สอนวิชา CN332"}}

User: วันมะรื่นนี้ห้องไหนว่างบ้าง
Output: {{"intent": "check_availability", "date": "YYYY-MM-DD"}}

User: ห้อง 406-3 พรุ่งนี้ว่างช่วงไหนบ้าง
Output: {{"intent": "check_room", "room_id": "406-3", "date": "YYYY-MM-DD"}}

User: ดูการจองของฉัน
Output: {{"intent": "my_bookings"}}

User: ยกเลิกการจองห้อง 406-3 พรุ่งนี้
Output: {{"intent": "cancel_booking", "room_id": "406-3", "date": "YYYY-MM-DD"}}

User: help
Output: {{"intent": "help"}}
"""

def parse_booking_request(text):
    print(f"DEBUG: Entering parse_booking_request with text: {text}", file=sys.stderr, flush=True)
    if not client:
        return {"intent": "unknown", "error": "Client not initialized"}

    current_date = datetime.now().strftime("%Y-%m-%d (%A)")

    try:
        response = client.chat.completions.create(
            model="typhoon-v2.5-30b-a3b-instruct",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(current_date=current_date)},
                {"role": "user", "content": text},
            ],
            temperature=0.1,
            max_tokens=256,
        )
        content = response.choices[0].message.content.strip()
        print(f"DEBUG: Typhoon Response received: {content}", file=sys.stderr, flush=True)

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)
    except Exception as e:
        print(f"DEBUG: EXCEPTION in parse: {str(e)}", file=sys.stderr, flush=True)
        return {"intent": "unknown"}
