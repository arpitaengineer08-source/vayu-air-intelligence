"""Central configuration for VAYU."""
from pathlib import Path

ROOT = Path(__file__).parent
DATA, EXPORTS = ROOT / "data", ROOT / "exports"
DB = DATA / "vayu.sqlite"

# city: (lat, lon, state, relative pollution factor used ONLY by the demo generator)
CITIES = {
    "Delhi": (28.6139, 77.2090, "Delhi", 1.00),
    "Gurugram": (28.4595, 77.0266, "Haryana", 0.95),
    "Faridabad": (28.4089, 77.3178, "Haryana", 1.00),
    "Sonipat": (28.9931, 77.0151, "Haryana", 1.05),
    "Panipat": (29.3909, 76.9635, "Haryana", 1.00),
    "Rohtak": (28.8955, 76.6066, "Haryana", 0.90),
    "Karnal": (29.6857, 76.9905, "Haryana", 0.85),
    "Patiala": (30.3398, 76.3869, "Punjab", 0.80),
    "Ludhiana": (30.9010, 75.8573, "Punjab", 0.85),
}
EVENTS = {"Diwali 2025": "2025-10-20", "Diwali 2026": "2026-11-08"}
FIRE_BBOX = (73.5, 28.0, 78.0, 32.5)  # west, south, east, north (Punjab-Haryana)
