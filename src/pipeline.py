"""Ingest -> clean/validate -> store (SQLite) -> export (CSV for Power BI).

python run_pipeline.py          # demo data (offline)
python run_pipeline.py --live   # Open-Meteo air-quality (CAMS) + weather; NASA FIRMS if FIRMS_MAP_KEY is set
"""
import os, sqlite3
import numpy as np, pandas as pd
from config import CITIES, DATA, DB, EVENTS, EXPORTS, FIRE_BBOX
from .indices import cpcb_aqi

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WX_URL = "https://api.open-meteo.com/v1/forecast"

def _get(url, params):
    import requests
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=60); r.raise_for_status(); return r.json()["hourly"]
        except Exception as e:
            if attempt == 2: raise RuntimeError(f"Live fetch failed ({url.split('/')[2]}): {e}")

def fetch_live(days=92):
    frames = []
    for city, (lat, lon, *_) in CITIES.items():
        base = dict(latitude=lat, longitude=lon, past_days=days, forecast_days=1, timezone="Asia/Kolkata")
        aq = _get(AQ_URL, {**base, "hourly": "pm2_5,pm10"})
        wx = _get(WX_URL, {**base, "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation"})
        df = pd.DataFrame({"ts": pd.to_datetime(aq["time"]), "city": city, "pm25": aq["pm2_5"], "pm10": aq["pm10"]})
        w = pd.DataFrame({"ts": pd.to_datetime(wx["time"]), "temp": wx["temperature_2m"], "rh": wx["relative_humidity_2m"],
                          "wind_speed": np.array(wx["wind_speed_10m"], float) / 3.6, "wind_dir": wx["wind_direction_10m"], "rain": wx["precipitation"]})
        frames.append(df.merge(w, on="ts", how="left"))
    h = pd.concat(frames)
    h = h[h.ts <= pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None).floor("h")]
    h = h.dropna(subset=["pm25"])
    fd, fp = _firms(days)
    h["fires"] = h.ts.dt.normalize().map(fd).fillna(0).values
    return h, fd, fp

def _firms(days):
    key = os.getenv("FIRMS_MAP_KEY")
    empty = pd.DataFrame(columns=["latitude", "longitude", "acq_date", "frp"])
    if not key:
        return pd.Series(dtype=float), empty
    parts, bbox = [], ",".join(map(str, FIRE_BBOX))
    for k in range(0, days, 10):
        start = (pd.Timestamp.now() - pd.Timedelta(days=days - k)).strftime("%Y-%m-%d")
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/{bbox}/10/{start}"
        try: parts.append(pd.read_csv(url)[["latitude", "longitude", "acq_date", "frp"]])
        except Exception as e: print("FIRMS chunk failed:", e)
    fp = pd.concat(parts) if parts else empty
    fp["acq_date"] = pd.to_datetime(fp.acq_date)
    return fp.groupby("acq_date").size().astype(float), fp

def _ar(n, phi, sigma, rng):
    x, e = np.zeros(n), rng.normal(0, sigma, n)
    for i in range(1, n): x[i] = phi * x[i - 1] + e[i]
    return x

