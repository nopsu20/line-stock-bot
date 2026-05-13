"""
LINE Bot - Stock Analyzer with Sector Top Picks
ใช้ Twelve Data API + cache 30 นาที
"""
import os
import time
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

# ---------- Sector Definitions ----------
SECTORS = {
    'AI': {
        'name': '🤖 Artificial Intelligence',
        'tickers': ['NVDA', 'MSFT', 'META', 'GOOGL', 'PLTR'],
        'theses': {
            'NVDA':  'GPU ผูกขาดตลาด AI training/inference',
            'MSFT':  'Azure + OpenAI partnership ครอบ enterprise',
            'META':  'Llama open-source + AI ads + Reality Labs',
            'GOOGL': 'Gemini + ทุก product Google ใส่ AI',
            'PLTR':  'AIP for enterprise + government AI',
        },
    },
    'SEMI': {
        'name': '💾 Semiconductors',
        'tickers': ['NVDA', 'TSM', 'AMD', 'ASML', 'AVGO'],
        'theses': {
            'NVDA':  'AI GPU leader',
            'TSM':   'World #1 foundry — สร้างชิป AI ทุกค่าย',
            'AMD':   'CPU/GPU คู่แข่ง NVDA + Intel',
            'ASML':  'ผูกขาด EUV lithography เครื่องเดียวในโลก',
            'AVGO':  'Custom AI silicon + VMware enterprise',
        },
    },
    'FINTECH': {
        'name': '💳 Fintech',
        'tickers': ['V', 'MA', 'PYPL', 'SQ', 'HOOD'],
        'theses': {
            'V':    'Payment rails ระดับโลก — โตตาม consumer spending',
            'MA':   'รายที่ 2 ของ payment rails ขนาดเดียวกัน Visa',
            'PYPL': 'Digital wallet ทั่วโลก + Braintree',
            'SQ':   'Cash App + Square merchant',
            'HOOD': 'Retail brokerage โต + Crypto + Tokenization',
        },
    },
    'CYBER': {
        'name': '🛡️ Cybersecurity',
        'tickers': ['CRWD', 'PANW', 'ZS', 'FTNT', 'S'],
        'theses': {
            'CRWD': 'Endpoint security cloud-native #1',
            'PANW': 'Network security platform ครบสุด',
            'ZS':   'Zero-trust SASE pure-play',
            'FTNT': 'Firewall + SASE คุ้มสุดในกลุ่ม',
            'S':    'AI-driven endpoint คู่แข่ง CRWD',
        },
    },
    'CLOUD': {
        'name': '☁️ Cloud Computing',
        'tickers': ['AMZN', 'MSFT', 'GOOGL', 'ORCL', 'NOW'],
        'theses': {
            'AMZN':  'AWS — cloud อันดับ 1',
            'MSFT':  'Azure — cloud อันดับ 2 + AI integration',
            'GOOGL': 'GCP — เติบโตเร็วสุดในกลุ่ม',
            'ORCL':  'OCI + AI workload จาก database',
            'NOW':   'ServiceNow — enterprise workflow platform',
        },
    },
    'EV': {
        'name': '🔋 EV & Energy',
        'tickers': ['TSLA', 'ENPH', 'FSLR', 'NEE', 'LCID'],
        'theses': {
            'TSLA': 'EV + Energy storage + FSD + Optimus',
            'ENPH': 'Solar microinverter ผู้นำ residential',
            'FSLR': 'Solar panel ผลิตในอเมริกา + IRA tailwind',
            'NEE':  'Clean utility ขนาดใหญ่สุดในอเมริกา',
            'LCID': 'Premium EV — Saudi PIF หนุน',
        },
    },
    'BIO': {
        'name': '🧬 Biotech / Pharma',
        'tickers': ['LLY', 'NVO', 'VRTX', 'REGN', 'AMGN'],
        'theses': {
            'LLY':  'GLP-1 (Mounjaro/Zepbound) + Alzheimer',
            'NVO':  'GLP-1 (Ozempic/Wegovy) ผู้นำในกลุ่ม',
            'VRTX': 'Cystic fibrosis monopoly + pain pipeline',
            'REGN': 'Eylea + immunology + obesity pipeline',
            'AMGN': 'Biologics ใหญ่ + GLP-1 oral pipeline',
        },
    },
    'DEFENSE': {
        'name': '🚀 Defense & Space',
        'tickers': ['LMT', 'RTX', 'PLTR', 'KTOS', 'BA'],
        'theses': {
            'LMT':  'F-35 + missile + space — defense ผู้นำ',
            'RTX':  'Patriot + GTF engine + missile',
            'PLTR': 'Software AI สำหรับ defense + commercial',
            'KTOS': 'Drone + satellite + hypersonic',
            'BA':   'Aerospace ใหญ่สุด + defense + space',
        },
    },
    'DIV': {
        'name': '💰 Dividend Stocks',
        'tickers': ['JNJ', 'KO', 'O', 'PG', 'XOM'],
        'theses': {
            'JNJ': 'Healthcare blue chip — Dividend King',
            'KO':  'Coca-Cola — Dividend King 60+ ปี',
            'O':   'REIT จ่ายปันผลรายเดือน',
            'PG':  'P&G สินค้าอุปโภค — Dividend King',
            'XOM': 'พลังงานยักษ์ใหญ่ ปันผลสูง',
        },
        # yield คงที่ (approximate, ปรับได้ตามจริง)
        'yields': {
            'JNJ': 3.2,
            'KO':  3.0,
            'O':   5.5,
            'PG':  2.5,
            'XOM': 3.5,
        },
    },
}

