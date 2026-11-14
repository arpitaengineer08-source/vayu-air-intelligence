import numpy as np, pandas as pd, plotly.express as px, plotly.graph_objects as go, streamlit as st
from plotly.subplots import make_subplots
from config import CITIES, DB, EVENTS
from src import forecast as fc, indices as ix, pipeline as pl

st.set_page_config(page_title="VAYU | Air intelligence", page_icon="🌫️", layout="wide")
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;700;800&family=Manrope:wght@400;500;600&display=swap');
html,body,[class*="css"],.stMarkdown{font-family:'Manrope',sans-serif}
.stApp{background:#0b1020}
[data-testid=stSidebar]{background:#0e1430;border-right:1px solid #26305c}
h1,h2,h3{font-family:'Sora',sans-serif!important;letter-spacing:-.02em}
.logo{font:800 2.4rem 'Sora';letter-spacing:-.04em;color:#fff;margin:0}
.tag{color:#8a93b8;font-size:.82rem;margin-bottom:1rem;line-height:1.35}
.hero{border-radius:20px;padding:34px 38px;border:1px solid #ffffff22;margin-bottom:18px;
 background:linear-gradient(115deg,#121936 0%,#121936 30%,var(--haze) 140%)}
.hero .big{font:800 6.2rem/1 'Sora';letter-spacing:-.05em;color:var(--haze)}
.hero .cap{font:700 1.5rem 'Sora';color:#fff;margin:6px 0 4px}
.hero .sub{color:#aab2d5;max-width:640px;font-size:1rem}
.hero .row{display:flex;gap:42px;align-items:flex-end;flex-wrap:wrap}
.kpi{background:#121936;border:1px solid #26305c;border-left:4px solid var(--c);border-radius:14px;padding:14px 18px}
.kl{color:#8a93b8;font-size:.85rem}.kv{font:700 1.9rem 'Sora';color:#fff}.ks{color:var(--c);font-size:.85rem}
.pill{display:inline-block;background:#1b2350;border:1px solid #26305c;color:#aab2d5;padding:4px 12px;border-radius:99px;font-size:.78rem}
.note{background:#121936;border:1px dashed #3a4580;border-radius:12px;padding:12px 16px;color:#aab2d5;font-size:.88rem}
.rec{background:#121936;border:1px solid var(--c);border-radius:14px;padding:16px 20px;font-size:1.05rem}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

@st.cache_data(show_spinner="Building dataset...")
def data():
    if not DB.exists(): pl.build()
    return {t: pl.read(t) for t in ["hourly", "fires_daily", "fire_points", "coverage", "meta"]}

@st.cache_data(show_spinner="Training forecast models (about 20 seconds the first time)...")
def forecast_city(city, _H):
    return fc.run(_H[_H.city == city])

def style(fig, h=360):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=h,
                      font=dict(family="Manrope", color="#cbd5e1"), margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-.18))
    fig.update_xaxes(gridcolor="#1c2550"); fig.update_yaxes(gridcolor="#1c2550")
    return fig

def kpi(label, val, sub="", color="#f59e0b"):
    return f'<div class="kpi" style="--c:{color}"><div class="kl">{label}</div><div class="kv">{val}</div><div class="ks">{sub}</div></div>'

def head(t, s):
    st.markdown(f"## {t}"); st.caption(s)

D = data(); H = D["hourly"]; SRC = D["meta"].source.iloc[0]
PAGES = ["Air intelligence", "Forecast centre", "Fire and weather", "CampusShield", "Mobility and exposure", "Policy simulator"]
with st.sidebar:
    st.markdown('<p class="logo">VAYU</p><div class="tag">From pollution monitoring to pollution-aware decision making</div>', unsafe_allow_html=True)
    page = st.radio("Page", PAGES, label_visibility="collapsed")
    city = st.selectbox("Location", list(CITIES))
    st.markdown(f'<span class="pill">{SRC}</span>', unsafe_allow_html=True)

c = H[H.city == city]; res = forecast_city(city, H); p = fc.tomorrow_profile(c, res)
last = c.iloc[-1]; prev = c[c.ts <= last.ts - pd.Timedelta(hours=24)].iloc[-1]
f24 = res["fc"][0]; cat24, col24 = ix.aqi_cat(f24["aqi"]); cat_now, col_now = ix.aqi_cat(last.aqi)

# ------------------------------------------------------------------ 1
if page == PAGES[0]:
    st.markdown(f'''<div class="hero" style="--haze:{col24}"><div class="row"><div><div class="sub">{city}, 24 hours from now</div>
    <div class="big">{f24["aqi"]:.0f}</div></div><div><div class="cap">{cat24} air expected</div>
    <div class="sub">Forecast PM2.5 {f24["pred"]:.0f} µg/m³ (80% range {f24["lo"]:.0f} to {f24["hi"]:.0f}). Chance of a high-pollution day, PM2.5 above 90: {f24["p_high"]*100:.0f}%. This is a forecast, not a guaranteed warning.</div></div></div></div>''', unsafe_allow_html=True)
    a, b, d_, e = st.columns(4)
    a.markdown(kpi("AQI now", f"{last.aqi:.0f}", cat_now, col_now), unsafe_allow_html=True)
    b.markdown(kpi("PM2.5", f"{last.pm25:.0f}", "µg/m³", "#38bdf8"), unsafe_allow_html=True)
    d_.markdown(kpi("PM10", f"{last.pm10:.0f}", "µg/m³", "#a78bfa"), unsafe_allow_html=True)
    dl = last.pm25 - prev.pm25
    e.markdown(kpi("Change in 24 hours", f"{dl:+.0f}", "µg/m³ PM2.5", "#fb923c" if dl > 0 else "#34d399"), unsafe_allow_html=True)
    l, r = st.columns([1, 1.4])
    lead = c.tail(24).aqi.mean(); lb = H[H.ts > last.ts - pd.Timedelta(hours=24)].groupby("city").aqi.mean().sort_values()
    lbd = lb.rename("aqi").reset_index()
    l.plotly_chart(style(px.bar(lbd, x="aqi", y="city", orientation="h", title="Average AQI, last 24 hours", color="aqi", color_continuous_scale=["#34d399", "#facc15", "#fb923c", "#f43f5e", "#c026d3"]).update_layout(coloraxis_showscale=False, showlegend=False), 400), use_container_width=True)
    dd = H[H.ts > last.ts - pd.Timedelta(days=30)].assign(day=lambda x: x.ts.dt.date).groupby(["day", "city"]).pm25.mean().reset_index()
    r.plotly_chart(style(px.line(dd, x="day", y="pm25", color="city", title="Daily PM2.5, last 30 days"), 400), use_container_width=True)
    hm = H[H.ts > last.ts - pd.Timedelta(days=7)].assign(h=lambda x: x.ts.dt.hour).pivot_table(index="city", columns="h", values="pm25")
    st.plotly_chart(style(px.imshow(hm, aspect="auto", color_continuous_scale="YlOrRd", title="When is the air worst? Average PM2.5 by hour, last 7 days"), 340), use_container_width=True)
    cov = D["coverage"].sort_values("coverage_pct")
    st.markdown("#### Data coverage")
    st.markdown('<div class="note">Monitoring is not uniform, so this shows how much of each city’s raw PM2.5 record was present before gaps up to 12 hours were interpolated. Cities with lower coverage deserve less confidence.</div>', unsafe_allow_html=True)
    st.plotly_chart(style(px.bar(cov, x="coverage_pct", y="city", orientation="h", range_x=[max(0, cov.coverage_pct.min() - 5), 100], labels={"coverage_pct": "Raw coverage %"}), 300), use_container_width=True)

# ------------------------------------------------------------------ 2
elif page == PAGES[1]:
    head("Forecast centre", f"{city}: 24, 48 and 72 hour PM2.5 forecasts, tested against a naive persistence baseline on a time-ordered hold-out.")
    cols = st.columns(3)
    for col, f in zip(cols, res["fc"]):
        n, cl = ix.aqi_cat(f["aqi"])
        col.markdown(kpi(f'In {f["h"]} hours · {f["ts"]:%a %H:%M}', f'AQI {f["aqi"]:.0f}', f'{n} · PM2.5 {f["pred"]:.0f} ({f["lo"]:.0f} to {f["hi"]:.0f}) · {f["p_high"]*100:.0f}% high-day chance', cl), unsafe_allow_html=True)
    tail = c.tail(168); fs = res["fc"]
    fig = go.Figure(go.Scatter(x=tail.ts, y=tail.pm25, name="Observed", line=dict(color="#38bdf8")))
    fig.add_trace(go.Scatter(x=[tail.ts.iloc[-1]] + [f["ts"] for f in fs], y=[tail.pm25.iloc[-1]] + [f["pred"] for f in fs], name="Forecast", mode="lines+markers", line=dict(color="#f59e0b", dash="dot"),
                             error_y=dict(type="data", symmetric=False, array=[0] + [f["hi"] - f["pred"] for f in fs], arrayminus=[0] + [f["pred"] - f["lo"] for f in fs])))
    fig.add_hline(y=90, line=dict(color="#f43f5e", dash="dash"), annotation_text="PM2.5 90")
    st.plotly_chart(style(fig.update_layout(title="Last 7 days and forecast, with 80% intervals"), 380), use_container_width=True)
    l, r = st.columns(2)
    bt = res["backtest"]
    l.plotly_chart(style(px.line(bt, x="ts", y=["Actual", "Predicted", "Persistence"], title="Hold-out check: 24 hour forecast vs actual"), 340), use_container_width=True)
    imp = res["importance"].rename("importance").rename_axis("feature").reset_index()
    r.plotly_chart(style(px.bar(imp, x="importance", y="feature", orientation="h", title="What drives the model (RandomForest importance)").update_layout(showlegend=False), 340), use_container_width=True)
    m = res["metrics"]
    st.dataframe(m.style.format({"MAE": "{:.1f}", "RMSE": "{:.1f}", "R2": "{:.2f}"}), hide_index=True, use_container_width=True)
    st.markdown('<div class="note">Reading this table honestly: persistence is a strong baseline at 24 hours because air quality changes slowly. The models predict the change from the current level, and a blend with persistence gives the most reliable gain. Beating persistence by more needs weather forecast inputs for the target day, which is the next upgrade.</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------ 3
elif page == PAGES[2]:
    head("Fire and weather intelligence", "Spatial and temporal associations between fire detections, wind and PM2.5. Detections do not prove that a given fire caused a given city’s pollution.")
    fp = D["fire_points"]
    if len(fp):
        days = st.slider("Fire detections: last N days", 1, 14, 5)
        fpp = fp[fp.acq_date > fp.acq_date.max() - pd.Timedelta(days=days)]
        m = px.scatter_map(fpp, lat="latitude", lon="longitude", size="frp", color="frp", color_continuous_scale="YlOrRd", size_max=9, opacity=.7, zoom=5.4, center=dict(lat=29.9, lon=76.4), map_style="carto-darkmatter", height=480)
        cs = H[H.ts > last.ts - pd.Timedelta(hours=24)].groupby("city").pm25.mean()
        m.add_trace(go.Scattermap(lat=[CITIES[k][0] for k in cs.index], lon=[CITIES[k][1] for k in cs.index], mode="markers+text", text=[f"{k} {v:.0f}" for k, v in cs.items()], textposition="top right",
                                  marker=dict(size=14, color="#38bdf8"), name="City PM2.5 (24h mean)", textfont=dict(color="#fff")))
        st.plotly_chart(m.update_layout(margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)"), use_container_width=True)
    else:
        st.info("No fire detections loaded. Set the FIRMS_MAP_KEY environment variable and run: python run_pipeline.py --live")
    fd = D["fires_daily"].set_index("date").fires
    dly = c.assign(date=c.ts.dt.normalize()).groupby("date").agg(pm25=("pm25", "mean"), wind=("wind_speed", "mean"), rh=("rh", "mean")).tail(120)
    dly["fires"] = fd.reindex(dly.index).fillna(0)
    l, r = st.columns(2)
    sf = make_subplots(specs=[[{"secondary_y": True}]])
    sf.add_trace(go.Bar(x=dly.index, y=dly.fires, name="Fire detections", marker_color="#7c2d12"), secondary_y=False)
    sf.add_trace(go.Scatter(x=dly.index, y=dly.pm25, name=f"{city} PM2.5", line=dict(color="#38bdf8")), secondary_y=True)
    l.plotly_chart(style(sf.update_layout(title="Fire detections vs PM2.5, last 120 days"), 360), use_container_width=True)
    dfull = c.assign(date=c.ts.dt.normalize()).groupby("date").pm25.mean()
    lag = {k: dfull.corr(fd.shift(k).reindex(dfull.index)) for k in range(0, 8)}
    r.plotly_chart(style(px.bar(x=list(lag), y=list(lag.values()), labels={"x": "Days fires lead PM2.5", "y": "Correlation"}, title="Lagged association (not causation)"), 360), use_container_width=True)
    w = c.tail(24 * 60).copy(); w["dir"] = (((w.wind_dir + 11.25) // 22.5) % 16).astype(int)
    names = "N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW".split()
    rose = w.groupby("dir").pm25.mean().reset_index().assign(d=lambda x: [names[i] for i in x.dir])
    ev = []
    for nm, dt in EVENTS.items():
        t0 = pd.Timestamp(dt); 
        for ph, (a, b) in {"7 days before": (-7, 0), "Event (0 to 2 days)": (0, 3), "After (3 to 9 days)": (3, 10)}.items():
            s = dfull[(dfull.index >= t0 + pd.Timedelta(days=a)) & (dfull.index < t0 + pd.Timedelta(days=b)) & (dfull.index <= dfull.index.max())]
            if len(s): ev.append(dict(Event=nm, Phase=ph, PM25=s.mean(), Days=len(s)))
    l, r = st.columns(2)
    l.plotly_chart(style(px.bar_polar(rose, r="pm25", theta="d", color="pm25", color_continuous_scale="YlOrRd", title="Pollution rose: PM2.5 by wind direction (last 60 days)"), 380), use_container_width=True)
    if ev:
        r.plotly_chart(style(px.bar(pd.DataFrame(ev), x="Event", y="PM25", color="Phase", barmode="group", title="Pollution events: before, during and after"), 380), use_container_width=True)

# ------------------------------------------------------------------ 4
elif page == PAGES[3]:
    head("CampusShield", "Decision support for educational continuity. These are scenarios under stated assumptions, not medical or government directives.")
    a, b, d_ = st.columns(3)
    students = a.number_input("Students on campus", 100, 100000, 5000, 100)
    start, end = b.slider("Campus hours", 6, 20, (9, 16)); cm = d_.slider("Commute, one way (minutes)", 10, 120, 45, 5)
    a, b, d_, e = st.columns(4)
    out_h = a.slider("Outdoor activity hours", 0, 4, 1); indoor = b.slider("Indoor exposure factor", .2, 1.0, .5, .05, help="Share of outdoor PM2.5 reaching indoor air. Assumption.")
    shift = d_.slider("Shift timings later by (hours)", 0, 4, 2); hyb = e.slider("Hybrid: % still on campus", 0, 100, 30, 10)
    with st.expander("PDI component weights"):
        w = {k: st.slider(k, 0., 1., v, .05) for k, v in ix.PDI_WEIGHTS.items()}
    ch = cm / 60
    win = p[start:end]; commute = np.r_[p[int(max(start - ch, 0)):start] if start > 0 else p[:1], p[end:int(min(end + ch + 1, 24))] if end < 24 else p[-1:]]
    wnd = c.tail(24)
    score, comps = ix.pdi(win, wnd.wind_speed.mean(), wnd.rh.mean(), commute, w); lab, lc = ix.pdi_label(score)
    l, r = st.columns([1, 1.5])
    g = go.Figure(go.Indicator(mode="gauge+number", value=score, title={"text": f"Pollution Disruption Index · {lab}"}, gauge=dict(axis=dict(range=[0, 100]), bar=dict(color=lc),
                  steps=[dict(range=[0, 25], color="#12362e"), dict(range=[25, 50], color="#3b3a14"), dict(range=[50, 75], color="#432a14"), dict(range=[75, 100], color="#43141f")])))
    l.plotly_chart(style(g, 330), use_container_width=True)
    r.plotly_chart(style(px.bar(pd.DataFrame({"score": list(comps.values()), "component": list(comps)}), x="score", y="component", orientation="h", range_x=[0, 100], title="What the score is made of").update_layout(showlegend=False), 330), use_container_width=True)
    st.markdown(f'<div class="rec" style="--c:{lc}">{ix.recommendation(score)}</div>', unsafe_allow_html=True)
    sc = ix.scenario_table(p, start, end, cm, out_h, indoor, shift, hyb, students)
    st.plotly_chart(style(px.bar(sc, x="Scenario", y=["Campus hours", "Commute"], barmode="stack", title="Estimated exposure per student (µg·h/m³)"), 360), use_container_width=True)
    st.dataframe(sc.style.format({"Campus hours": "{:.0f}", "Commute": "{:.0f}", "Avg exposure": "{:.0f}", "Change vs normal %": "{:+.1f}"}), hide_index=True, use_container_width=True)
    st.markdown('<div class="note">Exposure is estimated ambient PM2.5 × time, adjusted by the indoor factor you set. It is not an inhaled dose, which also depends on breathing rate and indoor conditions. Component weights and the index method are documented in src/indices.py.</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------ 5
elif page == PAGES[4]:
    head("Mobility and exposure", "Compare commute options by estimated exposure, and find the lower-exposure departure windows.")
    a, b = st.columns(2); km = a.slider("Trip distance (km)", 1, 40, 12); dep = b.slider("Departure hour", 5, 22, 8)
    MODES = {"Walk": (5, 1.0), "Cycle": (15, 1.0), "Bus": (20, .8), "Car (AC)": (25, .5), "Metro": (30, .4)}
    def expo(h, mode):
        sp, f = MODES[mode]; mins = km / sp * 60
        return ix.integrate(p, h, h + mins / 60) * f, mins
    rows = []; curves = {}
    for m in MODES:
        e_, mins = expo(dep, m); rows.append({"Mode": m, "Minutes": mins, "Exposure index": e_})
        curves[m] = [expo(h, m)[0] for h in range(5, 23)]
    t = pd.DataFrame(rows).sort_values("Exposure index")
    st.dataframe(t.style.format({"Minutes": "{:.0f}", "Exposure index": "{:.0f}"}), hide_index=True, use_container_width=True)
    mode = st.selectbox("Mode for the departure-window chart", list(MODES), index=2)
    cv = pd.DataFrame({"Hour": range(5, 23), "Exposure": curves[mode]}); bh = int(cv.loc[cv.Exposure.idxmin(), "Hour"])
    st.plotly_chart(style(px.bar(cv, x="Hour", y="Exposure", color="Exposure", color_continuous_scale="YlOrRd", title=f"Exposure by departure hour · {mode} · {city}").update_layout(coloraxis_showscale=False), 340), use_container_width=True)
    st.markdown(f'<div class="rec" style="--c:#38bdf8">Lowest estimated exposure for this trip: leave at {bh}:00.</div>', unsafe_allow_html=True)
    st.markdown('<div class="note">The in-vehicle factors (bus 0.8, AC car 0.5, metro 0.4) are assumptions you can change in MODES. This estimates ambient exposure along the trip time, not inhaled dose. Route-segment pollution needs a routing API and is on the roadmap.</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------ 6
else:
    head("Policy simulator", "What-if scenarios under explicit assumptions. This shows how exposure could change, not proof that an intervention produces a given reduction.")
    l, r = st.columns(2)
    with l:
        s_f = st.slider("Share of PM2.5 from crop burning (assumption, %)", 0, 50, 20) / 100; cut_f = st.slider("Reduction in burning detections (%)", 0, 100, 40) / 100
        s_i = st.slider("Share of PM2.5 from industry (assumption, %)", 0, 40, 15) / 100; cut_i = st.slider("Industrial emission reduction (%)", 0, 100, 20) / 100
    with r:
        s_t = st.slider("Share of PM2.5 from road transport (assumption, %)", 0, 40, 20) / 100; pt = st.slider("Public transport shift of car trips (%)", 0, 100, 20) / 100
        out_cut = st.slider("Reduction in outdoor campus activity (%)", 0, 100, 50) / 100; sh = st.slider("Campus timings shifted later (hours)", 0, 4, 0)
    red = min(s_f * cut_f + s_i * cut_i + s_t * pt * .6, .9); p2 = p * (1 - red)
    base = ix.scenario_table(p, 9, 16, 45, 1, .5, 0, 100, 1000).iloc[0]; new = ix.scenario_table(p2, 9, 16, 45, 1 * (1 - out_cut), .5, sh, 100, 1000).iloc[1 if sh else 0]
    a, b, d_ = st.columns(3)
    a.markdown(kpi("Ambient PM2.5 change", f"-{red*100:.0f}%", f"{p.mean():.0f} to {p2.mean():.0f} µg/m³ (tomorrow mean)", "#34d399"), unsafe_allow_html=True)
    b.markdown(kpi("AQI category", f"{ix.aqi_cat(float(ix.cpcb_aqi(p.mean())))[0]} to {ix.aqi_cat(float(ix.cpcb_aqi(p2.mean())))[0]}", "", "#38bdf8"), unsafe_allow_html=True)
    d_.markdown(kpi("Campus exposure per student", f'{(new["Avg exposure"]/base["Avg exposure"]-1)*100:+.0f}%', "9:00 to 16:00, 45 min commute", "#f59e0b"), unsafe_allow_html=True)
    fig = go.Figure([go.Scatter(x=list(range(24)), y=p, name="Baseline", line=dict(color="#f43f5e")), go.Scatter(x=list(range(24)), y=p2, name="Scenario", line=dict(color="#34d399"))])
    st.plotly_chart(style(fig.update_layout(title="Estimated hourly PM2.5 tomorrow", xaxis_title="Hour"), 340), use_container_width=True)
    st.markdown("#### Historical what-if: what does this city's own data say about burning?")
    dly = c.assign(date=c.ts.dt.normalize()).groupby("date").agg(pm=("pm25", "mean"), wind=("wind_speed", "mean"), rh=("rh", "mean"))
    dly["fires"] = D["fires_daily"].set_index("date").fires.shift(1).reindex(dly.index)
    dly = dly.dropna()
    if dly.fires.sum() > 0:
        X = np.c_[np.ones(len(dly)), dly.fires, dly.wind, dly.rh]; beta = np.linalg.lstsq(X, dly.pm.values, rcond=None)[0]
        season = dly[dly.index.month.isin([10, 11])]
        st.markdown(f'<div class="note">A simple regression controlling for wind and humidity associates about {beta[1]:.3f} µg/m³ of daily PM2.5 with each extra fire detection the day before. With 40% fewer detections in Oct to Nov, the implied average change is about {-beta[1]*season.fires.mean()*.4:.0f} µg/m³. This is an association from observational data, not a causal estimate.</div>', unsafe_allow_html=True)
    else:
        st.info("No fire data loaded for this what-if. Set FIRMS_MAP_KEY and run the pipeline with --live.")