def synthetic(days=300, seed=7):
    """Physically-shaped DEMO data (seasonality, stubble season, Diwali, NW winds, stagnation, gaps). Not real measurements."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(end=pd.Timestamp.now().floor("h"), periods=days * 24, freq="h")
    n, doy, hr, month = len(idx), idx.dayofyear.values, idx.hour.values, idx.month.values
    dates = idx.normalize(); ud = pd.DatetimeIndex(dates.unique()); nd = len(ud)
    udoy = ud.dayofyear.values
    fires_d = pd.Series(rng.poisson(1600 * np.exp(-((udoy - 305) / 14.0) ** 2) * (.6 + .8 * rng.random(nd)) + 150 * np.exp(-((udoy - 120) / 10.0) ** 2) + 8), index=ud).astype(float)
    di = pd.Series(np.arange(nd), index=ud).loc[dates].values
    stag = _ar(nd, .8, .55, rng)[di]
    fl = fires_d.rolling(3, min_periods=1).mean().shift(1).bfill().values[di]
    diwali = sum(np.exp(-(((np.asarray((idx - pd.Timestamp(d)).total_seconds())) / 86400 - .6) / 1.1) ** 2) for d in EVENTS.values())
    frames = []
    for c, (lat, lon, state, cf) in CITIES.items():
        ws = np.clip(2.4 - .6 * stag + .8 * np.sin(2 * np.pi * (hr - 9) / 24) + rng.normal(0, .35, n), .2, 12)
        temp = 25 - 11 * np.cos(2 * np.pi * (doy - 15) / 365) + 4 * np.sin(2 * np.pi * (hr - 9) / 24)
        rh = np.clip(52 + 22 * np.cos(2 * np.pi * (doy - 225) / 365) - 12 * np.sin(2 * np.pi * (hr - 9) / 24) + 4 * stag + rng.normal(0, 3, n), 12, 100)
        rain = (rng.random(n) < np.where((month >= 7) & (month <= 9), .07, .008)) * rng.exponential(2., n)
        wd = (np.where((month >= 10) | (month <= 2), 315, 255) + rng.normal(0, 30, n)) % 360
        fw = 0.8 if state == "Punjab" else 1.0
        nw = .6 + .4 * np.cos(np.deg2rad(wd - 315))
        diurnal = 1 + .30 * np.cos(2 * np.pi * (hr - 9) / 24) + .22 * np.cos(2 * np.pi * (hr - 21) / 24)
        season = 80 + 45 * np.cos(2 * np.pi * (doy - 360) / 365)
        pm = (season * np.exp(.30 * stag) / (.55 + .18 * ws) * cf * .9 + .045 * fl * fw * nw) * diurnal * (1 + .9 * diwali)
        pm = np.clip(pm * np.exp(_ar(n, .97, .025, rng)) * np.where(rain > 1, .55, 1), 3, 900)
        pm10 = pm * np.clip(1.75 + .25 * rng.standard_normal(n), 1.2, 2.6)
        for _ in range(rng.integers(5, 25)):
            s0, L = rng.integers(0, n - 40), rng.integers(3, 36); pm[s0:s0 + L] = np.nan
        frames.append(pd.DataFrame(dict(ts=idx, city=c, pm25=pm, pm10=pm10, temp=temp, rh=rh, wind_speed=ws, wind_dir=wd, rain=rain, fires=fires_d.loc[dates].values)))
    pts = []
    for d in ud[-14:]:
        k = int(min(fires_d[d], 300)); pun = rng.random(k) < .7
        pts.append(pd.DataFrame(dict(latitude=np.where(pun, rng.uniform(29.9, 31.4, k), rng.uniform(29.2, 30.5, k)),
                                     longitude=np.where(pun, rng.uniform(74.2, 76.6, k), rng.uniform(76.0, 77.2, k)),
                                     acq_date=d, frp=np.exp(rng.normal(1.5, .6, k)))))
    return pd.concat(frames), fires_d, pd.concat(pts)

def build(live=False):
    DATA.mkdir(exist_ok=True); EXPORTS.mkdir(exist_ok=True)
    h, fd, fp = fetch_live() if live else synthetic()
    src = ("Live: CAMS air quality via Open-Meteo + weather" + (" + NASA FIRMS" if len(fp) else "")) if live else "Demo data (synthetic). Run the pipeline with --live for real data"
    cov = h.groupby("city").pm25.apply(lambda s: round(s.notna().mean() * 100, 1)).rename("coverage_pct").reset_index()
    h = h.sort_values(["city", "ts"])
    for col in ["pm25", "pm10", "temp", "rh", "wind_speed", "wind_dir"]:
        h[col] = h.groupby("city")[col].transform(lambda s: s.interpolate(limit=12, limit_direction="both"))
    h["rain"] = h.rain.fillna(0); h["fires"] = h.fires.fillna(0)
    h = h.dropna(subset=["pm25", "temp"]); h = h[(h.pm25 >= 0) & (h.pm25 < 1000)]
    h["aqi"] = cpcb_aqi(h.pm25).round(0)
    fdf = fd.rename("fires").rename_axis("date").reset_index()
    with sqlite3.connect(DB) as con:
        for name, df in {"hourly": h, "fires_daily": fdf, "fire_points": fp, "coverage": cov, "meta": pd.DataFrame({"source": [src]})}.items():
            df.to_sql(name, con, if_exists="replace", index=False)
    h.to_csv(EXPORTS / "powerbi_hourly.csv", index=False)
    h.assign(date=h.ts.dt.date).groupby(["city", "date"]).agg(pm25=("pm25", "mean"), pm10=("pm10", "mean"), aqi=("aqi", "max"), wind=("wind_speed", "mean"), fires=("fires", "max")).reset_index().to_csv(EXPORTS / "powerbi_daily.csv", index=False)
    print(f"{src}\n{len(h):,} hourly rows | {h.city.nunique()} cities | {h.ts.min():%Y-%m-%d} -> {h.ts.max():%Y-%m-%d}\n{DB}")

def read(table):
    with sqlite3.connect(DB) as con:
        parse = {"hourly": ["ts"], "fires_daily": ["date"], "fire_points": ["acq_date"]}.get(table, [])
        return pd.read_sql(f"select * from {table}", con, parse_dates=parse)
