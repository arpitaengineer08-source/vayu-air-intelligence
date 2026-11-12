"""24/48/72h PM2.5 forecasting: persistence baseline vs RandomForest vs XGBoost (HistGB fallback)."""
import math
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from .indices import cpcb_aqi
try:
    from xgboost import XGBRegressor; GB = "XGBoost"
except Exception:
    from sklearn.ensemble import HistGradientBoostingRegressor; GB = "HistGB"

LAGS = (1, 2, 3, 6, 12, 24, 48, 72)
FEATS = [f"l{l}" for l in LAGS] + ["r24", "r72", "hour", "dow", "month", "temp", "rh", "wind_speed", "wd_s", "wd_c", "rain", "fire_l2"]

def feats(df):
    d = df.sort_values("ts").reset_index(drop=True).copy()
    for l in LAGS: d[f"l{l}"] = d.pm25.shift(l)
    d["r24"], d["r72"] = d.pm25.rolling(24).mean(), d.pm25.rolling(72).mean()
    d["hour"], d["dow"], d["month"] = d.ts.dt.hour, d.ts.dt.dayofweek, d.ts.dt.month
    d["wd_s"], d["wd_c"] = np.sin(np.deg2rad(d.wind_dir)), np.cos(np.deg2rad(d.wind_dir))
    d["fire_l2"] = d.fires.rolling(48, min_periods=1).mean()
    return d

def _model(kind):
    if kind == "RandomForest": return RandomForestRegressor(100, min_samples_leaf=5, max_depth=12, max_samples=.5, n_jobs=-1, random_state=0)
    if GB == "XGBoost": return XGBRegressor(n_estimators=200, learning_rate=.05, max_depth=5, subsample=.8, random_state=0)
    return HistGradientBoostingRegressor(max_iter=150, learning_rate=.06, random_state=0)

def run(df, horizons=(24, 48, 72)):
    """Time-ordered 80/20 split (no leakage). Returns forecasts, metrics, backtest and feature importance."""
    d = feats(df); last = d.iloc[[-1]]
    fcs, mets, bt, imp = [], [], None, None
    for h in horizons:
        d["y"] = d.pm25.shift(-h)
        tr = d.dropna(subset=FEATS + ["y"]); k = int(len(tr) * .8)
        X, y = tr[FEATS], tr.y
        base = np.log1p(tr.pm25.values)                      # models learn the log-change vs the current level
        yd = np.log1p(y.values) - base                       # (trees cannot extrapolate raw levels across seasons)
        back = lambda dpred, b: np.expm1(b + dpred)
        preds, fitted = {"Persistence": tr.pm25.values[k:]}, {}
        for name in ("RandomForest", GB):
            m = _model(name).fit(X[:k], yd[:k]); preds[name] = back(m.predict(X[k:]), base[k:]); fitted[name] = m
        preds["Blend (RF + persistence)"] = .5 * (preds["RandomForest"] + preds["Persistence"])
        yt = y.values[k:]
        for n, p in preds.items():
            mets.append(dict(Horizon=f"{h}h", Model=n, MAE=mean_absolute_error(yt, p), RMSE=math.sqrt(mean_squared_error(yt, p)), R2=r2_score(yt, p)))
        best = min((n for n in preds if n != "Persistence"), key=lambda n: mean_absolute_error(yt, preds[n]))
        sigma = float(np.std(yt - preds[best]))
        if h == horizons[0]:
            imp = pd.Series(fitted["RandomForest"].feature_importances_, FEATS).nlargest(10)[::-1]
            bt = pd.DataFrame(dict(ts=tr.ts.values[k:] + np.timedelta64(h, "h"), Actual=yt, Predicted=preds[best], Persistence=preds["Persistence"])).tail(336)
        core = "RandomForest" if best.startswith("Blend") else best
        cur = float(last.pm25.iloc[0])
        pred = float(back(fitted[core].fit(X, yd).predict(last[FEATS])[0], np.log1p(cur)))
        pred = max(.5 * (pred + cur) if best.startswith("Blend") else pred, 0)
        ph = 1 - .5 * (1 + math.erf((90 - pred) / (sigma * math.sqrt(2) + 1e-9)))
        fcs.append(dict(h=h, ts=last.ts.iloc[0] + pd.Timedelta(hours=h), pred=pred, lo=max(pred - 1.28 * sigma, 0), hi=pred + 1.28 * sigma,
                        aqi=float(cpcb_aqi(pred)), p_high=ph, model=best))
    return dict(fc=fcs, metrics=pd.DataFrame(mets), backtest=bt, importance=imp)

def tomorrow_profile(df, res):
    """Hourly PM2.5 estimate for the next day = forecast level x recent diurnal shape (an approximation)."""
    d = df.tail(24 * 30)
    shape = d.groupby(d.ts.dt.hour).pm25.mean().reindex(range(24)).ffill().bfill()
    shape = (shape / shape.mean()).values
    f = res["fc"][0]
    mean = np.clip(f["pred"] / shape[f["ts"].hour], .4 * d.pm25.mean(), 2.5 * d.pm25.mean())
    return mean * shape
