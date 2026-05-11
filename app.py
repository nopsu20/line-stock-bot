"""
LINE Bot - Stock Analyzer with Support/Resistance Levels
ใช้ Twelve Data API (ฟรี 800 calls/วัน, รองรับ cloud IP)
"""
import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import pandas as pd
import numpy as np
import requests as std_requests

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')
TWELVE_DATA_API_KEY = os.environ.get('TWELVE_DATA_API_KEY', '')

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


@app.route("/", methods=['GET'])
def health():
    return "LINE Stock Bot is running ✅", 200


@app.route("/debug/<symbol>", methods=['GET'])
def debug_stock(symbol):
    """เปิดในเบราว์เซอร์เพื่อดูว่า Twelve Data ตอบอะไรกลับมา"""
    s = symbol.upper().strip()
    if s.endswith('-USD'):
        s = s.replace('-USD', '/USD')
    elif s.endswith('.BK'):
        s = s.replace('.BK', '')

    url = "https://api.twelvedata.com/time_series"
    params = {
        'symbol': s,
        'interval': '1day',
        'outputsize': 252,
        'apikey': TWELVE_DATA_API_KEY,
        'order': 'asc',
    }
    apikey_status = "set" if TWELVE_DATA_API_KEY else "NOT SET ❌"
    try:
        r = std_requests.get(url, params=params, timeout=15)
        body_preview = r.text[:800]
        return (
            f"Symbol: {s}\n"
            f"TWELVE_DATA_API_KEY: {apikey_status}\n"
            f"Status: {r.status_code}\n"
            f"Length: {len(r.text)}\n"
            f"--- Body Preview ---\n"
            f"{body_preview}"
        ), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}", 500


@app.route("/webhook", methods=['POST'])
def webhook():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


def fetch_twelvedata(symbol: str):
    """ดึงข้อมูลราคารายวันจาก Twelve Data API"""
    s = symbol.upper().strip()

    # แปลงรูปแบบ ticker
    if s.endswith('-USD'):
        # Crypto: BTC-USD -> BTC/USD
        s = s.replace('-USD', '/USD')
    elif s.endswith('.BK'):
        # Thai stocks: PTT.BK -> PTT (Twelve Data ใช้ชื่อสั้น)
        s = s.replace('.BK', '')

    url = "https://api.twelvedata.com/time_series"
    params = {
        'symbol': s,
        'interval': '1day',
        'outputsize': 252,
        'apikey': TWELVE_DATA_API_KEY,
        'order': 'asc',
    }
    try:
        r = std_requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        # ตรวจ error message
        if data.get('status') == 'error':
            return None
        values = data.get('values')
        if not values or len(values) < 20:
            return None
        df = pd.DataFrame(values)
        # แปลงเป็น float
        df['Open'] = df['open'].astype(float)
        df['High'] = df['high'].astype(float)
        df['Low'] = df['low'].astype(float)
        df['Close'] = df['close'].astype(float)
        return df[['Open', 'High', 'Low', 'Close']].reset_index(drop=True)
    except Exception:
        return None


def calc_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def trend_signal(close, sma50, sma200):
    if sma200 is None or sma50 is None:
        return "📊 ข้อมูลไม่พอประเมินเทรนด์ระยะยาว"
    if close > sma50 > sma200:
        return "🟢 เทรนด์ขาขึ้น (Uptrend)"
    if close < sma50 < sma200:
        return "🔴 เทรนด์ขาลง (Downtrend)"
    return "🟡 Sideways / กำลังเปลี่ยนเทรนด์"


def rsi_signal(rsi):
    if rsi >= 70:
        return "⚠️ Overbought (ซื้อมากไป)"
    if rsi <= 30:
        return "⚠️ Oversold (ขายมากไป)"
    return "✅ ปกติ"


