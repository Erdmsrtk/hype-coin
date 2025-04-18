import os
import requests
import pandas as pd
from datetime import datetime
from telegram import Bot

# Config
TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
VS_CUR  = os.getenv("VS_CURRENCY", "usd")

bot = Bot(token=TOKEN)

def detect_hype_coins():
    try:
        data = requests.get("https://api.coingecko.com/api/v3/search/trending").json()
        return [c["item"]["id"] for c in data.get("coins", [])]
    except Exception as e:
        print("Trend fetch error:", e)
        return []

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs    = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(series, fast=12, slow=26, sig=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd     = ema_fast - ema_slow
    signal   = macd.ewm(span=sig, adjust=False).mean()
    return macd.iloc[-1], signal.iloc[-1]

def analyze_coin(cid):
    m = requests.get(
        f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={VS_CUR}&ids={cid}"
    ).json()[0]
    price    = m["current_price"]
    change   = m.get("price_change_percentage_24h", 0)
    hist     = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart?vs_currency={VS_CUR}&days=1&interval=hourly"
    ).json().get("prices", [])
    df       = pd.DataFrame(hist, columns=["t","p"])
    df["t"]  = pd.to_datetime(df["t"], unit="ms")
    df       = df.set_index("t")
    rsi      = calculate_rsi(df["p"]).iloc[-1]
    macd_v, s= calculate_macd(df["p"])
    return {
        "price": price,
        "change_24h": round(change, 2),
        "rsi": round(rsi,2),
        "macd_diff": round(macd_v - s,4)
    }

def send_signal(cid, stats):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"🚀 <b>{cid.upper()}</b>\n"
        f"Price: {stats['price']} {VS_CUR.upper()}\n"
        f"24h Δ: {stats['change_24h']}%\n"
        f"RSI: {stats['rsi']}\n"
        f"MACD Δ: {stats['macd_diff']}\n"
        f"Time UTC: {ts}"
    )
    bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")

if __name__ == "__main__":
    coins = detect_hype_coins()
    for c in coins:
        try:
            stats = analyze_coin(c)
            send_signal(c, stats)
        except Exception as e:
            print(f"Error {c}:", e)
