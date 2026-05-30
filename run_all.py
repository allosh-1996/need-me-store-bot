"""
Run Bot + Dashboard + Keep-Alive together
"""
import threading
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)

def run_dashboard():
    from web_dashboard import run_dashboard as _run
    _run()

def run_bot():
    import main
    main.main()

if __name__ == '__main__':
    # شغل الداشبورد بالخلفية
    t = threading.Thread(target=run_dashboard, daemon=True)
    t.start()
    print("✅ Dashboard started on port 5000")

    # شغل البوت بالفورغراوند
    run_bot()