def analyze_stock(symbol: str) -> str:
    try:
        symbol = symbol.upper().strip()
        df = fetch_twelvedata(symbol)

        if df is None or df.empty or len(df) < 20:
            return (
                f"❌ ไม่พบข้อมูลหุ้น '{symbol}'\n"
                "ลองตรวจ ticker เช่น AAPL, TSLA, NVDA\n"
                "หรือคริปโต BTC-USD, ETH-USD"
            )

        close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])
        high = float(df['High'].iloc[-1])
        low = float(df['Low'].iloc[-1])
        change_pct = (close - prev_close) / prev_close * 100

        # Pivot Point Classic
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)

        # Moving Averages
        sma20 = float(df['Close'].rolling(20).mean().iloc[-1])
        sma50 = float(df['Close'].rolling(50).mean().iloc[-1]) if len(df) >= 50 else None
        sma200 = float(df['Close'].rolling(200).mean().iloc[-1]) if len(df) >= 200 else None

        # Swing 20 วัน
        swing_high_20 = float(df['High'].rolling(20).max().iloc[-1])
        swing_low_20 = float(df['Low'].rolling(20).min().iloc[-1])

        # 52 สัปดาห์
        high_52w = float(df['High'].max())
        low_52w = float(df['Low'].min())

        rsi = calc_rsi(df['Close'])

        msg = []
        msg.append(f"📊 {symbol}")
        msg.append("━━━━━━━━━━━━━━━")
        msg.append(f"💰 ราคา: ${close:,.2f} ({change_pct:+.2f}%)")
        msg.append(f"📈 RSI(14): {rsi:.1f} {rsi_signal(rsi)}")
        msg.append(trend_signal(close, sma50, sma200))
        msg.append("")
        msg.append("🔴 แนวต้าน (Resistance)")
        msg.append(f"  R3: ${r3:,.2f}")
        msg.append(f"  R2: ${r2:,.2f}")
        msg.append(f"  R1: ${r1:,.2f}")
        msg.append(f"⚪ Pivot: ${pivot:,.2f}")
        msg.append("🟢 แนวรับ (Support)")
        msg.append(f"  S1: ${s1:,.2f}")
        msg.append(f"  S2: ${s2:,.2f}")
        msg.append(f"  S3: ${s3:,.2f}")
        msg.append("")
        msg.append("📐 Moving Averages")
        msg.append(f"  SMA20:  ${sma20:,.2f}")
        if sma50:
            msg.append(f"  SMA50:  ${sma50:,.2f}")
        if sma200:
            msg.append(f"  SMA200: ${sma200:,.2f}")
        msg.append("")
        msg.append("🎯 Swing 20 วัน")
        msg.append(f"  High: ${swing_high_20:,.2f}")
        msg.append(f"  Low:  ${swing_low_20:,.2f}")
        msg.append("")
        msg.append("📅 52 สัปดาห์")
        msg.append(f"  High: ${high_52w:,.2f}")
        msg.append(f"  Low:  ${low_52w:,.2f}")
        msg.append("")
        msg.append("📡 ข้อมูลจาก Twelve Data")

        return "\n".join(msg)
    except Exception as e:
        return f"⚠️ เกิดข้อผิดพลาด: {str(e)[:100]}"


HELP_TEXT = (
    "📖 วิธีใช้งาน LINE Stock Bot\n"
    "━━━━━━━━━━━━━━━\n"
    "พิมพ์ ticker หุ้นต่างประเทศ เช่น:\n"
    "• AAPL  (Apple)\n"
    "• TSLA  (Tesla)\n"
    "• NVDA  (NVIDIA)\n"
    "• MSFT  (Microsoft)\n"
    "• GOOGL (Google)\n\n"
    "คริปโต:\n"
    "• BTC-USD  (Bitcoin)\n"
    "• ETH-USD  (Ethereum)\n\n"
    "คำสั่งอื่น:\n"
    "• /help  - แสดงคำแนะนำ\n"
    "• /analyze AAPL  - วิเคราะห์หุ้น"
)


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    upper = text.upper()

    if upper in ('/HELP', 'HELP', 'ช่วย', 'วิธีใช้'):
        reply = HELP_TEXT
    elif upper.startswith('/ANALYZE '):
        reply = analyze_stock(upper.replace('/ANALYZE ', '', 1))
    elif upper.startswith('/'):
        reply = "❓ คำสั่งไม่ถูกต้อง พิมพ์ /help เพื่อดูวิธีใช้"
    else:
        if 1 <= len(text) <= 10 and text.replace('.', '').replace('-', '').isalnum():
            reply = analyze_stock(upper)
        else:
            reply = "❓ ไม่เข้าใจคำสั่ง พิมพ์ /help เพื่อดูวิธีใช้"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
