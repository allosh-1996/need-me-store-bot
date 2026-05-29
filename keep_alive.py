"""
Keep-Alive Self-Ping
يمنع البوت من النوم — self-ping كل 4 دقائق.
FIX: حُذف Flask server المنفصل — health endpoint الآن في web_dashboard.py على port 5000.
"""

from threading import Thread
import urllib.request
import time
import logging
import os

logger = logging.getLogger(__name__)

def self_ping():
    """يحكي مع حاله كل 4 دقائق عشان ما ينام"""
    time.sleep(30)

    # جرب تجيب الرابط من متغيرات البيئة
    url = os.environ.get("RAILWAY_STATIC_URL") or \
          os.environ.get("RENDER_EXTERNAL_URL") or \
          os.environ.get("BOT_URL") or \
          "http://localhost:5000"

    ping_url = f"{url}/health"

    while True:
        try:
            urllib.request.urlopen(ping_url, timeout=10)
            logger.debug(f"Self-ping OK — {time.strftime('%H:%M:%S')}")
        except Exception:
            logger.debug(f"Self-ping (local) — {time.strftime('%H:%M:%S')}")
        time.sleep(240)  # كل 4 دقائق

def keep_alive():
    """
    FIX: لا يشغل Flask server منفصل — يستخدم /health من web_dashboard.py (port 5000).
    يشغل فقط self-ping thread.
    """
    ping_thread = Thread(target=self_ping)
    ping_thread.daemon = True
    ping_thread.start()
    logger.info("✅ Self-ping every 4 minutes activated (pinging port 5000)")
