-- 1. Monthly average and peak PM2.5 per city
SELECT city, date_trunc('month', ts) AS month, ROUND(AVG(pm25)::numeric,1) AS avg_pm25, MAX(pm25) AS peak
FROM hourly GROUP BY 1,2 ORDER BY 1,2;
-- 2. Rank cities by share of hours above PM2.5 90 (window function)
SELECT city, ROUND(100.0*AVG((pm25>90)::int),1) AS pct_hours_poor,
       RANK() OVER (ORDER BY AVG((pm25>90)::int) DESC) AS rnk FROM hourly GROUP BY city;
-- 3. Diwali 2026: before / during / after
SELECT city, CASE WHEN ts < '2026-11-08' THEN 'before' WHEN ts < '2026-11-11' THEN 'during' ELSE 'after' END AS phase,
       ROUND(AVG(pm25)::numeric,1) AS avg_pm25
FROM hourly WHERE ts BETWEEN '2026-11-01' AND '2026-11-18' GROUP BY 1,2;
-- 4. Fire detections within 300 km of each city in the last 3 days (PostGIS)
SELECT s.city, COUNT(*) AS fires_300km FROM station s JOIN fire_points f
  ON ST_DWithin(s.geom, f.geom, 300000) WHERE f.acq_date >= CURRENT_DATE - 3 GROUP BY s.city;
