#added a comment!!!

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import csv
from datetime import datetime

load_dotenv()
app = Flask(__name__)
CORS(app)
client = OpenAI()

LOGFILE = "chartgpt_trade_log.csv"

@app.route('/', methods=['GET'])
def home():
    return "✅ ChartGPT Flask server with CSV logging."

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        print("🚀 Raw payload:")
        print(request.data)

        data = json.loads(request.data)
        print("✅ Parsed JSON:")
        print(json.dumps(data, indent=2))

        price = data.get("price")
        rsi = data.get("rsi")
        ema9 = data.get("ema9")
        ema21 = data.get("ema21")
        vwap = data.get("vwap")
        bb_mid = data.get("bb_mid")
        macd_hist = data.get("macd_hist")
        volume_osc = data.get("volume_osc")
        atr = data.get("atr")
        bb_width = data.get("bb_width")
        session_range = data.get("session_range")
        c1 = data.get("candle_1", {})
        c2 = data.get("candle_2", {})
        c3 = data.get("candle_3", {})

        candle_summary = (
            f"Last 3 candles:\n"
            f"1: Open {c1.get('open')}, High {c1.get('high')}, Low {c1.get('low')}, Close {c1.get('close')}\n"
            f"2: Open {c2.get('open')}, High {c2.get('high')}, Low {c2.get('low')}, Close {c2.get('close')}\n"
            f"3: Open {c3.get('open')}, High {c3.get('high')}, Low {c3.get('low')}, Close {c3.get('close')}"
        )

        prompt = f"""You are ChartGPT, an intelligent scalping assistant. Interpret the following BTCUSD 1-minute chart snapshot.

Indicators:
- Price: {price}
- RSI: {rsi}
- EMA9: {ema9}
- EMA21: {ema21}
- VWAP: {vwap}
- Bollinger Midline: {bb_mid}
- MACD Histogram: {macd_hist}
- Volume Oscillator: {volume_osc}x average
- ATR: {atr}
- BB Width: {bb_width}
- Daily Session Range: {session_range}

{candle_summary}

Decide:
1. Go long, short, or stay out?
2. Suggest Entry, Stop-Loss, and Take-Profit.
3. Explain your logic briefly.
4. Rate your confidence from 0–100.
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )

        decision = response.choices[0].message.content
        print("🧠 GPT decision:\n", decision)

        # Log all relevant data to CSV
        with open(LOGFILE, mode="a", newline="") as file:
            writer = csv.writer(file)
            if file.tell() == 0:
                writer.writerow([
                    "timestamp", "price", "rsi", "ema9", "ema21", "vwap", "bb_mid", "macd_hist",
                    "volume_osc", "atr", "bb_width", "session_range",
                    "c1_open", "c1_high", "c1_low", "c1_close",
                    "c2_open", "c2_high", "c2_low", "c2_close",
                    "c3_open", "c3_high", "c3_low", "c3_close",
                    "gpt_decision"
                ])
            writer.writerow([
                datetime.now().isoformat(), price, rsi, ema9, ema21, vwap, bb_mid, macd_hist,
                volume_osc, atr, bb_width, session_range,
                c1.get("open"), c1.get("high"), c1.get("low"), c1.get("close"),
                c2.get("open"), c2.get("high"), c2.get("low"), c2.get("close"),
                c3.get("open"), c3.get("high"), c3.get("low"), c3.get("close"),
                decision.strip().replace("\n", " ")
            ])

        return jsonify({"decision": decision}), 200

    except Exception as e:
        print("❌ Error handling webhook:", e)
        return jsonify({"error": str(e)}), 400
