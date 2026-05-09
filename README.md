# LINE Stock Bot — วิเคราะห์หุ้นต่างประเทศพร้อมแนวรับ/แนวต้าน

ส่งชื่อหุ้น (เช่น `AAPL`, `TSLA`, `NVDA`) ทาง LINE แล้วบอทจะตอบกลับด้วย:
- ราคา, % เปลี่ยนแปลง, RSI(14), เทรนด์
- แนวต้าน R1/R2/R3 + Pivot + แนวรับ S1/S2/S3
- SMA20 / SMA50 / SMA200
- Swing High/Low 20 วัน, High/Low 52 สัปดาห์

ข้อมูลดึงจาก Yahoo Finance ผ่าน `yfinance` (ฟรี ไม่ต้องสมัคร API key)

---

## ขั้นที่ 1 — สมัคร LINE Messaging API (ฟรี)

1. ไปที่ <https://developers.line.biz/console/> เข้าด้วย LINE Account
2. **Create a new provider** → ตั้งชื่อ
3. **Create a new channel** → เลือก **Messaging API**
4. กรอกข้อมูลพื้นฐานแล้วสร้าง
5. ไปแท็บ **Basic settings** → คัดลอก **Channel secret**
6. ไปแท็บ **Messaging API** → กดสร้าง **Channel access token (long-lived)** → คัดลอก
7. ในหน้านี้ ปิด **Auto-reply messages** (Edit → ปิด) เพื่อไม่ให้ชนกับบอทเรา

เก็บค่า 2 ตัวนี้ไว้:
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`

---

## ขั้นที่ 2 — Push โค้ดขึ้น GitHub

1. สร้าง repo ใหม่บน GitHub (private ก็ได้)
2. อัปโหลดไฟล์เหล่านี้: `app.py`, `requirements.txt`, `Procfile`, `runtime.txt`, `.gitignore`

หรือใช้ command line:
```bash
git init
git add .
git commit -m "init line stock bot"
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

---

## ขั้นที่ 3 — Deploy ฟรีบน Render.com

1. สมัคร <https://render.com> (ผูกบัญชี GitHub)
2. **New +** → **Web Service** → เลือก repo ที่เพิ่งสร้าง
3. ตั้งค่า:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120`
   - **Instance Type**: **Free**
4. กด **Advanced** → **Add Environment Variable**:
   - `LINE_CHANNEL_ACCESS_TOKEN` = ค่าจากขั้นที่ 1
   - `LINE_CHANNEL_SECRET` = ค่าจากขั้นที่ 1
5. **Create Web Service** → รอ build เสร็จ (~3-5 นาที)
6. คัดลอก URL ที่ได้ เช่น `https://line-stock-bot.onrender.com`

> หมายเหตุ Free tier: เซิร์ฟเวอร์จะ "หลับ" หลังไม่มี traffic ~15 นาที ครั้งแรกที่กลับมาใช้จะตอบช้า ~30-50 วินาที จากนั้นกลับมาเร็วปกติ

---

## ขั้นที่ 4 — ตั้ง Webhook URL ที่ LINE

1. กลับไปที่ LINE Developers Console → channel ของเรา → แท็บ **Messaging API**
2. **Webhook URL** = `https://<ชื่อ-app-คุณ>.onrender.com/webhook`
3. กด **Update** → กด **Verify** ต้องขึ้น `Success`
4. เปิด **Use webhook** ให้เป็น `On`
5. แท็บนี้จะมี **QR code** ให้เพิ่มเพื่อนกับบอท → สแกนด้วย LINE มือถือ

---

## ขั้นที่ 5 — ลองใช้

ในแชต LINE กับบอท พิมพ์:
```
AAPL
```
หรือ
```
/analyze TSLA
```

จะได้ผลประมาณนี้:
```
📊 AAPL
━━━━━━━━━━━━━━━
💰 ราคา: $189.45 (+1.23%)
📈 RSI(14): 58.3 ✅ ปกติ
🟢 เทรนด์ขาขึ้น (Uptrend)

🔴 แนวต้าน (Resistance)
  R3: $195.20
  R2: $192.80
  R1: $191.10
⚪ Pivot: $189.00
🟢 แนวรับ (Support)
  S1: $187.30
  S2: $185.20
  S3: $182.90

📐 Moving Averages
  SMA20:  $186.40
  SMA50:  $182.15
  SMA200: $175.80
...
```

---

## รัน Local เพื่อทดสอบก่อน deploy (optional)

```bash
python -m venv venv
source venv/bin/activate          # Mac/Linux
# หรือ venv\Scripts\activate     # Windows
pip install -r requirements.txt
export LINE_CHANNEL_ACCESS_TOKEN="..."
export LINE_CHANNEL_SECRET="..."
python app.py
```

ใช้ [ngrok](https://ngrok.com) เปิด public URL: `ngrok http 5000`
แล้วเอา URL ที่ได้ + `/webhook` ไปใส่ในช่อง Webhook URL ของ LINE

---

## ปรับแต่งเพิ่มเติม

ในไฟล์ `app.py` แก้ฟังก์ชัน `analyze_stock()` ได้ตามต้องการ เช่น:
- เปลี่ยนช่วงเวลา: `period="1y"` → `"6mo"`, `"2y"`, `"5y"`
- เพิ่ม Fibonacci Retracement
- เพิ่ม MACD, Bollinger Bands (ใช้ `pandas-ta`)
- ส่งกราฟเป็นรูป (ImageSendMessage + matplotlib + อัปโหลดไป Imgur/S3)

## หุ้นที่รองรับ

ใส่ ticker ตามมาตรฐาน Yahoo Finance:
- หุ้นสหรัฐฯ: `AAPL`, `TSLA`, `MSFT`, `GOOGL`, `META`, `AMZN`, `NVDA`
- ETF: `SPY`, `QQQ`, `VOO`, `ARKK`
- คริปโต: `BTC-USD`, `ETH-USD`
- ทอง/น้ำมัน: `GC=F`, `CL=F`
- หุ้นไทย: `PTT.BK`, `KBANK.BK`, `CPALL.BK`
