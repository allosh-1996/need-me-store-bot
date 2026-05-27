"""
Keep-Alive Server + Self-Ping
يمنع البوت من النوم - يحكي مع حاله كل 4 دقائق
"""

from flask import Flask
from threading import Thread
import urllib.request
import time
import logging
import os

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

@app.route('/')
def home():
    return "🌙 NexVault Bot — Online ✅"

@app.route('/health')
def health():
    return {"status": "alive", "bot": "NexVault"}, 200

def run_server():
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

def self_ping():
    """يحكي مع حاله كل 4 دقائق عشان ما ينام"""
    # انتظر شوي حتى يشتغل السيرفر
    time.sleep(30)
    
    # جرب تجيب الرابط من متغيرات البيئة
    url = os.environ.get("RAILWAY_STATIC_URL") or \
          os.environ.get("RENDER_EXTERNAL_URL") or \
          os.environ.get("BOT_URL") or \
          "http://localhost:8080"
    
    ping_url = f"{url}/health"
    
    while True:
        try:
            urllib.request.urlopen(ping_url, timeout=10)
            print(f"🏓 Self-ping OK — {time.strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"🏓 Self-ping (local) — {time.strftime('%H:%M:%S')}")
        
        time.sleep(240)  # كل 4 دقائق

def keep_alive():
    # شغل السيرفر
    server_thread = Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # شغل الـ self-ping
    ping_thread = Thread(target=self_ping)
    ping_thread.daemon = True
    ping_thread.start()
    
    print("✅ Keep-alive server started on port 8080")
    print("✅ Self-ping every 4 minutes activated")