# ---------- Simple Cache (memory, 30 นาที) ----------
CACHE = {}
CACHE_TTL = 30 * 60


def cache_get(key):
    if key in CACHE:
        ts, value = CACHE[key]
        if time.time() - ts < CACHE_TTL:
            return value
    return None


def cache_set(key, value):
    CACHE[key] = (time.time(), value)


# ---------- Flask Routes ----------
@app.route("/", methods=['GET'])
def health():
    return "LINE Stock Bot is running ✅", 200


@app.route("/debug/<symbol>", methods=['GET'])
def debug_stock(symbol):
    s = symbol.upper().strip()
    if s.endswith('.BK'):
        s = s.replace('.BK', '')
    url = "https://api.twelvedata.com/time_series"
    params = {
        'symbol': s, 'interval': '1day', 'outputsize': 252,
        'apikey': TWELVE_DATA_API_KEY, 'order': 'asc',
    }
    apikey_status = "set" if TWELVE_DATA_API_KEY else "NOT SET ❌"
    try:
        r = std_requests.get(url, params=params, timeout=15)
        return (
            f"Symbol: {s}\n"
            f"TWELVE_DATA_API_KEY: {apikey_status}\n"
            f"Status: {r.status_code}\n"
            f"Length: {len(r.text)}\n"
            f"--- Body Preview ---\n"
            f"{r.text[:800]}"
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


# ---------- Data Fetching ----------
def fetch_twelvedata(symbol: str):
    """ดึงข้อมูลจาก Twelve Data — มี cache 30 นาที"""
    s = symbol.upper().strip()
    if s.endswith('.BK'):
        s = s.replace('.BK', '')

    cached = cache_get(f"price:{s}")
    if cached is not None:
        return cached

    url = "https://api.twelvedata.com/time_series"
    params = {
        'symbol': s, 'interval': '1day', 'outputsize': 252,
        'apikey': TWELVE_DATA_API_KEY, 'order': 'asc',
    }
    try:
        r = std_requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get('status') == 'error':
            return None
        values = data.get('values')
        if not values or len(values) < 20:
            return None
        df = pd.DataFrame(values)
        df['Open'] = df['open'].astype(float)
        df['High'] = df['high'].astype(float)
        df['Low'] = df['low'].astype(float)
        df['Close'] = df['close'].astype(float)
        df = df[['Open', 'High', 'Low', 'Close']].reset_index(drop=True)
        cache_set(f"price:{s}", df)
        return df
    except Exception:
        return None


# ---------- Analytics ----------
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
        return "⚠️ Overbought"
    if rsi <= 30:
        return "⚠️ Oversold"
    return "✅ ปกติ"


# ---------- Stock Analysis ----------
def analyze_stock(symbol: str) -> str:
    try:
        symbol = symbol.upper().strip()
        df = fetch_twelvedata(symbol)

        if df is None or df.empty or len(df) < 20:
            return (
                f"❌ ไม่พบข้อมูลหุ้น '{symbol}'\n"
                "ลองตรวจ ticker เช่น AAPL, TSLA, NVDA"
            )

        close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])
        high = float(df['High'].iloc[-1])
        low = float(df['Low'].iloc[-1])
        change_pct = (close - prev_close) / prev_close * 100

        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)

        sma20 = float(df['Close'].rolling(20).mean().iloc[-1])
        sma50 = float(df['Close'].rolling(50).mean().iloc[-1]) if len(df) >= 50 else None
        sma200 = float(df['Close'].rolling(200).mean().iloc[-1]) if len(df) >= 200 else None
        swing_high_20 = float(df['High'].rolling(20).max().iloc[-1])
        swing_low_20 = float(df['Low'].rolling(20).min().iloc[-1])
        high_52w = float(df['High'].max())
        low_52w = float(df['Low'].min())
        rsi = calc_rsi(df['Close'])
        pullback_pct = (close - high_52w) / high_52w * 100

        m = []
        m.append(f"📊 {symbol}")
        m.append("━━━━━━━━━━━━━━━")
        m.append(f"💰 ราคา: ${close:,.2f} ({change_pct:+.2f}%)")
        m.append(f"📉 จาก 52w High: {pullback_pct:+.1f}%")
        m.append(f"📈 RSI(14): {rsi:.1f} {rsi_signal(rsi)}")
        m.append(trend_signal(close, sma50, sma200))
        m.append("")
        m.append("🔴 แนวต้าน (Resistance)")
        m.append(f"  R3: ${r3:,.2f}")
        m.append(f"  R2: ${r2:,.2f}")
        m.append(f"  R1: ${r1:,.2f}")
        m.append(f"⚪ Pivot: ${pivot:,.2f}")
        m.append("🟢 แนวรับ (Support)")
        m.append(f"  S1: ${s1:,.2f}")
        m.append(f"  S2: ${s2:,.2f}")
        m.append(f"  S3: ${s3:,.2f}")
        m.append("")
        m.append("📐 Moving Averages")
        m.append(f"  SMA20:  ${sma20:,.2f}")
        if sma50:
            m.append(f"  SMA50:  ${sma50:,.2f}")
        if sma200:
            m.append(f"  SMA200: ${sma200:,.2f}")
        m.append("")
        m.append("🎯 Swing 20 วัน")
        m.append(f"  High: ${swing_high_20:,.2f}")
        m.append(f"  Low:  ${swing_low_20:,.2f}")
        m.append("")
        m.append("📅 52 สัปดาห์")
        m.append(f"  High: ${high_52w:,.2f}")
        m.append(f"  Low:  ${low_52w:,.2f}")

        return "\n".join(m)
    except Exception as e:
        return f"⚠️ เกิดข้อผิดพลาด: {str(e)[:100]}"


