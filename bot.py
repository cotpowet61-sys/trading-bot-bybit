#!/usr/bin/env python3
import requests
import time
import json
from datetime import datetime
from collections import defaultdict

BOT_TOKEN = "8329085403:AAH5DCLhjdM--YJgMxxqRFj9qo3ZKwSSTNM"
CHAT_ID = "5751308265"

SYMBOLS = [
    "1000PEPEUSDT", "AVAXUSDT", "1000BONKUSDT", "ENAUSDT", "LDOUSDT", 
    "ZEREBROUSDT", "1000RATSUSDT", "NEARUSDT", "TRBUSDT", "APTUSDT", 
    "BLURUSDT", "WLDUSDT", "ARBUSDT", "1000FLOKIUSDT", "MAGICUSDT", 
    "JUPUSDT", "LTCUSDT", "LINKUSDT", "FILUSDT", "MASKUSDT"
]

CHECK_INTERVAL = 300
BYBIT_API = "https://api.bybit.com/v5/market/klines"
last_signals = defaultdict(lambda: {"timestamp": 0, "signal_type": None})

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Sent: {message[:50]}...")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
    return False

def get_klines(symbol, interval="15", limit=50):
    params = {"category": "linear", "symbol": symbol, "interval": interval, "limit": limit}
    try:
        response = requests.get(BYBIT_API, params=params, timeout=10)
        data = response.json()
        return data["result"]["list"] if data["retCode"] == 0 else None
    except:
        return None

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    seed = deltas[:period]
    up = sum([x for x in seed if x > 0]) / period
    down = sum([abs(x) for x in seed if x < 0]) / period
    if down == 0:
        return 100 if up > 0 else 0
    rs = up / down
    rsi = 100 - (100 / (1 + rs))
    for delta in deltas[period:]:
        up = (up * (period - 1) + (delta if delta > 0 else 0)) / period
        down = (down * (period - 1) + (abs(delta) if delta < 0 else 0)) / period
        rs = up / down if down != 0 else 0
        rsi = 100 - (100 / (1 + rs)) if rs != 0 else (100 if up > 0 else 0)
    return rsi

def analyze_confluence(symbol):
    klines = get_klines(symbol, "15", 50)
    if not klines or len(klines) < 21:
        return None
    closes = [float(k[4]) for k in klines]
    volumes = [float(k[7]) for k in klines]
    current_price = closes[-1]
    current_volume = volumes[-1]
    avg_volume_5 = sum(volumes[-5:]) / 5
    ema9 = sum(closes[-9:]) / 9
    ema21 = sum(closes[-21:]) / 21
    rsi = calculate_rsi(closes, 14)
    volume_multiplier = current_volume / avg_volume_5 if avg_volume_5 > 0 else 0
    
    buy_conditions = 0
    if rsi and rsi < 25:
        buy_conditions += 1
    if ema9 > ema21:
        buy_conditions += 1
    if volume_multiplier >= 2.0:
        buy_conditions += 1
    
    sell_conditions = 0
    if rsi and rsi > 75:
        sell_conditions += 1
    if ema9 < ema21:
        sell_conditions += 1
    if volume_multiplier >= 2.0:
        sell_conditions += 1
    
    if buy_conditions >= 3:
        return {
            "symbol": symbol, "signal": "BUY", "price": current_price,
            "rsi": rsi, "ema9": ema9, "ema21": ema21,
            "volume_mult": volume_multiplier, "confidence": 70, "conditions": buy_conditions
        }
    elif sell_conditions >= 3:
        return {
            "symbol": symbol, "signal": "SELL", "price": current_price,
            "rsi": rsi, "ema9": ema9, "ema21": ema21,
            "volume_mult": volume_multiplier, "confidence": 70, "conditions": sell_conditions
        }
    return None

def format_signal(analysis):
    signal = analysis["signal"]
    symbol = analysis["symbol"]
    price = analysis["price"]
    rsi = analysis["rsi"]
    tp1_pct = 2.5 if signal == "BUY" else -2.5
    tp2_pct = 5.8 if signal == "BUY" else -5.8
    sl_pct = -2 if signal == "BUY" else 2
    tp1 = price * (1 + tp1_pct / 100)
    tp2 = price * (1 + tp2_pct / 100)
    sl = price * (1 + sl_pct / 100)
    emoji = "🟢" if signal == "BUY" else "🔴"
    msg = f"{emoji} <b>{signal}</b>\n{symbol} @ {price:.8f}\nRSI: {rsi:.1f}\n📈 TP1: {tp1:.8f}\n🛑 SL: {sl:.8f}\n{datetime.now().strftime('%H:%M:%S UTC')}"
    return msg

def main():
    print("🚀 Bot started! Monitoring 20 symbols on 15m...")
    send_telegram("🚀 <b>Trading Bot started!</b>\n📊 Confluence (15m)")
    while True:
        try:
            for symbol in SYMBOLS:
                analysis = analyze_confluence(symbol)
                if analysis:
                    signal_key = f"{symbol}_{analysis['rsi']}"
                    if signal_key != last_signals.get(symbol):
                        msg = format_signal(analysis)
                        send_telegram(msg)
                        last_signals[symbol] = signal_key
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
