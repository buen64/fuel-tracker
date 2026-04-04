import os
from dotenv import load_dotenv

load_dotenv()

# Tankerkönig
API_KEY           = os.environ["TANKERKOENIG_API_KEY"]
LAT               = 53.2833   # Tostedt
LNG               = 9.7167
RADIUS_KM         = 10        # Umkreis in km
FETCH_INTERVAL_MIN = 15       # Preisabfrage alle 15 Minuten

# Dashboard
DASH_HOST = "0.0.0.0"        # LAN-Zugriff
DASH_PORT = 8050

# Datenbank
DB_PATH = "fuel_tracker.db"
