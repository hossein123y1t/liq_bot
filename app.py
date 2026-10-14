import os
import requests
from flask import Flask
import threading
import time

app = Flask(__name__)

# ===== تنظیمات =====
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")

ACTOR_ID = "automation-lab/coinglass-liquidation-heatmap-scraper"
CHECK_INTERVAL = 2 * 60 * 60  # هر 2 ساعت
ALERT_THRESHOLD = 1.0          # فاصله کمتر از 1 درصد

# ===== گرفتن داده از Apify =====
def get_heatmap_data():
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
    params = {"token": APIFY_TOKEN}
    payload = {
        "symbol": "BTC",
        "exchange": "Binance",
        "pair": "BTCUSDT",
        "model": "1",
        "range": "24h"
    }
    try:
        r = requests.post(url, params=params, json=payload, timeout=120)
        r.raise_for_status()
        items = r.json()
        return items[0] if items else None
    except Exception as e:
        print(f"Apify error: {e}")
        return None

# ===== فرستادن پیام به تلگرام =====
def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

# ===== تحلیل و هشدار =====
def check_and_alert():
    data = get_heatmap_data()
    if not data:
        return

    current = data.get("latestClose")
    hotspots = data.get("liquidationHotspots", [])
    if not current or not hotspots:
        return

    closest = min(hotspots, key=lambda h: abs(h.get("distancePercent", 999)))
    dist = abs(closest.get("distancePercent", 999))
    price = closest.get("price")
    intensity = closest.get("aggregateIntensity", 0)
    side = "بالاتر" if closest.get("side") == "above" else "پایین‌تر"

    if dist <= ALERT_THRESHOLD:
        msg = (
            f"🚨 <b>هشدار لیکوییدیشن BTC</b>\n\n"
            f"قیمت فعلی: <b>${current:,.0f}</b>\n"
            f"منطقه پرتراکم: <b>${price:,.0f}</b> ({side})\n"
            f"فاصله: <b>{dist:.2f}%</b>\n"
            f"شدت: <b>${intensity/1e9:,.1f} میلیارد</b>\n\n"
            f"⚠️ احتمال حرکت قیمت به این سمت"
        )
        send_telegram(msg)
        print(f"Alert sent: {dist:.2f}%")

# ===== حلقه پس‌زمینه =====
def background_worker():
    time.sleep(10)
    while True:
        try:
            check_and_alert()
        except Exception as e:
            print(f"Worker error: {e}")
        time.sleep(CHECK_INTERVAL)

# ===== Flask endpoints =====
@app.route("/")
def home():
    return "Bot is running"

@app.route("/health")
def health():
    return "OK"

# ===== اجرا =====
if __name__ == "__main__":
    threading.Thread(target=background_worker, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
