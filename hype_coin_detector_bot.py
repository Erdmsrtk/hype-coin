import os
import requests
import pandas as pd
from datetime import datetime

# Configuration from environment
TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
VS_CUR  = os.getenv("VS_CURRENCY", "usd")

# Fetch trending coins from CoinGecko
# Limit to first 7 to avoid hitting rate limits
def detect_hype_coins():
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/search/trending"
        )
        coins = resp.json().get("coins", [])
        return [c["item"]["id"] for c in coins][:7]
    except Exception as e:
        print("Error fetching trending coins:", e)
        return []

# RSI calculation
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# MACD calculation
def calculate_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    sig_line  = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line.iloc[-1], sig_line.iloc[-1]

# Analyze a single coin
def analyze_coin(coin_id):
    # Market data
    url_market = (
        f"https://api.coingecko.com/api/v3/coins/markets"
        f"?vs_currency={VS_CUR}&ids={coin_id}"
    )
    m = requests.get(url_market).json()[0]
    price    = m.get("current_price")
    change24 = m.get("price_change_percentage_24h", 0)

    # Historical prices (24h hourly)
    url_hist = (
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        f"?vs_currency={VS_CUR}&days=1&interval=hourly"
    )
    hist = requests.get(url_hist).json().get("prices", [])

    # Prepare defaults
    rsi_val = None
    macd_diff = None
    if len(hist) >= 2:
        df = pd.DataFrame(hist, columns=["time","price"])
        df["time"] = pd.to_datetime(df["time"], unit='ms')
        df.set_index("time", inplace=True)
        rsi_val = calculate_rsi(df["price"]).iloc[-1]
        macd_v, sig_v = calculate_macd(df["price"])
        macd_diff = macd_v - sig_v

    return {
        "price": price,
        "change_24h": round(change24, 2),
        "rsi": round(rsi_val, 2) if rsi_val is not None else "N/A",
        "macd_diff": round(macd_diff, 4) if macd_diff is not None else "N/A"
    }

# Send Telegram message via HTTP
def send_signal(coin_id, stats):
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    text = (
        f"🚀 <b>{coin_id.upper()}</b>\n"
        f"Price: {stats['price']} {VS_CUR.upper()}\n"
        f"24h Δ: {stats['change_24h']}%\n"
        f"RSI: {stats['rsi']}\n"
        f"MACD Δ: {stats['macd_diff']}\n"
        f"Time UTC: {ts}"
    )
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    resp = requests.post(url, data=payload)
    if resp.ok and resp.json().get("ok"):
        print(f"Sent signal for {coin_id}")
    else:
        print("Telegram send error", resp.text)

if __name__ == '__main__':
    print("Starting hype detection...")
    coins = detect_hype_coins()
    print("Detected coins:", coins)
    if not coins:
        send_signal("No coins", {"price": "-", "change_24h": 0, "rsi": "-", "macd_diff": "-"})
    for c in coins:
        try:
            stats = analyze_coin(c)
            send_signal(c, stats)
        except Exception as e:
            print(f"Error processing {c}:", e)
