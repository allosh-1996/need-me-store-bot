"""
run_all.py — Start Bot + Dashboard together.

The dashboard runs in a background daemon thread (port 5000).
The bot runs in the foreground and blocks until stopped.
"""
import threading
import logging
import sys
import os

# Ensure the project root is on the path before any local imports
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)

# Import here (after sys.path is set) so both modules resolve correctly
from web_dashboard import run_dashboard
import main as bot_main

if __name__ == "__main__":
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    print("✅ Dashboard started on port 5000")

    bot_main.main()
