-- PostgreSQL + PostGIS schema (production target; the demo app uses SQLite with the same logical tables)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE station (city TEXT PRIMARY KEY, state TEXT, geom GEOGRAPHY(Point, 4326));
CREATE TABLE hourly (ts TIMESTAMPTZ, city TEXT REFERENCES station(city), pm25 REAL, pm10 REAL, aqi REAL,
  temp REAL, rh REAL, wind_speed REAL, wind_dir REAL, rain REAL, fires REAL, PRIMARY KEY (city, ts));
CREATE TABLE fire_points (acq_date DATE, geom GEOGRAPHY(Point, 4326), frp REAL);
CREATE INDEX ON fire_points USING GIST (geom);
