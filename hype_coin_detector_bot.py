#!/usr/bin/env python3 """ hype_coin_detector_bot.py

This script detects trending coins from CoinGecko, calculates price, RSI, MACD, and sends signals via Telegram.

Designed for one-time execution (e.g. by GitHub Actions every 5 minutes).

Requirements: pip install python-telegram-bot requests pandas

Environment variables: TELEGRAM_TOKEN    Your Telegram bot token (set in repo secrets) TELEGRAM_CHAT_ID  The Telegram chat ID to send messages to (set in repo secrets) VS_CURRENCY       (optional) Currency for price data; default "usd" """ import os import requests import pandas as pd from datetime import datetime from telegram import Bot

Configuration

TOKEN   = os.getenv('TELEGRAM_TOKEN') CHAT_ID = os.getenv('TELEGRAM_CHAT_ID') VS_CUR  = os.getenv('VS_CURRENCY', 'usd')

bot = Bot(token=TOKEN)

Fetch trending coins from CoinGecko

def detect_hype_coins(): try: data = requests.get( 'https://api.coingecko.com/api/v3/search/trending' ).json() return [item['item']['id'] for item in data.get('coins', [])] except Exception as e: print(f"Error fetching trending coins: {e}") return []

Compute RSI

def calculate_rsi(prices, period=14): delta = prices.diff() gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean() loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean() rs = gain / loss return 100 - (100 / (1 + rs))

Compute MACD

def calculate_macd(prices, fast=12, slow=26, signal=9): ema_fast = prices.ewm(span=fast, adjust=False).mean() ema_slow = prices.ewm(span=slow, adjust=False).mean() macd_line = ema_fast - ema_slow signal_line = macd_line.ewm(span=signal, adjust=False).mean() return macd_line.iloc[-1], signal_line.iloc[-1]

Analyze a single coin

def analyze_coin(coin_id): # Market data url_market = ( f"https://api.coingecko.com/api/v3/coins/markets" f"?vs_currency={VS_CUR}&ids={coin_id}" ) market = requests.get(url_market).json()[0] price = market.get('current_price') change_24h = market.get('price_change_percentage_24h')

# Historical prices (24h, hourly)
url_hist = (
    f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    f"?vs_currency={VS_CUR}&days=1&interval=hourly"
)
hist = requests.get(url_hist).json().get('prices', [])
df = pd.DataFrame(hist, columns=['time', 'price'])
df['time'] = pd.to_datetime(df['time'], unit='ms')
df.set_index('time', inplace=True)

# Indicators
rsi = calculate_rsi(df['price']).iloc[-1]
macd_val, signal_val = calculate_macd(df['price'])

return {
    'price': price,
    'change_24h': round(change_24h or 0, 2),
    'rsi': round(rsi, 2),
    'macd_diff': round(macd_val - signal_val, 4)
}

Send Telegram message

def send_signal(coin_id, stats): timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') msg = ( f"🚀 <b>{coin_id.upper()}</b>\n" f"Price: {stats['price']} {VS_CUR.upper()}\n" f"24h Change: {stats['change_24h']}%\n" f"RSI: {stats['rsi']}\n" f"MACD Diff: {stats['macd_diff']}\n" f"Time UTC: {timestamp}" ) try: bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='HTML') print(f"Sent: {coin_id}") except Exception as e: print(f"Telegram error for {coin_id}: {e}")

Main execution

if name == 'main': coins = detect_hype_coins() print(f"Detected coins: {coins}") for coin in coins: try: stats = analyze_coin(coin) send_signal(coin, stats) except Exception as e: print(f"Error for {coin}: {e}")

