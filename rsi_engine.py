import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime

SCAN_INTERVAL = 60

def send_startup_message():
    message = "🚀 MASTERQUANT RSI ENGINE ONLINE\n\nScanner started successfully."

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Startup message failed:", e)# ================================
# ENV VARIABLES
# ================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
send_startup_message()
def bot_alive():
    message = "🟢 BOT ALIVE\n\nMASTERQUANT RSI ENGINE RUNNING"

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Alive message failed:", e)
        
    SCAN_INTERVAL = 60

INDICES = [
    "NIFTY",
    "BANKNIFTY",
    "SENSEX"
]

# ================================
# TELEGRAM FUNCTION
# ================================

def send_telegram(msg):

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(msg)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg
    }

    try:
        requests.post(url, data=payload)

    except Exception as e:
        print("Telegram error", e)

# ================================
# RSI CALCULATION
# ================================

def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi

# ================================
# MOCK DATA (Replace with Angel)
# ================================

def fetch_candles(symbol):

    price = np.cumsum(np.random.randn(100)) + 100

    df = pd.DataFrame({
        "close": price
    })

    df["high"] = df["close"] + np.random.rand(len(df))
    df["low"] = df["close"] - np.random.rand(len(df))

    df["rsi"] = calculate_rsi(df["close"])

    return df

# ================================
# RSI STRUCTURE DETECTION
# ================================

def rsi_structure(df):

    rsi = df["rsi"]

    r1 = rsi.iloc[-1]
    r2 = rsi.iloc[-2]
    r3 = rsi.iloc[-3]

    if r1 > r2 and r2 > r3:
        return "Higher High"

    if r1 < r2 and r2 < r3:
        return "Lower Low"

    return "Sideways"

# ================================
# PBC LEVEL
# ================================

def pbc_level(df):

    return round(df["high"].iloc[-2],2)

# ================================
# SWING PBC
# ================================

def swing_pbc(df):

    return round(df["high"].rolling(5).max().iloc[-1],2)

# ================================
# TRADE STATE CLASS
# ================================

class TradeState:

    def __init__(self):

        self.active = False
        self.entry = None
        self.stop = None
        self.target = None
        self.rsi_signal = None
        self.partial_done = False

states = {i: TradeState() for i in INDICES}

# ================================
# SIGNAL CHECK
# ================================

def check_signal(symbol):

    df = fetch_candles(symbol)

    rsi = df["rsi"].iloc[-1]
    prev_rsi = df["rsi"].iloc[-2]

    momentum = rsi - prev_rsi

    structure = rsi_structure(df)

    if momentum >= 2 and rsi < 80:

        price = df["close"].iloc[-1]

        return {
            "price": round(price,2),
            "rsi": round(rsi,2),
            "structure": structure,
            "pbc": pbc_level(df),
            "swing": swing_pbc(df),
            "stop": round(df["low"].iloc[-2],2)
        }

    return None

# ================================
# MAIN ENGINE
# ================================

def run():

    print("RSI INDEX ENGINE STARTED")
    bot_alive()
    
    while True:
        
        now = datetime.now()

    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

    if market_open <= now <= market_close:
        

        for index in INDICES:
            print(f"Scanning {index} at {datatime.now()}")

            state = states[index]

            signal = check_signal(index)
            print(f"{index} signal -> {signal}")
            if signal and not state.active:

                entry = signal["price"]

                stop = signal["stop"]

                risk = entry - stop

                target = entry + risk

                state.active = True
                state.entry = entry
                state.stop = stop
                state.target = target
                state.rsi_signal = signal["rsi"]

                message = f"""
🚀 {index} BUY SIGNAL

RSI: {signal['rsi']}
Structure: {signal['structure']}

Entry: {entry}

Stoploss: {stop}

Target 1: {round(target,2)}

PBC Level: {signal['pbc']}

Swing PBC: {signal['swing']}

Action:
Buy ATM CE
"""

                send_telegram(message)

            if state.active:

                df = fetch_candles(index)

                price = df["close"].iloc[-1]

                rsi_now = df["rsi"].iloc[-1]

                if not state.partial_done and price >= state.target:

                    state.partial_done = True

                    send_telegram(f"""
🎯 TARGET 1 HIT

{index}

Book 50% Partial Profit
""")

                if price <= state.stop:

                    send_telegram(f"""
⚠️ STOPLOSS TRIGGERED

{index}
""")

                    states[index] = TradeState()

                if rsi_now >= state.rsi_signal + 5:

                    send_telegram(f"""
🔥 MOMENTUM EXPANSION

{index}

RSI: {round(rsi_now,2)}
""")

        time.sleep(60)

# ================================
# START ENGINE
# ================================

if __name__ == "__main__":
    run()
