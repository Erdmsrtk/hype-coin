#!/usr/bin/env python3 """ hype_coin_detector_bot.py

Tek seferlik çalıştırıldığında CoinGecko’dan trending coinleri tespit eder, fiyat + teknik indikatör (RSI, MACD diff) analizi yapar ve Telegram’a gönderir.

Her 5 dakikada bir GitHub Actions ile tetiklenmeye hazır.

Gereksinimler: pip install python-telegram-bot requests pandas

Çevresel Değişkenler: TELEGRAM_TOKEN: Bot token’ınız (actions secrets içine ekleyin) TELEGRAM_CHAT_ID: Mesajın gideceği chat ID (actions secrets içine ekleyin) VS_CURRENCY: (opsiyonel) Fiyat için para birimi, default 'usd' """ import os import requests import pandas as pd from datetime import datetime from telegram import Bot

=== Config ===

TOKEN   = os.getenv('TELEGRAM_TOKEN') CHAT_ID = os.getenv('TELEGRAM_CHAT_ID') VS_CUR  = os.getenv('VS_CURRENCY', 'usd')

bot = Bot(token=TOKEN)

Trend coinleri CoinGecko’dan al

def detect_hype_coins(): try: j = requests.get('https://api.coingecko.com/api/v3/search/trending').json() return [c['item']['id'] for c in j.get('coins', [])] except Exception as e: print(f"Error fetching trending coins: {e}") return []

RSI hesaplama

def calculate_rsi(prices, period=14): delta = prices.diff() gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean() loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean() rs = gain / loss return 100 - (100 / (1 + rs))

MACD hesaplama

def calculate_macd(prices, fast=12, slow=26, sig=9): e_fast = prices.ewm(span=fast, adjust=False).mean() e_slow = prices.ewm(span=slow, adjust=False).mean() macd = e_fast - e_slow signal = macd.ewm(span=sig, adjust=False).mean() return macd.iloc[-1], signal.iloc[-1]

Coin analizi: fiyat, %24 değişim, RSI, MACD farkı

def analyze_coin(cid): # Piyasa verisi try: m = requests.get( f'https://api.coingecko.com/api/v3/coins/markets?vs_currency={VS_CUR}&ids={cid}' ).json()[0] except Exception as e: raise RuntimeError(f"Market data error for {cid}: {e}")

price = m.get('current_price')
ch24 = m.get('price_change_percentage_24h')

# Fiyat geçmişi
hist_url = (
    f'https://api.coingecko.com/api/v3/coins/{cid}/market_chart'
    f'?vs_currency={VS_CUR}&days=1&interval=hourly'
)
try:
    hist_json = requests.get(hist_url).json()
    prices_list = hist_json.get('prices')
    if not prices_list:
        raise KeyError('prices')
    df = pd.DataFrame(prices_list, columns=['time','price'])
except Exception as e:
    raise RuntimeError(f"History data error for {cid}: {e}")

df['time'] = pd.to_datetime(df['time'], unit='ms')
df.set_index('time', inplace=True)

rsi_val = calculate_rsi(df['price']).iloc[-1]
macd_val, sig_val = calculate_macd(df['price'])

return {
    'price': price,
    'change_24h': round(ch24 or 0, 2),
    'rsi': round(rsi_val, 2),
    'macd_diff': round(macd_val - sig_val, 4)
}

Telegram mesajı gönderimi

def send_signal(cid, info): ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S') text = ( f"🚀 <b>Hype Coin: {cid.upper()}</b>\n" f"Fiyat: {info['price']} {VS_CUR.upper()}\n" f"24s Δ: {info['change_24h']}%\n" f"RSI: {info['rsi']}\n" f"MACD Diff: {info['macd_diff']}\n" f"Zaman (UTC): {ts}" ) try: bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML') print(f"Sent alert for {cid}") except Exception as e: print(f"Failed to send signal for {cid}: {e}")

Ana fonksiyon: hata tolere ederek devam eden döngü

def main(): coins = detect_hype_coins() print(f"Detected coins: {coins}") for cid in coins: try: data = analyze_coin(cid) send_signal(cid, data) except Exception as e: print(f"Error analyzing {cid}: {e}")

if name == 'main': main()