# ---------- Sector Top Picks (เรียงตามคะแนนความน่าซื้อ) ----------
def get_quick_stats(symbol: str):
    df = fetch_twelvedata(symbol)
    if df is None or df.empty or len(df) < 20:
        return None
    close = float(df['Close'].iloc[-1])
    prev = float(df['Close'].iloc[-2])
    change_pct = (close - prev) / prev * 100
    high_52w = float(df['High'].max())
    pullback = (close - high_52w) / high_52w * 100
    rsi = calc_rsi(df['Close'])
    sma50 = float(df['Close'].rolling(50).mean().iloc[-1]) if len(df) >= 50 else None
    sma200 = float(df['Close'].rolling(200).mean().iloc[-1]) if len(df) >= 200 else None
    return {
        'price': close,
        'change_pct': change_pct,
        'pullback': pullback,
        'rsi': rsi,
        'sma50': sma50,
        'sma200': sma200,
    }


def calculate_buy_score(stats):
    """คำนวณคะแนนความน่าซื้อ 0-100 + เหตุผล"""
    score = 0
    reasons = []

    rsi = stats['rsi']
    pullback = stats['pullback']
    close = stats['price']
    sma50 = stats['sma50']
    sma200 = stats['sma200']

    # 1. RSI Score (0-35 คะแนน)
    if 25 <= rsi <= 35:
        score += 35
        reasons.append("RSI oversold เข้าจังหวะดี")
    elif 35 < rsi <= 45:
        score += 30
        reasons.append("RSI ต่ำ น่าทยอยเก็บ")
    elif 45 < rsi <= 55:
        score += 22
    elif 55 < rsi <= 65:
        score += 15
    elif 65 < rsi <= 75:
        score += 5
        reasons.append("RSI สูง ราคาเริ่มแพง")
    elif rsi > 75:
        score += 0
        reasons.append("RSI overbought รอ correction")
    else:  # rsi < 25
        score += 20
        reasons.append("RSI ต่ำมาก ระวัง falling knife")

    # 2. Pullback Score (0-35 คะแนน)
    if -35 <= pullback <= -20:
        score += 35
        reasons.append("ลงจาก ATH 20-35% = healthy correction")
    elif -20 < pullback <= -10:
        score += 28
    elif -10 < pullback <= -5:
        score += 20
    elif -5 < pullback <= 0:
        score += 10
        reasons.append("ใกล้ ATH ราคาเต็ม")
    elif pullback < -35:
        score += 15
        reasons.append("ลงเยอะ อาจมีปัญหาธุรกิจ")

    # 3. Trend Score (0-30 คะแนน)
    if sma50 and sma200:
        if close > sma50 > sma200:
            score += 30
            reasons.append("เทรนด์ขาขึ้นชัด")
        elif sma50 > sma200 and close < sma50:
            score += 28
            reasons.append("Uptrend + pullback")
        elif close > sma50 and sma50 < sma200:
            score += 15
            reasons.append("กำลังฟื้นจากลง")
        elif close < sma50 < sma200:
            score += 5
            reasons.append("เทรนด์ขาลง")
        else:
            score += 12
    else:
        score += 15  # ข้อมูลไม่พอ

    return min(score, 100), reasons


