import numpy as np
from src import indices as ix

def test_aqi_monotonic_and_bounded():
    x = np.linspace(0, 600, 50); a = ix.cpcb_aqi(x)
    assert (np.diff(a) >= 0).all() and a.max() <= 500

def test_pdi_in_range_and_ordered():
    clean, dirty = np.full(24, 20.), np.full(24, 200.)
    lo, _ = ix.pdi(clean[9:16], 4, 40, clean[:2]); hi, _ = ix.pdi(dirty[9:16], 0.5, 90, dirty[:2])
    assert 0 <= lo < hi <= 100

def test_hybrid_reduces_exposure_when_air_is_dirty():
    t = ix.scenario_table(np.full(24, 150.), 9, 16, 45, 1, .5, 2, 30, 1000)
    assert t.loc[2, "Avg exposure"] < t.loc[0, "Avg exposure"]
