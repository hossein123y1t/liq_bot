import os
import requests
from flask import Flask
import threading
import time

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")

ACTOR_ID = "feng0928~coinglass-heatmap"
CHECK_INTERVAL = 2 * 60 * 60

def get_heatmap():
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
    params = {"token": APIFY_TOKEN}
    payload = {
        "coin": "BTC",
        "exchange": "Binance",
        "quoteCurrency": "USDT",
        "timeRange": "24h",
        "headless": True
    }
    try:
        r = requests.post(url, params=params, json=payload, timeout=180)
        r.raise_for_status()
        items = r.json()
        if items and len(items) > 0:
            return items[0]
        return None
    except Exception as e:
        print(f"Apify error: {e}")
        return None

def send_telegram_photo(image_url, caption):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": image_url,
            "caption": caption,
            "parse_mode": "HTML"
        }, timeout=30)
    except Exception as e:
        print(f"Telegram error: {e}")

def check_and_send():
    data = get_heatmap()
    if not data or not data.get("success"):
        print("No data or failed")
        return
    image_url = data.get("url")
    if not image_url:
        print("No image URL")
        return
    caption = (
        f"📊 <b>Heatmap لیکوییدیشن BTC</b>\n\n"
        f"صرافی: {data.get('exchange')}\n"
        f"جفت: {data.get('coin')}/{data.get('quoteCurrency')}\n"
        f"بازه: {data.get('timeRange')}\n"
        f"زمان: {data.get('timestamp')}"
    )
    send_telegram_photo(image_url, caption)
    print(f"Heatmap sent at {data.get('timestamp')}")

def background_worker():
    time.sleep(10)
    while True:
        try:
            check_and_send()
        except Exception as e:
            print(f"Worker error: {e}")
        time.sleep(CHECK_INTERVAL)

@app.route("/")
def home():
    return "Bot is running"

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    threading.Thread(target=background_worker, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