def buy_label(score):
    if score >= 80:
        return "🟢 น่าสนใจมาก"
    elif score >= 65:
        return "🟡 น่าสนใจ"
    elif score >= 50:
        return "⚪ เฉยๆ"
    elif score >= 30:
        return "🟠 ระวัง"
    else:
        return "🔴 หลีกเลี่ยง"


def top_picks(sector_code: str) -> str:
    sector_code = sector_code.upper().strip()
    if sector_code not in SECTORS:
        return (
            f"❓ ไม่พบ sector '{sector_code}'\n"
            "พิมพ์ /help เพื่อดูทั้งหมด"
        )

    sector = SECTORS[sector_code]
    tickers = sector['tickers']
    theses = sector['theses']
    yields = sector.get('yields', {})
    is_div = sector_code == 'DIV'

    # ดึงข้อมูลทั้งหมด + คำนวณ score
    items = []
    for ticker in tickers:
        stats = get_quick_stats(ticker)
        if stats is None:
            items.append({'ticker': ticker, 'stats': None})
            continue
        score, reasons = calculate_buy_score(stats)
        items.append({
            'ticker': ticker,
            'stats': stats,
            'score': score,
            'reasons': reasons,
        })

    # เรียงตาม score มาก -> น้อย (ตัวที่ไม่มีข้อมูลอยู่ท้าย)
    items.sort(key=lambda x: x.get('score', -1), reverse=True)

    m = [f"{sector['name']}", "เรียงตามความน่าซื้อ", "━━━━━━━━━━━━━━━"]
    for i, item in enumerate(items, 1):
        ticker = item['ticker']
        stats = item['stats']
        if stats is None:
            m.append(f"{i}. {ticker} — ไม่พบข้อมูล")
            continue

        score = item['score']
        label = buy_label(score)
        reasons_str = ", ".join(item['reasons'][:2]) if item['reasons'] else "—"

        if is_div:
            y = yields.get(ticker, 0)
            m.append(
                f"{i}. {ticker}  ${stats['price']:,.2f} ({stats['change_pct']:+.2f}%)\n"
                f"   {label}  Score {score}/100\n"
                f"   💵 Yield ~{y:.1f}%  | RSI {stats['rsi']:.0f}  | ATH {stats['pullback']:+.1f}%\n"
                f"   💡 {theses.get(ticker, '')}\n"
                f"   ✨ {reasons_str}"
            )
        else:
            m.append(
                f"{i}. {ticker}  ${stats['price']:,.2f} ({stats['change_pct']:+.2f}%)\n"
                f"   {label}  Score {score}/100\n"
                f"   📉 ATH {stats['pullback']:+.1f}%  | RSI {stats['rsi']:.0f}\n"
                f"   💡 {theses.get(ticker, '')}\n"
                f"   ✨ {reasons_str}"
            )

    m.append("")
    m.append("━━━━━━━━━━━━━━━")
    m.append("🟢 น่าสนใจมาก (80+)")
    m.append("🟡 น่าสนใจ (65-79)")
    m.append("⚪ เฉยๆ (50-64)")
    m.append("🟠 ระวัง (30-49)")
    m.append("🔴 หลีกเลี่ยง (<30)")
    m.append("")
    m.append("📊 พิมพ์ ชื่อหุ้นที่คุณสนใจเพื่อดูแนวรับแนวต้าน")
    return "\n".join(m)


