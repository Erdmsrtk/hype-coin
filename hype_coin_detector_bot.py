#!/usr/bin/env python3
"""
CoinGecko Trend Sinyal Botu
Trend coinleri tespit eder ve teknik göstergelere göre Telegram'da uyarı gönderir.
"""

import os
import logging
import requests
import pandas as pd
from datetime import datetime
from telegram import Bot
from dotenv import load_dotenv

# Ortam değişkenlerini yükle
load_dotenv()

# Log ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Yapılandırma
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
VS_CURRENCY = os.getenv('VS_CURRENCY', 'usd')

# Telegram bot başlatma
bot = Bot(token=TELEGRAM_TOKEN)

def get_trending_coins():
    """Trend coin listesini alır"""
    try:
        response = requests.get(
            'https://api.coingecko.com/api/v3/search/trending',
            timeout=30
        )
        data = response.json()
        return [coin['item']['id'] for coin in data.get('coins', [])]
    except Exception as e:
        logger.error(f"Trend coinler alınırken hata: {e}")
        return []

def calculate_rsi(prices, period=14):
    """RSI hesaplar"""
    delta = prices.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """MACD hesaplar"""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line.iloc[-1], signal_line.iloc[-1]

def analyze_coin(coin_id):
    """Coin analizi yapar"""
    try:
        # Piyasa verileri
        market_data = requests.get(
            f'https://api.coingecko.com/api/v3/coins/markets?vs_currency={VS_CURRENCY}&ids={coin_id}',
            timeout=30
        ).json()[0]

        # Tarihsel veriler
        history = requests.get(
            f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={VS_CURRENCY}&days=1&interval=hourly',
            timeout=30
        ).json()

        df = pd.DataFrame(history['prices'], columns=['timestamp', 'price'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        rsi = calculate_rsi(df['price']).iloc[-1]
        macd, signal = calculate_macd(df['price'])

        return {
            'coin': coin_id,
            'price': market_data['current_price'],
            'change': market_data['price_change_percentage_24h'],
            'rsi': round(rsi, 2),
            'macd_diff': round(macd - signal, 4),
            'volume': market_data['total_volume']
        }

    except Exception as e:
        logger.error(f"{coin_id} analizinde hata: {e}")
        raise

def send_alert(coin_data):
    """Telegram uyarısı gönderir"""
    try:
        message = (
            f"🚀 <b>{coin_data['coin'].upper()}</b>\n\n"
            f"💰 Fiyat: {coin_data['price']} {VS_CURRENCY.upper()}\n"
            f"📈 24s Değişim: %{round(coin_data['change'], 2)}\n"
            f"📊 RSI: {coin_data['rsi']}\n"
            f"📉 MACD Farkı: {coin_data['macd_diff']}\n"
            f"🔄 Hacim: {coin_data['volume']:,.2f}\n\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode='HTML'
        )
        logger.info(f"{coin_data['coin']} için uyarı gönderildi")
    except Exception as e:
        logger.error(f"Telegram gönderim hatası: {e}")

def main():
    """Ana işlem"""
    logger.info("Bot başlatıldı")
    
    coins = get_trending_coins()
    if not coins:
        logger.warning("Trend coin bulunamadı")
        return

    logger.info(f"Analiz edilecek coinler: {', '.join(coins)}")

    for coin in coins:
        try:
            data = analyze_coin(coin)
            send_alert(data)
        except Exception as e:
            logger.error(f"{coin} işlenirken hata: {e}")
            continue

    logger.info("Analiz tamamlandı")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f"Beklenmeyen hata: {e}")
