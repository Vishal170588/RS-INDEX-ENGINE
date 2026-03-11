import os
import time
import requests
import pandas as pd
import numpy as np
import pyotp
from datetime import datetime
from SmartApi import SmartConnect

SCAN_INTERVAL = 60

# ================================
# TELEGRAM
# ================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
        print("Telegram error:", e)

# ================================
# ANGEL LOGIN
# ================================

ANGEL_API_KEY = os.getenv("ANGEL_API_KEY")
ANGEL_CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
ANGEL_PASSWORD = os.getenv("ANGEL_PASSWORD")

ANGEL_TOTP_SECRET = os.environ.get("ANGEL_TOTP", "").replace(" ", "").strip().upper()

print("TOTP VALUE:", ANGEL_TOTP_SECRET)

if not ANGEL_TOTP_SECRET:
    raise Exception("ANGEL_TOTP missing in Railway variables")

totp = pyotp.TOTP(ANGEL_TOTP_SECRET).now()

smart = SmartConnect(api_key=ANGEL_API_KEY)

session = smart.generateSession(
    ANGEL_CLIENT_ID,
    ANGEL_PASSWORD,
    totp
)

print("Angel Login Successful")

# ===============================
# INDEX TOKENS
# ===============================

INDICES = {
    "NIFTY": "99926000",
    "BANKNIFTY": "99926009",
    "SENSEX": "99919000"
}

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
# TRADE STATE
# ================================

class TradeState:

    def __init__(self):

        self.active = False
        self.entry = None
        self.stop = None
        self.target = None
        self.rsi_signal = None
        self.partial_done = False
        self.alert_sent = False
        self.expansion_sent = False

states = {i: TradeState() for i in INDICES}

# ================================
# SIGNAL CHECK
# ================================

def check_signal(symbol):

    df = fetch_candles(symbol)

    rsi = df["rsi"].iloc[-1]
    prev_rsi = df["rsi"].iloc[-2]

    momentum = rsi - prev_rsi

    if momentum >= 2 and rsi < 80:

        price = df["close"].iloc[-1]

        return {
            "price": round(price,2),
            "rsi": round(rsi,2),
            "stop": round(df["low"].iloc[-2],2)
        }

    return None

# ================================
# MAIN ENGINE
# ================================

def run():

    print("RSI INDEX ENGINE STARTED")

    send_telegram("🚀 MASTERQUANT RSI ENGINE ONLINE")

    while True:

        now = datetime.now()

        market_open = now.replace(hour=9, minute=15)
        market_close = now.replace(hour=15, minute=30)

        if market_open <= now <= market_close:

            for index in INDICES:

                print(f"Scanning {index} at {datetime.now()}")

                state = states[index]

                signal = check_signal(index)

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

Entry: {entry}
Stoploss: {stop}

Target 1: {round(target,2)}

Action:
Buy ATM CE
"""

                    send_telegram(message)

        time.sleep(SCAN_INTERVAL)

# ================================
# START ENGINE
# ================================

if __name__ == "__main__":
    run()
