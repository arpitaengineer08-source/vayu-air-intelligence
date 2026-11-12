"""Transparent, documented indicators: CPCB-style AQI, Pollution Disruption Index, campus scenarios."""
import numpy as np
import pandas as pd

def cpcb_aqi(pm25):
    """Indian CPCB sub-index from PM2.5 only (ug/m3). Piecewise-linear approximation."""
    return np.interp(pm25, [0, 30, 60, 90, 120, 250, 380], [0, 50, 100, 200, 300, 400, 500])

CATS = [(50, "Good", "#34d399"), (100, "Satisfactory", "#a3e635"), (200, "Moderate", "#facc15"),
        (300, "Poor", "#fb923c"), (400, "Very poor", "#f43f5e"), (9999, "Severe", "#c026d3")]

def aqi_cat(a):
    for hi, name, col in CATS:
        if a <= hi:
            return name, col

PDI_WEIGHTS = {"Forecast level": .35, "Duration": .25, "Weather stagnation": .20, "Commute exposure": .20}

def pdi(p_window, wind, rh, p_commute, w=PDI_WEIGHTS):
    """Pollution Disruption Index (0-100). Components stay visible; NOT an official health index."""
    p_window = np.asarray(p_window, float)
    comps = {
        "Forecast level": min(100, float(cpcb_aqi(p_window.mean())) / 5),
        "Duration": 100 * float((p_window > 60).mean()),
        "Weather stagnation": float(60 * np.clip((2.5 - wind) / 2.5, 0, 1) + 40 * np.clip((rh - 60) / 40, 0, 1)),
        "Commute exposure": min(100, float(cpcb_aqi(np.mean(p_commute))) / 5),
    }
    return sum(w[k] * v for k, v in comps.items()) / sum(w.values()), comps

def pdi_label(x):
    return ("Low", "#34d399") if x < 25 else ("Elevated", "#facc15") if x < 50 else ("High", "#fb923c") if x < 75 else ("Severe", "#f43f5e")

def integrate(p, a, b, step=.25):
    """Exposure integral (ug.h/m3) of an hourly profile over [a, b) hours; wraps past midnight."""
    return float(sum(p[int(t) % 24] * step for t in np.arange(a, b, step)))

def scenario_table(p, start, end, commute_min, out_h, indoor_f, shift, hybrid_pct, students):
    """Compare Normal offline / Shifted timings / Hybrid. All numbers are estimates under stated assumptions."""
    p = np.asarray(p, float); ch = commute_min / 60
    def on_campus(s, e):
        win = [p[h % 24] for h in range(int(s), int(e))] or [p.mean()]
        campus = integrate(p, s, e) * indoor_f + out_h * np.mean(win) * (1 - indoor_f)
        commute = integrate(p, s - ch, s) + integrate(p, e, e + ch)
        hrs = sum(p[h % 24] > 90 for h in range(int(s), int(e))) + ch * sum(p[int(t) % 24] > 90 for t in (s - ch / 2, e + ch / 2))
        return campus, commute, hrs
    home = integrate(p, start, end) * indoor_f
    rows = []
    for name, (s, e, share) in {"Normal offline": (start, end, 1.0), "Shifted timings": (start + shift, end + shift, 1.0),
                                "Hybrid / online": (start, end, hybrid_pct / 100)}.items():
        c, m, hrs = on_campus(s, e)
        rows.append({"Scenario": name, "Campus hours": share * c + (1 - share) * home, "Commute": share * m,
                     "Avg exposure": share * (c + m) + (1 - share) * home,
                     "Student-hours above PM2.5 90": round(students * share * hrs)})
    df = pd.DataFrame(rows)
    df["Change vs normal %"] = (df["Avg exposure"] / df["Avg exposure"].iloc[0] - 1) * 100
    return df

def recommendation(score):
    if score < 25: return "Normal operations look reasonable. Keep monitoring the next forecast update."
    if score < 50: return "Review outdoor activities and consider moving them to lower-exposure hours."
    if score < 75: return "Consider restricting outdoor activity and compare the shifted-timing and hybrid scenarios."
    return "Evaluate hybrid or online options, following institutional and official guidance."
