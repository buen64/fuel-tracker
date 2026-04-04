"""
Einstiegspunkt: Datenbank initialisieren, Scheduler starten, Dashboard öffnen.
Starten mit: python main.py
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

import config
from collector import fetch_prices, fetch_stations
from dashboard import app
from db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


if __name__ == "__main__":
    # 1. Datenbank anlegen (falls nicht vorhanden)
    init_db()
    log.info("Datenbank bereit.")

    # 2. Tankstellen im Umkreis einmalig laden
    log.info("Lade Tankstellen im Umkreis %d km um Tostedt …", config.RADIUS_KM)
    fetch_stations()

    # 3. Erste Preisabfrage sofort
    log.info("Erste Preisabfrage …")
    fetch_prices()

    # 4. Scheduler: Preise alle 15 min, Stammdaten täglich um 03:00
    scheduler = BackgroundScheduler(timezone="Europe/Berlin")
    scheduler.add_job(
        fetch_prices,
        trigger="interval",
        minutes=config.FETCH_INTERVAL_MIN,
        id="fetch_prices",
        max_instances=1,
    )
    scheduler.add_job(
        fetch_stations,
        trigger="cron",
        hour=3, minute=0,
        id="refresh_stations",
    )
    scheduler.start()
    log.info(
        "Scheduler aktiv: Preise alle %d min · Stammdaten täglich 03:00",
        config.FETCH_INTERVAL_MIN,
    )

    # 5. Dashboard starten (blockierend)
    log.info(
        "Dashboard erreichbar unter http://localhost:%d  |  LAN: http://<mac-ip>:%d",
        config.DASH_PORT, config.DASH_PORT,
    )
    app.run(host=config.DASH_HOST, port=config.DASH_PORT, debug=False)
