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

def parse_gpt_json_response(response_text):
    """Parse GPT response and extract JSON, fallback to structured parsing if needed"""
    try:
        # Try to find JSON in the response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx != -1:
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)
        else:
            # Fallback: create structured response from free text
            return {
                "decision": "stay_out",
                "confidence": 50,
                "entry_price": None,
                "stop_loss": None,
                "take_profit": None,
                "reasoning": response_text[:200] + "..." if len(response_text) > 200 else response_text
            }
    except:
        # If JSON parsing fails, return safe default
        return {
            "decision": "stay_out",
            "confidence": 30,
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "reasoning": "Failed to parse GPT response properly"
        }

@app.route('/', methods=['GET'])
def home():
    return "✅ ChartGPT Flask server v2.0 with structured JSON output and CSV logging."

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        print("🚀 Raw payload:")
        print(request.data)

        data = json.loads(request.data)
        print("✅ Parsed JSON:")
        print(json.dumps(data, indent=2))

        # Extract all the technical indicators
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

        # Enhanced prompt for structured JSON output
        prompt = f"""You are ChartGPT, an AI trading assistant. Analyze this BTCUSD 1-minute chart data and respond with ONLY valid JSON in this exact format:

{{
  "decision": "go_long" | "go_short" | "stay_out",
  "confidence": 0-100,
  "entry_price": number or null,
  "stop_loss": number or null,
  "take_profit": number or null,
  "reasoning": "brief 1-2 sentence explanation"
}}

Market Data:
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

Return ONLY the JSON object, no other text."""

        # Get GPT response
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1  # Lower temperature for more consistent JSON
        )

        raw_decision = response.choices[0].message.content
        print("🧠 GPT raw response:\n", raw_decision)

        # Parse the structured response
        structured_decision = parse_gpt_json_response(raw_decision)
        print("📊 Parsed structured decision:", structured_decision)

        # Enhanced CSV logging with new columns
        with open(LOGFILE, mode="a", newline="") as file:
            writer = csv.writer(file)
            
            # Check if file is empty to write headers
            if file.tell() == 0:
                writer.writerow([
                    "timestamp", "price", "rsi", "ema9", "ema21", "vwap", "bb_mid", "macd_hist",
                    "volume_osc", "atr", "bb_width", "session_range",
                    "c1_open", "c1_high", "c1_low", "c1_close",
                    "c2_open", "c2_high", "c2_low", "c2_close",
                    "c3_open", "c3_high", "c3_low", "c3_close",
                    "decision", "confidence", "entry_price", "stop_loss", "take_profit", "reasoning", "raw_gpt_response"
                ])
            
            # Write the enhanced data
            writer.writerow([
                datetime.now().isoformat(), price, rsi, ema9, ema21, vwap, bb_mid, macd_hist,
                volume_osc, atr, bb_width, session_range,
                c1.get("open"), c1.get("high"), c1.get("low"), c1.get("close"),
                c2.get("open"), c2.get("high"), c2.get("low"), c2.get("close"),
                c3.get("open"), c3.get("high"), c3.get("low"), c3.get("close"),
                structured_decision["decision"],
                structured_decision["confidence"], 
                structured_decision["entry_price"],
                structured_decision["stop_loss"],
                structured_decision["take_profit"],
                structured_decision["reasoning"],
                raw_decision.replace("\n", " ").replace(",", ";")  # Clean for CSV
            ])

        return jsonify({
            "status": "success",
            "structured_decision": structured_decision,
            "raw_response": raw_decision
        }), 200

    except Exception as e:
        print("❌ Error handling webhook:", e)
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)