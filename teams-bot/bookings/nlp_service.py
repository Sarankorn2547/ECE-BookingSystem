import os
import json
import sys
from openai import OpenAI
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

# Set Timezone
TZ = pytz.timezone('Asia/Bangkok')

api_key = os.getenv("TYPHOON_API_KEY")

try:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.opentyphoon.ai/v1"
    )
except Exception as e:
    client = None

SYSTEM_PROMPT = """คุณเป็น booking assistant ของภาควิชา ECE หน้าที่ของคุณคือแปลงคำขอภาษาไทยเป็น JSON
**ข้อมูลปัจจุบัน (สำคัญมาก):**
วันนี้คือ: {current_date}

**หลักการคำนวณวันที่:**
1. ใช้ "{current_date}" เป็นจุดตั้งต้นเสมอ
2. "วันนี้" = วันที่ระบุข้างบน
3. "พรุ่งนี้" = วันถัดไป
4. "วันจันทร์/อังคาร/.../อาทิตย์" = ให้หาวันที่ของวันนั้นๆ ที่กำลังจะมาถึง (ถ้าวัดวันนี้ตรงกับวันที่ถาม ให้ถือว่าเป็นวันนี้)
5. หากผู้ใช้ระบุวันที่ (เช่น วันที่ 20) แต่เดือนนั้นผ่านวันที่ 20 ไปแล้ว ให้สันนิษฐานว่าเป็น "วันที่ 20 ของเดือนถัดไป"
6. หาก "วันในสัปดาห์" และ "วันที่" ขัดแย้งกัน (เช่น บอกวันศุกร์ที่ 20 แต่ปีนี้วันที่ 20 เป็นวันจันทร์) ให้ยึดตาม "วันที่" (20) เป็นหลัก แล้วคำนวณเดือน/ปีให้ถูกต้อง

**การแปลงเวลา (24 ชั่วโมง):**
- X โมงเช้า = 0X:00
- บ่าย X โมง = (X+12):00 (เช่น บ่าย 2 = 14:00)
- X ทุ่ม = (X+18):00 (เช่น 1 ทุ่ม = 19:00)
- เที่ยง = 12:00, เที่ยงคืน = 00:00
- หากระบุช่วง (เช่น บ่ายโมงถึงสามโมง) = start: 13:00, end: 15:00

**Output Format (JSON Only):**
1. create_booking: {{"intent": "create_booking", "room_id": "string", "date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM", "purpose": "string"}}
2. check_availability: {{"intent": "check_availability", "date": "YYYY-MM-DD"}}
3. check_room: {{"intent": "check_room", "room_id": "string", "date": "YYYY-MM-DD"}}
4. my_bookings: {{"intent": "my_bookings"}}
5. cancel_booking: {{"intent": "cancel_booking", "room_id": "string", "date": "YYYY-MM-DD"}}
6. help/unknown: ตามความเหมาะสม
"""

def parse_booking_request(text):
    if not client:
        return {"intent": "unknown", "error": "Client not initialized"}

    # Use Asia/Bangkok time for AI context
    now = datetime.now(TZ)
    current_date = now.strftime("%Y-%m-%d (%A)")

    try:
        response = client.chat.completions.create(
            model="typhoon-v2.5-30b-a3b-instruct",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(current_date=current_date)},
                {"role": "user", "content": text},
            ],
            temperature=0.0, # ลดความสร้างสรรค์ เพิ่มความแม่นยำ
            max_tokens=256,
        )
        content = response.choices[0].message.content.strip()
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)
    except Exception as e:
        return {"intent": "unknown"}