def sectors_list() -> str:
    m = ["📂 Mega-Trend Sectors", "━━━━━━━━━━━━━━━"]
    for code, info in SECTORS.items():
        m.append(f"/top {code}  →  {info['name']}")
    m.append("")
    m.append("ตัวอย่าง: /top AI")
    return "\n".join(m)


# ---------- Help ----------
HELP_TEXT = (
    "📖 LINE Stock Bot\n"
    "━━━━━━━━━━━━━━━\n"
    "\n"
    "🔹 วิเคราะห์หุ้นรายตัว\n"
    "\n"
    "  พิมพ์ ticker เช่น:\n"
    "  AAPL, TSLA, NVDA, MSFT\n"
    "\n"
    "━━━━━━━━━━━━━━━\n"
    "\n"
    "🔹 ดูหุ้นเด่นแต่ละกลุ่ม\n"
    "\n"
    "  /top AI       Top 5 หุ้น AI\n"
    "  /top SEMI     เซมิคอนดักเตอร์\n"
    "  /top FINTECH  เทคโนโลยีการเงิน\n"
    "  /top CYBER    ความปลอดภัยไซเบอร์\n"
    "  /top CLOUD    คลาวด์\n"
    "  /top EV       รถยนต์ไฟฟ้า\n"
    "  /top BIO      ไบโอเทค\n"
    "  /top DEFENSE  กลาโหม/อวกาศ\n"
    "  /top DIV      หุ้นปันผล\n"
    "\n"
    "━━━━━━━━━━━━━━━\n"
    "\n"
    "🔹 ความช่วยเหลือ\n"
    "  /help — แสดงคู่มือนี้"
)


# ---------- Message Handler ----------
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    upper = text.upper()

    if upper in ('/HELP', 'HELP', 'ช่วย', 'วิธีใช้'):
        reply = HELP_TEXT
    elif upper in ('/SECTORS', '/SECTOR', 'SECTORS'):
        reply = sectors_list()
    elif upper.startswith('/TOP '):
        sector_code = upper.replace('/TOP ', '', 1).strip()
        reply = top_picks(sector_code)
    elif upper.startswith('/'):
        reply = "❓ คำสั่งไม่ถูกต้อง พิมพ์ /help เพื่อดูวิธีใช้"
    else:
        # ticker ปกติ — ตัวอักษร 1-10 ตัว
        if 1 <= len(text) <= 10 and text.replace('.', '').isalnum():
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
