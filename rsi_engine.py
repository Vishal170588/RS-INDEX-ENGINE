
import os
import time
import requests
import pandas as pd
import pyotp
from datetime import datetime, timedelta
from SmartApi import SmartConnect

SCAN_INTERVAL = 300  # 5 minutes

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
ANGEL_TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

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
# SAFE CANDLE FETCH
# ================================

def fetch_candles(symbol, interval):

    try:

        from_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
        to_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        params = {
            "exchange": "NSE",
            "symboltoken": INDICES[symbol],
            "interval": interval,
            "fromdate": from_date,
            "todate": to_date
        }

        data = smart.getCandleData(params)

        if not data or "data" not in data or not data["data"]:
            print(f"No data returned for {symbol}")
            return None

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

    except Exception as e:

        print("Candle fetch error:", e)
        return None


# ================================
# RSI REGIME
# ================================

def rsi_regime(rsi):

    if rsi > 60:
        return "BULLISH"

    if rsi < 40:
        return "BEARISH"

    return "SIDEWAYS"


# ================================
# SIGNAL LOGIC
# ================================

def check_signal(symbol):

    df5 = fetch_candles(symbol, "FIVE_MINUTE")
    df15 = fetch_candles(symbol, "FIFTEEN_MINUTE")

    if df5 is None or df15 is None:
        return None

    rsi5 = df5["rsi"]
    rsi15 = df15["rsi"].iloc[-1]

    r1 = rsi5.iloc[-1]
    r2 = rsi5.iloc[-2]
    r3 = rsi5.iloc[-3]

    expansion = round(r1 - r2,2)

    regime = rsi_regime(rsi15)

    price = df5["close"].iloc[-1]

    # BUY STRUCTURE
    if r2 > r3 and r1 > r2:

        return {
            "type": "BUY",
            "price": round(price,2),
            "rsi5": round(r1,2),
            "rsi15": round(rsi15,2),
            "expansion": expansion,
            "regime": regime,
            "stop": round(df5["low"].iloc[-2],2)
        }

    # SELL STRUCTURE
    if r2 < r3 and r1 < r2:

        return {
            "type": "SELL",
            "price": round(price,2),
            "rsi5": round(r1,2),
            "rsi15": round(rsi15,2),
            "expansion": expansion,
            "regime": regime,
            "stop": round(df5["high"].iloc[-2],2)
        }

    return None


# ================================
# ENGINE LOOP
# ================================

def run():

    print("RSI INDEX ENGINE STARTED")
    send_telegram("🚀 RSI INDEX ENGINE ONLINE")

    while True:

        try:

            now = datetime.now()

            market_open = now.replace(hour=9, minute=15)
            market_close = now.replace(hour=15, minute=30)

            if market_open <= now <= market_close:

                for index in INDICES:

                    print(f"Scanning {index}")

                    signal = check_signal(index)

                    if signal:

                        entry = signal["price"]
                        stop = signal["stop"]

                        risk = abs(entry - stop)

                        target = entry + risk if signal["type"] == "BUY" else entry - risk

                        message = f"""
🚀 {index} {signal["type"]} SIGNAL

Price: {entry}

5m RSI: {signal["rsi5"]}
15m RSI: {signal["rsi15"]}

RSI Expansion: {signal["expansion"]}
RSI Regime: {signal["regime"]}

Stoploss: {stop}
Target: {round(target,2)}

Action:
{"Buy ATM CE" if signal["type"]=="BUY" else "Buy ATM PE"}
"""

                        send_telegram(message)

            time.sleep(SCAN_INTERVAL)

        except Exception as e:

            print("Engine error:", e)
            time.sleep(10)


# ================================
# START ENGINE
# ================================

if __name__ == "__main__":
    run()
