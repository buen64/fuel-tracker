# Fuel Tracker · Raum Tostedt

Kraftstoffpreis-Dashboard auf Basis der Tankerkönig API (MTS-K).  
Läuft lokal auf dem Mac, erreichbar im LAN von Handy und anderen Geräten.

---

## Einrichtung (einmalig)

### 1. API-Key einrichten
```bash
echo "TANKERKOENIG_API_KEY=dein-key-hier" > .env
```

### 2. Conda-Umgebung anlegen
```bash
conda env create -f environment.yml
conda activate fuel-tracker
```

### 3. Starten
```bash
python main.py
```

Dashboard öffnet sich unter:
- **Mac:**   http://localhost:8050
- **Handy:** http://<Mac-IP>:8050  (z. B. http://192.168.1.94:8050)

> Mac-IP ermitteln: `ipconfig getifaddr en0`

---

## Autostart als macOS-Dienst (LaunchDaemon)

Der Dienst läuft als LaunchDaemon — damit ist er auch ohne angemeldeten Benutzer aktiv.

```bash
sudo cp com.fueltracker.plist /Library/LaunchDaemons/
sudo chown root:wheel /Library/LaunchDaemons/com.fueltracker.plist
sudo chmod 644 /Library/LaunchDaemons/com.fueltracker.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.fueltracker.plist
```

| Befehl | Bedeutung |
|---|---|
| `sudo launchctl print system/com.fueltracker \| grep -E "state\|exit"` | Status prüfen |
| `sudo launchctl bootout system/com.fueltracker` | Dienst stoppen |
| `sudo launchctl bootstrap system /Library/LaunchDaemons/com.fueltracker.plist` | Dienst starten |
| `tail -f ~/Projects/fuel-tracker/logs/stdout.log` | Live-Log anzeigen |

---

## Energieverwaltung (pmset)

Damit der Dienst und das Dashboard auch ohne angemeldeten Benutzer erreichbar bleiben,
muss verhindert werden, dass der Mac in den Tief- oder Ruheschlaf fällt.

### Einstellungen setzen

| Befehl | Bewirkt |
|---|---|
| `sudo pmset -a sleep 0` | System schläft nie — Netzwerk und Prozesse bleiben aktiv |
| `sudo pmset -a standby 0` | Tiefschlaf (Hibernate) deaktivieren — trennt sonst das Netzwerk nach längerer Zeit |
| `sudo pmset -a displaysleep 30` | Bildschirm nach 30 Minuten ausschalten (unabhängig vom System-Schlaf) |
| `sudo pmset -a powernap 0` | Power Nap deaktivieren (unnötig wenn sleep=0) |
| `sudo pmset -a womp 1` | Wake on Magic Packet — Mac kann per Netzwerk geweckt werden |

> `-a` bedeutet „all" — gilt für Netzbetrieb und Batterie gleichzeitig.  
> Für nur Netzbetrieb `-c`, für nur Batterie `-b` verwenden.

### Einstellungen zurücksetzen

| Befehl | Bewirkt |
|---|---|
| `sudo pmset -a sleep 10` | System schläft nach 10 Minuten |
| `sudo pmset -a standby 1` | Tiefschlaf wieder aktivieren |
| `sudo pmset restoredefaults` | Alle Energieeinstellungen auf Werksstandard zurücksetzen |

### Abfragen

| Befehl | Bewirkt |
|---|---|
| `pmset -g` | Alle aktuellen Energieeinstellungen anzeigen |
| `pmset -g \| grep sleep` | Nur Schlaf-Einstellungen anzeigen |
| `pmset -g \| grep standby` | Tiefschlaf-Status prüfen |
| `pmset -g live` | Aktuelle Werte inkl. Akkustand live anzeigen |
| `pmset -g log \| tail -20` | Letzte 20 Energieereignisse (Schlaf/Aufwachen) anzeigen |

---

## Projektstruktur

```
fuel-tracker/
├── main.py                    ← Einstiegspunkt
├── config.py                  ← Konfiguration (Koordinaten, Intervall, Port)
├── db.py                      ← SQLAlchemy-Modelle (Station, Price)
├── collector.py               ← Tankerkönig-API-Abfragen
├── dashboard.py               ← Plotly-Dash-App
├── .env                       ← API-Key (nicht einchecken!)
├── environment.yml            ← Conda-Abhängigkeiten
├── com.fueltracker.plist      ← macOS-Systemdienst (LaunchDaemon)
└── logs/
    ├── stdout.log
    └── stderr.log
```

---

## Erweiterungen

- **Weiterer Umkreis:** `RADIUS_KM` in `config.py` erhöhen (max. 25 km laut API)
- **Häufigere Abfragen:** `FETCH_INTERVAL_MIN` anpassen (min. 5 min empfohlen)
- **Anderer Standort:** `LAT`/`LNG` in `config.py` ändern

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

## alte Einstellungen am Macbook:
(base) uwe@MacBookAir ~ % pmset -g
System-wide power settings:
Currently in use:
 standby              1
 Sleep On Power Button 1
 hibernatefile        /var/vm/sleepimage
 powernap             1
 networkoversleep     0
 disksleep            10
 sleep                0 (sleep prevented by sharingd, powerd, bluetoothd)
 hibernatemode        3
 ttyskeepawake        1
 displaysleep         30
 tcpkeepalive         1
 lowpowermode         0
 womp                 0
(base) uwe@MacBookAir ~ % 
