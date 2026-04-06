"""
Holt Tankstellen-Stammdaten und aktuelle Preise von der Tankerkönig-API.
Wird sowohl beim Start als auch zyklisch vom Scheduler aufgerufen.
"""
import logging
from datetime import datetime

import httpx

import config
from db import Price, Station, get_session

log = logging.getLogger(__name__)
BASE = "https://creativecommons.tankerkoenig.de/json"


def fetch_stations() -> None:
    """Tankstellen im Umkreis abrufen und in DB einpflegen (upsert)."""
    try:
        r = httpx.get(
            f"{BASE}/list.php",
            params={
                "lat": config.LAT,
                "lng": config.LNG,
                "rad": config.RADIUS_KM,
                "sort": "dist",
                "type": "all",
                "apikey": config.API_KEY,
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        log.error("Fehler beim Abrufen der Tankstellen: %s", exc)
        return

    if not data.get("ok"):
        log.error("API-Fehler (Tankstellen): %s", data.get("message"))
        return

    with get_session() as s:
        for st in data["stations"]:
            existing = s.get(Station, st["id"])
            if existing:
                # Stammdaten aktuell halten (Name/Adresse können sich ändern)
                existing.name         = st.get("name", "")
                existing.brand        = st.get("brand", "")
                existing.street       = st.get("street", "")
                existing.house_number = str(st.get("houseNumber", ""))
                existing.post_code    = str(st.get("postCode", ""))
                existing.place        = st.get("place", "")
                existing.dist_km      = round(st.get("dist", 0), 2)
            else:
                s.add(Station(
                    id=st["id"],
                    name=st.get("name", ""),
                    brand=st.get("brand", ""),
                    street=st.get("street", ""),
                    house_number=str(st.get("houseNumber", "")),
                    post_code=str(st.get("postCode", "")),
                    place=st.get("place", ""),
                    lat=st.get("lat"),
                    lng=st.get("lng"),
                    dist_km=round(st.get("dist", 0), 2),
                ))
        s.commit()

    log.info("Tankstellen synchronisiert: %d Stationen", len(data["stations"]))


def fetch_prices() -> None:
    """Aktuelle Preise für alle bekannten Tankstellen abrufen."""
    with get_session() as s:
        station_ids = [row.id for row in s.query(Station).all()]

    if not station_ids:
        log.warning("Keine Tankstellen in der DB – überspringe Preisabfrage.")
        return

    try:
        r = httpx.get(
            f"{BASE}/prices.php",
            params={"ids": ",".join(station_ids), "apikey": config.API_KEY},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        log.error("Fehler beim Abrufen der Preise: %s", exc)
        return

    if not data.get("ok"):
        log.error("API-Fehler (Preise): %s", data.get("message"))
        return

    now = datetime.now()
    rows = []
    for sid, p in data["prices"].items():
        # Auch geschlossene Tankstellen speichern (Preis gilt weiter)
        rows.append(Price(
            station_id=sid,
            e5=p.get("e5"),
            e10=p.get("e10"),
            diesel=p.get("diesel"),
            recorded_at=now,
        ))

    with get_session() as s:
        s.add_all(rows)
        s.commit()

    log.info("Preise erfasst: %d Tankstellen um %s UTC", len(rows), now.strftime("%H:%M"))
