#!/usr/bin/env python3
"""
hype_coin_detector_bot.py

Tek dosya: Bu betik çağrıldığında hype coin tespiti yapıp Telegram’a sinyal gönderir.
Her 5 dakikada bir GitHub Actions ile tetiklenmeye hazır.

Gereksinimler:
    pip install python-telegram-bot requests pandas

Çevresel Değişkenler:
    TELEGRAM_TOKEN: Telegram bot token’ınız
    CHAT_ID: Sinyal göndereceğiniz chat ID
    VS_CURRENCY: (opsiyonel) Fiyat analizinde kullanılacak para birimi (default 'usd')

Kullanım:
    python hype_coin_detector_bot.py
"""
import os
import requests
import pandas as pd
from datetime import datetime
from telegram import Bot

# === Yapılandırma ===
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'YOUR_TELEGRAM_TOKEN')
CHAT_ID        = os.getenv('TELEGRAM_CHAT_ID', 'YOUR_CHAT_ID')
VS_CURRENCY    = os.getenv('VS_CURRENCY', 'usd')

bot = Bot(token=TELEGRAM_TOKEN)

# Trend olan coinleri CoinGecko API’den al
def detect_hype_coins():
    try:
        resp = requests.get('https://api.coingecko.com/api/v3/search/trending')
        return [c['item']['id'] for c in resp.json().get('coins', [])]
    except:
        return []

# RSI hesaplama
def calculate_rsi(prices, period=14):
    delta    = prices.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs       = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# MACD hesaplama
def calculate_macd(prices, fast=12, slow=26, signal=9):
    ema_fast    = prices.ewm(span=fast, adjust=False).mean()
    ema_slow    = prices.ewm(span=slow, adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line.iloc[-1], signal_line.iloc[-1]

# Coin analizi: fiyat, %24 değişim, RSI, MACD farkı
def analyze_coin(coin_id):
    m_url   = f'https://api.coingecko.com/api/v3/coins/markets?vs_currency={VS_CURRENCY}&ids={coin_id}'
    m       = requests.get(m_url).json()[0]
    price   = m['current_price']
    change_24h = m['price_change_percentage_24h']

    hist_url = (
        f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart'
        f'?vs_currency={VS_CURRENCY}&days=1&interval=hourly'
    )
    df = pd.DataFrame(requests.get(hist_url).json()['prices'], columns=['time','price'])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df.set_index('time', inplace=True)

    rsi       = calculate_rsi(df['price']).iloc[-1]
    macd_val, sig_val = calculate_macd(df['price'])

    return {
        'price': price,
        'change_24h': round(change_24h, 2),
        'rsi': round(rsi, 2),
        'macd_diff': round(macd_val - sig_val, 4)
    }

# Telegram mesajı gönder
def send_signal(coin_id, analysis):
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    text = (
        f"🚀 <b>Hype Coin: {coin_id.upper()}</b>\n"
        f"Fiyat: {analysis['price']} {VS_CURRENCY.upper()}\n"
        f"24s Değişim: {analysis['change_24h']}%\n"
        f"RSI: {analysis['rsi']}\n"
        f"MACD Diff: {analysis['macd_diff']}\n"
        f"Zaman (UTC): {timestamp}"
    )
    bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')

# Ana fonksiyon: tek seferlik tespit ve sinyal
def main():
    coins = detect_hype_coins()
    for coin in coins:
        analysis = analyze_coin(coin)
        send_signal(coin, analysis)

if __name__ == '__main__':
    main()
