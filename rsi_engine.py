import os
import time
import requests
import pandas as pd
from datetime import datetime
from SmartApi import SmartConnect
import pyotp

SCAN_INTERVAL = 60

# ================================
# TELEGRAM
# ================================

TELEGRAM_TOKEN = os.getenv("8464017129:AAFoqp5h0MsQqgbiuAFA2KRi3dlBvD48i60")
TELEGRAM_CHAT_ID = os.getenv("-1003526964518")

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
import os
import pyotp
from SmartApi import SmartConnect

ANGEL_API_KEY = os.getenv("ANGEL_API_KEY")
ANGEL_CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
ANGEL_PASSWORD = os.getenv("ANGEL_PASSWORD")
ANGEL_TOTP_SECRET = os.getenv("ANGEL_TOTP")

if not ANGEL_TOTP_SECRET:
    raise Exception("ANGEL_TOTP not found in environment variables")

totp = pyotp.TOTP(ANGEL_TOTP_SECRET).now()

smart = SmartConnect(api_key=ANGEL_API_KEY)

session = smart.generateSession(
    ANGEL_CLIENT_ID,
    ANGEL_PASSWORD,
    totp
)

print("Angel Login Successful")
# ================================
# INDEX TOKENS
# ================================

INDICES = {
    "NIFTY": "99926000",
    "BANKNIFTY": "99926009",
    "SENSEX": "99919000"
}

# ================================
# RSI
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
# ANGEL CANDLE DATA
# ================================

def fetch_candles(symbol):

    params = {
        "exchange": "NSE",
        "symboltoken": INDICES[symbol],
        "interval": "FIFTEEN_MINUTE",
        "fromdate": "2024-01-01 09:15",
        "todate": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    data = smart.getCandleData(params)

    candles = data["data"]

    df = pd.DataFrame(
        candles,
        columns=["time","open","high","low","close","volume"]
    )

    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)

    df["rsi"] = calculate_rsi(df["close"])

    return df

# ================================
# TRADE STATE
# ================================

class TradeState:

    def __init__(self):

        self.active = False
        self.type = None
        self.entry = None
        self.stop = None
        self.target = None
        self.rsi_signal = None
        self.alert_sent = False
        self.expansion_sent = False
        self.partial_done = False

states = {i: TradeState() for i in INDICES}

# ================================
# RSI SIGNAL
# ================================

def check_signal(symbol):

    df = fetch_candles(symbol)

    rsi = df["rsi"].iloc[-1]
    rsi_prev = df["rsi"].iloc[-2]

    price = df["close"].iloc[-1]

    # BUY
    if rsi > 50 and rsi_prev <= 50:

        return {
            "type": "BUY",
            "price": round(price,2),
            "rsi": round(rsi,2),
            "stop": round(df["low"].iloc[-2],2)
        }

    # SELL
    if rsi < 50 and rsi_prev >= 50:

        return {
            "type": "SELL",
            "price": round(price,2),
            "rsi": round(rsi,2),
            "stop": round(df["high"].iloc[-2],2)
        }

    return None

# ================================
# ENGINE
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

                print(f"{index} signal -> {signal}")

                if signal and not state.active:

                    entry = signal["price"]
                    stop = signal["stop"]

                    risk = abs(entry - stop)

                    if signal["type"] == "BUY":
                        target = entry + risk
                    else:
                        target = entry - risk

                    state.active = True
                    state.type = signal["type"]
                    state.entry = entry
                    state.stop = stop
                    state.target = target
                    state.rsi_signal = signal["rsi"]

                    message = f"""
🚀 {index} {signal["type"]} SIGNAL

RSI: {signal["rsi"]}

Entry: {entry}
Stoploss: {stop}

Target: {round(target,2)}

Action:
{"Buy ATM CE" if signal["type"]=="BUY" else "Buy ATM PE"}
"""

                    send_telegram(message)

                if state.active:

                    df = fetch_candles(index)

                    price = df["close"].iloc[-1]
                    rsi_now = df["rsi"].iloc[-1]

                    if not state.alert_sent and rsi_now >= state.rsi_signal + 2:

                        send_telegram(f"""
⚠️ MOMENTUM BUILDING

{index}
RSI: {round(rsi_now,2)}
""")

                        state.alert_sent = True

                    if not state.expansion_sent and rsi_now >= state.rsi_signal + 4:

                        send_telegram(f"""
🚀 MOMENTUM EXPANSION

{index}
RSI: {round(rsi_now,2)}
""")

                        state.expansion_sent = True

                    if not state.partial_done and (
                        (state.type=="BUY" and price >= state.target) or
                        (state.type=="SELL" and price <= state.target)
                    ):

                        state.partial_done = True

                        send_telegram(f"""
🎯 TARGET HIT

{index}
Book 50% Partial Profit
""")

                    if (
                        (state.type=="BUY" and price <= state.stop) or
                        (state.type=="SELL" and price >= state.stop)
                    ):

                        send_telegram(f"""
⚠️ STOPLOSS TRIGGERED

{index}
""")

                        states[index] = TradeState()

        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    run()
