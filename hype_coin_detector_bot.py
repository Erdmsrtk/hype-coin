import os
import requests
import pandas as pd
from datetime import datetime
from telegram import Bot

# Configuration via environment variables
TOKEN   = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
VS_CUR  = os.getenv('VS_CURRENCY', 'usd')

# Initialize Telegram bot
bot = Bot(token=TOKEN)

# Fetch trending coins from CoinGecko
def detect_hype_coins():
    try:
        data = requests.get(
            "https://api.coingecko.com/api/v3/search/trending"
        ).json()
        # Return up to first 7 trending coin IDs
        return [item['item']['id'] for item in data.get('coins', [])][:7]
    except Exception as e:
        print("Error fetching trending coins:", e)
        return []

# Calculate RSI indicator
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Calculate MACD indicator
def calculate_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line.iloc[-1], signal_line.iloc[-1]

# Analyze a single coin
def analyze_coin(coin_id):
    # Market data
    try:
        market = requests.get(
            f"https://api.coingecko.com/api/v3/coins/markets?vs_currency={VS_CUR}&ids={coin_id}"
        ).json()[0]
    except Exception as e:
        raise RuntimeError(f"Market data error for {coin_id}: {e}")

    price       = market.get('current_price')
    change_24h  = market.get('price_change_percentage_24h', 0)

    # Historical price data (24h hourly)
    try:
        hist = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={VS_CUR}&days=1&interval=hourly"
        ).json().get('prices', [])
    except Exception as e:
        hist = []
        print(f"History fetch error for {coin_id}: {e}")

    # Default indicators
    rsi_val   = None
    macd_diff = None

    # Compute only if we have at least 2 points
    if len(hist) >= 2:
        df = pd.DataFrame(hist, columns=['time','price'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df.set_index('time', inplace=True)
        try:
            rsi_val, _ = (calculate_rsi(df['price']), None)
            rsi_val   = rsi_val.iloc[-1]
            macd_val, sig_val = calculate_macd(df['price'])
            macd_diff = macd_val - sig_val
        except Exception as e:
            print(f"Indicator error for {coin_id}: {e}")

    return {
        'price': price,
        'change_24h': round(change_24h, 2),
        'rsi': round(rsi_val, 2) if rsi_val is not None else 'N/A',
        'macd_diff': round(macd_diff, 4) if macd_diff is not None else 'N/A'
    }

# Send Telegram message
def send_signal(coin_id, stats):
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    text = (
        f"🚀 <b>{coin_id.upper()}</b>\n"
        f"Price: {stats['price']} {VS_CUR.upper()}\n"
        f"24h Δ: {stats['change_24h']}%\n"
        f"RSI: {stats['rsi']}\n"
        f"MACD Diff: {stats['macd_diff']}\n"
        f"Time UTC: {ts}"
    )
    try:
        bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')
        print(f"Sent signal for {coin_id}")
    except Exception as e:
        print(f"Telegram error for {coin_id}: {e}")

# Main execution
if __name__ == '__main__':
    print("Starting hype detection...")
    coins = detect_hype_coins()
    print(f"Detected coins: {coins}")
    if not coins:
        bot.send_message(chat_id=CHAT_ID, text="⏱️ No hype coins detected at this time.")
    for coin in coins:
        try:
            stats = analyze_coin(coin)
            send_signal(coin, stats)
        except Exception as e:
            print(f"Error processing {coin}: {e}")
