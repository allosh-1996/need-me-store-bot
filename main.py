import threading
import logging
from app.logging import configure_logging
from app.settings import get_settings
from infra.db import init_db
from infra.migrate import run_migrations, verify_schema
from bot.application import build_app
from dashboard.app import run_dashboard

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging()
    logger.info("Starting NexVault Bot...")

    get_settings()

    init_db()
    run_migrations()
    verify_schema()
    logger.info("✅ DB ready")

    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True, name="dashboard")
    dashboard_thread.start()
    logger.info("✅ Dashboard started on port 5000")

    app = build_app()
    logger.info("🚀 NexVault Bot polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
