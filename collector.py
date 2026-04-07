"""
Holt Tankstellen-Stammdaten und aktuelle Preise von der Tankerkönig-API.
Speichert nur wenn sich ein Preis tatsächlich geändert hat.
"""
import logging
from datetime import datetime

import httpx

import config
from db import Price, Station, get_session

log = logging.getLogger(__name__)
BASE = "https://creativecommons.tankerkoenig.de/json"

# Letzter bekannter Preis je Tankstelle – im Speicher gehalten um DB-Abfragen
# bei jedem Zyklus zu vermeiden. Format: {station_id: (e5, e10, diesel)}
_last_known: dict[str, tuple] = {}


def _load_last_known() -> None:
    """Beim Start letzte bekannte Preise aus der DB laden."""
    with get_session() as s:
        station_ids = [row.id for row in s.query(Station).all()]
        for sid in station_ids:
            last = (
                s.query(Price)
                .filter(Price.station_id == sid)
                .order_by(Price.recorded_at.desc())
                .first()
            )
            if last:
                _last_known[sid] = (last.e5, last.e10, last.diesel)
    log.info("Letzte Preise geladen: %d Tankstellen", len(_last_known))


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
    """Aktuelle Preise abrufen – nur bei Preisänderung speichern."""
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
    new_rows = []
    changed = 0
    skipped = 0

    for sid, p in data["prices"].items():
        e5     = p.get("e5")
        e10    = p.get("e10")
        diesel = p.get("diesel")

        # Preise nur speichern wenn sich mindestens ein Wert geändert hat
        current = (e5, e10, diesel)
        if _last_known.get(sid) == current:
            skipped += 1
            continue

        new_rows.append(Price(
            station_id=sid,
            e5=e5,
            e10=e10,
            diesel=diesel,
            recorded_at=now,
        ))
        _last_known[sid] = current
        changed += 1

    if new_rows:
        with get_session() as s:
            s.add_all(new_rows)
            s.commit()

    log.info(
        "Preisabfrage %s: %d geändert, %d unverändert",
        now.strftime("%H:%M"), changed, skipped,
    )
