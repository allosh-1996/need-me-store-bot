"""
Keep-Alive Server
يمنع البوت من النوم على السيرفرات المجانية
Prevents bot from sleeping on free hosting platforms
"""

from flask import Flask
from threading import Thread
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)  # اخفي logs الـ Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "🌙 Need Me Store Bot — Online ✅"

@app.route('/health')
def health():
    return {"status": "alive", "bot": "Need Me Store"}, 200

def run():
    app.run(host='0.0.0.0', port=8080, debug=False)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    print("✅ Keep-alive server started on port 8080")
