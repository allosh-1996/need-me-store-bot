from __future__ import annotations

import logging
import os
import threading
import time
import urllib.request

logger = logging.getLogger(__name__)


def start_keepalive() -> None:
    """
    Pings the /health endpoint every 4 minutes to prevent Railway
    from putting the container to sleep on Trial plan.
    Runs in a daemon thread — no impact on bot performance.
    """
    url = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    if not url:
        logger.info("RAILWAY_PUBLIC_DOMAIN not set — keepalive disabled")
        return

    if not url.startswith("http"):
        url = f"https://{url}"

    health_url = f"{url}/health"

    def _ping():
        # Wait 30s after startup before first ping
        time.sleep(30)
        while True:
            try:
                urllib.request.urlopen(health_url, timeout=10)
                logger.debug("Keepalive ping OK")
            except Exception as e:
                logger.debug("Keepalive ping failed (ignored): %s", e)
            time.sleep(240)  # every 4 minutes

    t = threading.Thread(target=_ping, daemon=True, name="keepalive")
    t.start()
    logger.info("✅ Keepalive started → %s", health_url)
