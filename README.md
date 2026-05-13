# LINE Stock Bot — วิเคราะห์หุ้นต่างประเทศพร้อมแนวรับ/แนวต้าน

LINE Bot สำหรับวิเคราะห์หุ้นต่างประเทศแบบเรียลไทม์ ตอบกลับด้วย Pivot Points, RSI, Moving Averages, แนวรับ/แนวต้าน และคัด Top Picks ตาม mega-trend sectors

**Live Demo:** ดูตัวอย่างผลลัพธ์ในข้อ "คำสั่งที่ใช้ได้" ด้านล่าง
**ภาษา:** Python 3.11 (Flask)
**Hosting:** Render.com (Free tier)
**Data Source:** Twelve Data API (Free tier — 800 calls/วัน)

---

## คำสั่งที่ใช้ได้

| คำสั่ง | ตัวอย่าง | ผลลัพธ์ |
|---|---|---|
| พิมพ์ ticker | `AAPL` | วิเคราะห์ราคา + RSI + SMA + แนวรับ/แนวต้าน R1-R3, S1-S3 |
| `/sectors` | — | รายการ 9 mega-trend sectors |
| `/top AI` | — | Top 5 หุ้น AI พร้อมราคา + thesis |
| `/top SEMI` | — | Top 5 หุ้นเซมิคอนดักเตอร์ |
| `/top FINTECH` | — | Top 5 หุ้นเทคโนโลยีการเงิน |
| `/top CYBER` | — | Top 5 หุ้นความปลอดภัยไซเบอร์ |
| `/top CLOUD` | — | Top 5 หุ้นคลาวด์ |
| `/top EV` | — | Top 5 หุ้นรถยนต์ไฟฟ้า/พลังงาน |
| `/top BIO` | — | Top 5 หุ้นไบโอเทค/ยา |
| `/top DEFENSE` | — | Top 5 หุ้นกลาโหม/อวกาศ |
| `/top DIV` | — | Top 5 หุ้นปันผลพร้อม Yield |
| `/help` | — | คู่มือการใช้งาน |

---

## ขั้นที่ 1 — สมัคร LINE Messaging API (ฟรี)

1. ไปที่ <https://developers.line.biz/console/>
2. **Create a new provider** → ตั้งชื่อ
3. **Create a new channel** → เลือก **Messaging API**
4. ไปแท็บ **Basic settings** → คัดลอก **Channel secret**
5. ไปแท็บ **Messaging API** → กดสร้าง **Channel access token (long-lived)**
6. ปิด **Auto-reply messages** ไม่ให้ชนกับบอท

เก็บค่าไว้:
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`

---

## ขั้นที่ 2 — สมัคร Twelve Data API (ฟรี)

1. ไปที่ <https://twelvedata.com/register>
2. กรอก email + password → ยืนยัน email
3. หลังล็อกอินจะเห็น **API key** ใน dashboard → คัดลอก

เก็บค่าไว้:
- `TWELVE_DATA_API_KEY`

> Free tier: 800 calls/วัน, 8 calls/นาที — เพียงพอสำหรับใช้ส่วนตัวและกลุ่มเล็ก

---

## ขั้นที่ 3 — Push โค้ดขึ้น GitHub

ไฟล์ที่ต้องมี (4 ไฟล์):
- `app.py` — โค้ดหลัก
- `requirements.txt` — Python dependencies
- `Procfile` — บอก Render วิธีรัน
- `runtime.txt` — Python version

อัปโหลดผ่านเว็บ GitHub ตรงๆ ได้ (ไม่ต้องใช้ git command line)

---

## ขั้นที่ 4 — Deploy บน Render.com (ฟรี)

1. สมัคร <https://render.com> (Sign in with GitHub)
2. **+ New** → **Web Service** → เลือก repo
3. ตั้งค่า:
   - **Language**: Python 3
   - **Region**: Singapore
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120`
   - **Instance Type**: **Free**
