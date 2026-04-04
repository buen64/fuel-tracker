# Fuel Tracker · Raum Tostedt

Kraftstoffpreis-Dashboard auf Basis der Tankerkönig API (MTS-K).  
Läuft lokal auf dem Mac, erreichbar im LAN von Handy und anderen Geräten.

---

## Einrichtung (einmalig)

### 1. Tankstellen-UUID ermitteln
Öffne https://creativecommons.tankerkoenig.de → **Tools → Tankstellenfinder**  
Marker auf Tostedt setzen → Hoyer auswählen → UUID notieren (wird automatisch geladen).

### 2. API-Key einrichten
```bash
cp .env.example .env
# .env öffnen und TANKERKOENIG_API_KEY=<dein-key> eintragen
```

### 3. Conda-Umgebung anlegen
```bash
conda env create -f environment.yml
conda activate fuel-tracker
```

### 4. Starten
```bash
python main.py
```

Dashboard öffnet sich unter:
- **Mac:**   http://localhost:8050
- **Handy:** http://<Mac-IP>:8050  (z. B. http://192.168.1.42:8050)

> Mac-IP ermitteln: `ipconfig getifaddr en0`

---

## Autostart als macOS-Dienst (optional)

```bash
# USERNAME und Pfade in der plist anpassen, dann:
cp com.fueltracker.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.fueltracker.plist
```

| Befehl | Bedeutung |
|---|---|
| `launchctl list \| grep fueltracker` | Status prüfen |
| `launchctl unload ~/Library/LaunchAgents/com.fueltracker.plist` | Dienst stoppen |
| `tail -f logs/stdout.log` | Live-Log anzeigen |

---

## Projektstruktur

```
fuel-tracker/
├── main.py            ← Einstiegspunkt
├── config.py          ← Konfiguration (Koordinaten, Intervall, Port)
├── db.py              ← SQLAlchemy-Modelle (Station, Price)
├── collector.py       ← Tankerkönig-API-Abfragen
├── dashboard.py       ← Plotly-Dash-App
├── .env               ← API-Key (nicht einchecken!)
├── environment.yml    ← Conda-Abhängigkeiten
├── com.fueltracker.plist  ← macOS-Dienst
└── logs/
    ├── stdout.log
    └── stderr.log
```

---

## Erweiterungen

- **Weiterer Umkreis:** `RADIUS_KM` in `config.py` erhöhen (max. 25 km laut API)
- **Häufigere Abfragen:** `FETCH_INTERVAL_MIN` anpassen (min. 5 min empfohlen)
- **Anderer Standort:** `LAT`/`LNG` in `config.py` ändern

## Nützliche befehle

### Live-Log anschauen
tail -f ~/Projects/fuel-tracker/logs/stdout.log

### Dienst stoppen (z.B. für Updates)
launchctl bootout gui/$(id -u)/com.fueltracker

### Dienst wieder starten
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.fueltracker.plist