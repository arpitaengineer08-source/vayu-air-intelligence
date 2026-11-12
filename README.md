# VAYU: air quality and urban disruption intelligence

From pollution monitoring to pollution-aware decision making. A Delhi-NCR, Haryana and Punjab case study with
forecasting, fire and weather analysis, a campus decision-support module (CampusShield), commute exposure and a policy simulator.

## Run it (VS Code)
Mac / Linux:
```bash
cd vayu                       # the unzipped folder, not the Trash or Downloads root
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py          # fetches LIVE data on first run (internet needed), refreshes hourly
```
Windows: use `.venv\Scripts\activate` instead of the `source` line.
Optional: `python run_pipeline.py --live` fetches without the app, and `python run_pipeline.py` builds offline demo data.
If an old `data/vayu.sqlite` exists from an earlier version, delete it so the app fetches fresh live data.

Live mode pulls up to 92 days of hourly PM2.5/PM10 (Open-Meteo CAMS model) and weather for 9 cities.
For satellite fires, get a free NASA FIRMS key and set `FIRMS_MAP_KEY` first. Tests: `pytest`.

## Data honesty (important for interviews)
- **The app is live-first.** It fetches on startup, hourly, and via the sidebar button. If there is no internet it falls back to synthetic demo data and says so.
- **Offline demo data is synthetic** shaped like the real world (seasons, stubble season, Diwali, NW winds, stagnation, gaps). The app badge says so. It exists so the project runs anywhere.
- **Live mode uses CAMS model-based PM2.5 (about 45 km grid, so Delhi, Gurugram and Faridabad look similar), not CPCB station readings.** Attribution: CAMS ENSEMBLE data via Open-Meteo. AQI is a CPCB-style sub-index from PM2.5 only.
  Connectors for CPCB/OpenAQ (API key needed) and ERA5 are the next step; add them in `src/pipeline.py`.
- Forecasts use persistence as the baseline and report where models do and do not beat it.

## Structure
```
app.py                Streamlit product (6 pages, custom design)
config.py             cities, events, paths
run_pipeline.py       ingest -> clean -> store -> export
src/pipeline.py       connectors, demo generator, validation, SQLite, Power BI CSV export
src/forecast.py       features, time-ordered split, RF / XGBoost / blend vs persistence, intervals
src/indices.py        CPCB-style AQI, Pollution Disruption Index, campus scenarios
sql/                  PostgreSQL + PostGIS schema and analytical queries (window functions, ST_DWithin)
tests/                unit tests
exports/              powerbi_hourly.csv, powerbi_daily.csv (created by the pipeline; load into Power BI)
```

## Not built yet (roadmap)
Power BI report file (CSVs are ready), GeoPandas/PostGIS spatial joins (SQL is written), route-segment exposure (needs a routing API),
weather-forecast features for the target day, CPCB/OpenAQ/ERA5 connectors, deployment.

## Resume bullets (edit to match what you actually run)
- Built an end-to-end air-quality analytics platform: automated ingestion, validation (coverage, gap interpolation), SQLite/PostgreSQL storage and a 6-page Streamlit product.
- Forecast 24/48/72h PM2.5 with time-ordered validation against a persistence baseline (MAE, RMSE, R²) and 80% prediction intervals.
- Designed a transparent Pollution Disruption Index and a campus scenario engine comparing offline, shifted and hybrid schedules.
- Analysed fire-detection lags and wind-direction associations while documenting limits (association, not causation).

## Likely interview questions
Why persistence as a baseline? Why a time-ordered split? What is wrong with using current weather to forecast tomorrow? How does coverage affect confidence? Why is the PDI not an official index?