4. เพิ่ม **Environment Variables** 3 ตัว:
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `LINE_CHANNEL_SECRET`
   - `TWELVE_DATA_API_KEY`
5. กด **Create Web Service** → รอ build ~5 นาที
6. คัดลอก URL ที่ได้ เช่น `https://line-stock-bot-xxxx.onrender.com`

---

## ขั้นที่ 5 — ตั้ง Webhook URL ใน LINE

1. กลับไป LINE Developers Console → channel → แท็บ **Messaging API**
2. **Webhook URL** = `https://<your-app>.onrender.com/webhook`
3. กด **Update** → **Verify** → ต้องขึ้น `Success`
4. เปิด **Use webhook** = On

---

## ขั้นที่ 6 — ทดสอบ

1. สแกน QR code ใน Developers Console เพิ่มบอทเป็นเพื่อน
2. พิมพ์ `/help` → ดูคำสั่งทั้งหมด
3. พิมพ์ `AAPL` → วิเคราะห์ Apple
4. พิมพ์ `/top AI` → Top 5 หุ้น AI

---

## ป้องกัน Render Free Tier "หลับ" (Optional)

Render Free tier จะ spin down หลังไม่มี traffic 15 นาที → ตอบช้าครั้งแรก 30-50 วินาที

แก้ด้วย **UptimeRobot** (ฟรี):
1. สมัคร <https://uptimerobot.com>
2. + New Monitor → HTTP(s) → URL คือ Render URL ของคุณ
3. Monitoring Interval: 5 minutes

---

## Mega-Trend Sectors ที่รองรับ

| Code | กลุ่ม | หุ้นในกลุ่ม |
|---|---|---|
| AI | ปัญญาประดิษฐ์ | NVDA, MSFT, META, GOOGL, PLTR |
| SEMI | เซมิคอนดักเตอร์ | NVDA, TSM, AMD, ASML, AVGO |
| FINTECH | เทคโนโลยีการเงิน | V, MA, PYPL, SQ, HOOD |
| CYBER | ความปลอดภัยไซเบอร์ | CRWD, PANW, ZS, FTNT, S |
| CLOUD | คลาวด์คอมพิวติ้ง | AMZN, MSFT, GOOGL, ORCL, NOW |
| EV | ยานยนต์ไฟฟ้า/พลังงาน | TSLA, ENPH, FSLR, NEE, LCID |
| BIO | ไบโอเทค / ยา | LLY, NVO, VRTX, REGN, AMGN |
| DEFENSE | กลาโหม / อวกาศ | LMT, RTX, PLTR, KTOS, BA |
| DIV | หุ้นปันผลสูง | JNJ, KO, O, PG, XOM |

---

## โครงสร้างโปรเจกต์

```
line-stock-bot/
├── app.py             # โค้ดหลัก (Flask + LINE handler + analyzer)
├── requirements.txt   # Python dependencies
├── Procfile          # Render start command
├── runtime.txt       # Python version (3.11.9)
└── README.md         # คู่มือนี้
```

---

## Tech Stack

- **Python 3.11** + **Flask 3.0**
- **line-bot-sdk** — LINE Messaging API
- **pandas + numpy** — คำนวณ technical indicators
- **requests** — เรียก Twelve Data API
- **gunicorn** — production WSGI server
- **Twelve Data API** — ข้อมูลราคาหุ้นรายวัน

---

## Disclaimer

ข้อมูลและการวิเคราะห์จากบอทนี้เป็นข้อมูลเชิงเทคนิคเพื่อการศึกษาเท่านั้น **ไม่ใช่คำแนะนำการลงทุน** การลงทุนมีความเสี่ยง ผู้ใช้ควรศึกษาข้อมูลและตัดสินใจด้วยตนเอง (DYOR — Do Your Own Research)

---

## License

MIT License — ใช้/แก้ไข/แจกจ่ายได้ตามต้องการ
