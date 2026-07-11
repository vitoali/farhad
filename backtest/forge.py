"""Python port of code 004 — AlphaX FORGE pattern engine (default inputs).

Faithful to the Pine geometry, with two documented deviations for honest testing:
1. Signal time = the bar where the pattern is first DETECTED (isNewPattern),
   entry = next bar open ("honest"), while the Pine script reports entry at the
   open of the historical breakout bar ("claimed"). Both are recorded.
2. Warmup gate lowered from 600 to 100 bars so 1-month windows on 1h/4h are
   testable; HTF bias uses the last CLOSED 1h bar (no intrabar leak).
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from indicators import atr_rma, ema, true_range

# ---- default inputs (locked) ----
COOLDOWN = 5
SYM_TOL = 0.10
LVL_TOL = 0.03
MIN_SIZE_PCT = 0.005
MIN_ATR_MULT = 1.0
ATR_LEN = 14
LB = 10                      # pivot left/right
BREAK_ATR = 1.0
MIN_BRK_BAR = 1
MIN_RR = 1.5
SL_PCT_TGT = 0.25
CHOP_LEN = 14
CHOP_MAX = 62.0
MIN_CONF = 5
VOL_MULT = 1.2
VOL_LEN = 20
WARMUP_GATE = 100            # Pine uses 600; documented deviation
SCAN_LIMIT = max(MIN_BRK_BAR, LB) + 10   # = 20


@dataclass
class Detection:
    name: str
    bull: bool
    entry_claimed: float     # open of breakout bar (what Pine reports)
    stop: float
    target: float
    start_idx: int
    breakout_idx: int
    conf: int = 0


def _project(x1, y1, x2, y2, x):
    return y1 if x2 == x1 else y1 + (y2 - y1) / (x2 - x1) * (x - x1)


def _near(v1, v2, tol):
    return abs(v1 - v2) <= abs((v1 + v2) / 2) * tol


class ForgeEngine:
    def __init__(self, df: pd.DataFrame, htf_df: pd.DataFrame | None):
        self.df = df
        self.o = df["open"].to_numpy(); self.h = df["high"].to_numpy()
        self.l = df["low"].to_numpy(); self.c = df["close"].to_numpy()
        self.v = df["volume"].to_numpy(); self.t = df["time"].to_numpy()
        self.n = len(df)
        self.atr = atr_rma(df, ATR_LEN).to_numpy()
        self.vol_sma = df["volume"].rolling(VOL_LEN).mean().to_numpy()
        # choppiness index
        tr1 = true_range(df).rolling(CHOP_LEN).sum()
        hh = df["high"].rolling(CHOP_LEN).max(); ll = df["low"].rolling(CHOP_LEN).min()
        rng = (hh - ll)
        self.chop = np.where(rng > 0, 100 * np.log10(tr1 / rng) / np.log10(CHOP_LEN), 50.0)
        # HTF bias from last closed 1h bar (EMA21/55 as in the Pine defaults)
        if htf_df is not None and len(htf_df) > 60:
            hc = htf_df["close"]
            f = ema(hc, 21).to_numpy(); s = ema(hc, 55).to_numpy()
            close_times = htf_df["time"].to_numpy() + 3600
            self._htf = (close_times, hc.to_numpy(), f, s)
        else:
            self._htf = None
        self.ph: list[tuple[float, int]] = []   # newest first: (price, bar)
        self.pl: list[tuple[float, int]] = []

    # ---- pivots (strict, symmetric LB) ----
    def _confirm_pivots(self, i: int):
        if i < 2 * LB:
            return
        j = i - LB
        w_h = self.h[i - 2 * LB: i + 1]; cand_h = self.h[j]
        if (np.delete(w_h, LB) < cand_h).all():
            self.ph.insert(0, (cand_h, j))
            if len(self.ph) > 500:
                self.ph.pop()
        w_l = self.l[i - 2 * LB: i + 1]; cand_l = self.l[j]
        if (np.delete(w_l, LB) > cand_l).all():
            self.pl.insert(0, (cand_l, j))
            if len(self.pl) > 500:
                self.pl.pop()

    def htf_state(self, i: int):
        if self._htf is None:
            return False, False
        ct, hc, f, s = self._htf
        # last 1h bar closed at or before close time of bar i
        sig_time = self.t[i]
        k = np.searchsorted(ct, sig_time, side="right") - 1
        if k < 0 or np.isnan(f[k]) or np.isnan(s[k]):
            return False, False
        bull = f[k] > s[k] and hc[k] > f[k]
        bear = f[k] < s[k] and hc[k] < f[k]
        return bull, bear

    # ---- helpers ----
    def _valid_size(self, height: float, i: int) -> bool:
        return height > max(self.c[i] * MIN_SIZE_PCT, self.atr[i] * MIN_ATR_MULT)

    def _sl(self, bull: bool, entry: float, target: float) -> float:
        dist = abs(target - entry)
        return entry - dist * SL_PCT_TGT if bull else entry + dist * SL_PCT_TGT

    def _break_idx(self, i, x1, y1, x2, y2, is_up):
        for k in range(SCAN_LIMIT, 0, -1):
            idx = i - k
            if idx < 0:
                continue
            proj = _project(x1, y1, x2, y2, idx)
            margin = self.atr[idx] * BREAK_ATR
            if np.isnan(margin):
                continue
            val = self.h[idx] if is_up else self.l[idx]
            if (is_up and val > proj + margin) or (not is_up and val < proj - margin):
                return idx
        return None

    def _entry_claimed(self, b_idx, i):
        if b_idx is None or i - b_idx < 1:
            return None
        return self.o[b_idx]

    def _mk(self, i, name, bull, b_idx, target, start_idx):
        ep = self._entry_claimed(b_idx, i)
        if ep is None or np.isnan(target):
            return None
        sp = self._sl(bull, ep, target)
        risk = abs(ep - sp)
        if risk == 0 or abs(target - ep) / risk < MIN_RR:
            return None
        return Detection(name, bull, ep, sp, target, start_idx, b_idx)

    # ---- detectors (latest pivots; newest first) ----
    def d_double(self, i):
        if len(self.ph) >= 2 and len(self.pl) >= 1:
            p1, p2, mid = self.ph[0], self.ph[1], self.pl[0]
            if p1[1] > mid[1] > p2[1] and _near(p1[0], p2[0], LVL_TOL):
                ht = (p1[0] + p2[0]) / 2 - mid[0]
                if self._valid_size(ht, i):
                    b = self._break_idx(i, mid[1], mid[0], i, mid[0], False)
                    d = self._mk(i, "Double Top", False, b, mid[0] - ht, p2[1])
                    if d:
                        return d
        if len(self.pl) >= 2 and len(self.ph) >= 1:
            p1, p2, mid = self.pl[0], self.pl[1], self.ph[0]
            if p1[1] > mid[1] > p2[1] and _near(p1[0], p2[0], LVL_TOL):
                ht = mid[0] - (p1[0] + p2[0]) / 2
                if self._valid_size(ht, i):
                    b = self._break_idx(i, mid[1], mid[0], i, mid[0], True)
                    return self._mk(i, "Double Bottom", True, b, mid[0] + ht, p2[1])
        return None

    def d_triple(self, i):
        if len(self.ph) >= 3 and len(self.pl) >= 2:
            h1, h2, h3 = self.ph[0], self.ph[1], self.ph[2]
            l1, l2 = self.pl[0], self.pl[1]
            if h1[1] > l1[1] > h2[1] > l2[1] > h3[1] and _near(h1[0], h2[0], LVL_TOL) and _near(h2[0], h3[0], LVL_TOL):
                neck = min(l1[0], l2[0])
                ht = max(h1[0], h2[0], h3[0]) - neck
                if self._valid_size(ht, i):
                    b = self._break_idx(i, l2[1], l2[0], l1[1], l1[0], False)
                    if b is not None:
                        na_ = _project(l2[1], l2[0], l1[1], l1[0], b)
                        d = self._mk(i, "Triple Top", False, b, na_ - ht, h3[1])
                        if d:
                            return d
        if len(self.pl) >= 3 and len(self.ph) >= 2:
            l1, l2, l3 = self.pl[0], self.pl[1], self.pl[2]
            h1, h2 = self.ph[0], self.ph[1]
            if l1[1] > h1[1] > l2[1] > h2[1] > l3[1] and _near(l1[0], l2[0], LVL_TOL) and _near(l2[0], l3[0], LVL_TOL):
                neck = max(h1[0], h2[0])
                ht = neck - min(l1[0], l2[0], l3[0])
                if self._valid_size(ht, i):
                    b = self._break_idx(i, h2[1], neck, h1[1], neck, True)
                    if b is not None:
                        return self._mk(i, "Triple Bottom", True, b, neck + ht, l3[1])
        return None

    def d_hs(self, i):
        if len(self.ph) >= 3 and len(self.pl) >= 2:
            rs, head, ls = self.ph[0], self.ph[1], self.ph[2]
            nr, nl = self.pl[0], self.pl[1]
            if rs[1] > nr[1] > head[1] > nl[1] > ls[1] and head[0] > rs[0] and head[0] > ls[0] and _near(ls[0], rs[0], SYM_TOL):
                neck_avg = (nr[0] + nl[0]) / 2
                ht = head[0] - neck_avg
                if self._valid_size(ht, i):
                    b = self._break_idx(i, nl[1], nl[0], nr[1], nr[0], False)
                    if b is not None:
                        na_ = _project(nl[1], nl[0], nr[1], nr[0], b)
                        d = self._mk(i, "Head & Shoulders", False, b, na_ - ht, ls[1])
                        if d:
                            return d
        if len(self.pl) >= 3 and len(self.ph) >= 2:
            rs, head, ls = self.pl[0], self.pl[1], self.pl[2]
            nr, nl = self.ph[0], self.ph[1]
            if rs[1] > nr[1] > head[1] > nl[1] > ls[1] and head[0] < rs[0] and head[0] < ls[0] and _near(ls[0], rs[0], SYM_TOL):
                neck_avg = (nr[0] + nl[0]) / 2
                ht = neck_avg - head[0]
                if self._valid_size(ht, i):
                    b = self._break_idx(i, nl[1], nl[0], nr[1], nr[0], True)
                    if b is not None:
                        na_ = _project(nl[1], nl[0], nr[1], nr[0], b)
                        return self._mk(i, "Inv Head & Shoulders", True, b, na_ + ht, ls[1])
        return None

    def d_cup(self, i):
        if len(self.ph) >= 2 and len(self.pl) >= 2:
            h_rim, h_left = self.ph[0], self.ph[1]
            l_handle, l_bot = self.pl[0], self.pl[1]
            if l_handle[1] > h_rim[1] > l_bot[1] > h_left[1] and _near(h_rim[0], h_left[0], SYM_TOL) \
               and l_bot[0] < l_handle[0] < h_rim[0]:
                ht = h_rim[0] - l_bot[0]
                if self._valid_size(ht, i):
                    b = self._break_idx(i, h_rim[1], h_rim[0], i, h_rim[0], True)
                    if b is not None:
                        na_ = _project(h_left[1], h_left[0], h_rim[1], h_rim[0], b)
                        d = self._mk(i, "Cup & Handle", True, b, na_ + ht, h_left[1])
                        if d:
                            return d
            l_rim, l_left = self.pl[0], self.pl[1]
            h_handle, h_top = self.ph[0], self.ph[1]
            if h_handle[1] > l_rim[1] > h_top[1] > l_left[1] and _near(l_rim[0], l_left[0], SYM_TOL) \
               and l_rim[0] < h_handle[0] < h_top[0]:
                ht = h_top[0] - l_rim[0]
                if self._valid_size(ht, i):
                    b = self._break_idx(i, l_rim[1], l_rim[0], i, l_rim[0], False)
                    if b is not None:
                        na_ = _project(l_left[1], l_left[0], l_rim[1], l_rim[0], b)
                        return self._mk(i, "Inv Cup & Handle", False, b, na_ - ht, l_left[1])
        return None

    def _two_two(self):
        h1, h2 = self.ph[0], self.ph[1]
        l1, l2 = self.pl[0], self.pl[1]
        su = 0.0 if h1[1] == h2[1] else (h1[0] - h2[0]) / max(1, h1[1] - h2[1])
        sl_ = 0.0 if l1[1] == l2[1] else (l1[0] - l2[0]) / max(1, l1[1] - l2[1])
        return h1, h2, l1, l2, su, sl_

    def d_flag(self, i):
        if len(self.ph) < 2 or len(self.pl) < 2:
            return None
        h1, h2, l1, l2, su, sl_ = self._two_two()
        start = min(h2[1], l2[1])
        pole_len = min(200, i - start + 1)
        if pole_len < 1:
            return None
        pole = self.h[max(0, i - pole_len + 1): i + 1].max() - self.l[max(0, i - pole_len + 1): i + 1].min()
        if pole <= self.atr[i] * 3 or np.isnan(self.atr[i]):
            return None
        parallel = _near(su, sl_, 0.2)
        if su < 0 and sl_ < 0:
            b = self._break_idx(i, h2[1], h2[0], h1[1], h1[0], True)
            if b is not None:
                ub = _project(h2[1], h2[0], h1[1], h1[0], b)
                return self._mk(i, "Bull Flag" if parallel else "Bull Pennant", True, b, ub + pole, h2[1])
        elif su > 0 and sl_ > 0:
            b = self._break_idx(i, l2[1], l2[0], l1[1], l1[0], False)
            if b is not None:
                lb = _project(l2[1], l2[0], l1[1], l1[0], b)
                return self._mk(i, "Bear Flag" if parallel else "Bear Pennant", False, b, lb - pole, h2[1])
        return None

    def d_wedge(self, i):
        if len(self.ph) < 2 or len(self.pl) < 2:
            return None
        h1, h2, l1, l2, su, sl_ = self._two_two()
        height_now = _project(h2[1], h2[0], h1[1], h1[0], i) - _project(l2[1], l2[0], l1[1], l1[0], i)
        if height_now <= 0:
            return None
        if su < 0 and sl_ < 0 and sl_ < su:
            b = self._break_idx(i, h2[1], h2[0], h1[1], h1[0], True)
            return self._mk(i, "Falling Wedge", True, b, h2[0], h2[1]) if b is not None else None
        if su > 0 and sl_ > 0 and sl_ > su:
            b = self._break_idx(i, l2[1], l2[0], l1[1], l1[0], False)
            return self._mk(i, "Rising Wedge", False, b, l2[0], h2[1]) if b is not None else None
        return None

    def d_triangle(self, i):
        if len(self.ph) < 2 or len(self.pl) < 2:
            return None
        h1, h2, l1, l2, su, sl_ = self._two_two()
        start = min(h2[1], l2[1])
        base = abs(_project(h2[1], h2[0], h1[1], h1[0], start) - _project(l2[1], l2[0], l1[1], l1[0], start))
        flat_tol = self.c[i] * 0.0005
        converging = _project(h2[1], h2[0], h1[1], h1[0], i) > _project(l2[1], l2[0], l1[1], l1[0], i)
        if not converging or not self._valid_size(base, i):
            return None
        if (su < 0 and sl_ > 0) or (abs(su) < flat_tol and sl_ > 0):
            b = self._break_idx(i, h2[1], h2[0], h1[1], h1[0], True)
            if b is not None:
                ub = _project(h2[1], h2[0], h1[1], h1[0], b)
                name = "Ascending Triangle" if abs(su) < flat_tol else "Sym Triangle"
                d = self._mk(i, name, True, b, ub + base, h2[1])
                if d:
                    return d
        if (su < 0 and sl_ > 0) or (su < 0 and abs(sl_) < flat_tol):
            b = self._break_idx(i, l2[1], l2[0], l1[1], l1[0], False)
            if b is not None:
                lb = _project(l2[1], l2[0], l1[1], l1[0], b)
                name = "Descending Triangle" if abs(sl_) < flat_tol else "Sym Triangle"
                return self._mk(i, name, False, b, lb - base, h2[1])
        return None

    def d_rect(self, i):
        if len(self.ph) < 2 or len(self.pl) < 2:
            return None
        h1, h2, l1, l2, su, sl_ = self._two_two()
        flat_tol = self.atr[i] * 0.05
        if np.isnan(flat_tol) or abs(su) >= flat_tol or abs(sl_) >= flat_tol or not _near(su, sl_, 0.5):
            return None
        start = min(h2[1], l2[1])
        avg_top = (h1[0] + h2[0]) / 2; avg_bot = (l1[0] + l2[0]) / 2
        height = avg_top - avg_bot
        if not self._valid_size(height, i):
            return None
        b = self._break_idx(i, start, avg_top, i, avg_top, True)
        if b is not None:
            d = self._mk(i, "Rectangle", True, b, avg_top + height, h2[1])
            if d:
                return d
        b = self._break_idx(i, start, avg_bot, i, avg_bot, False)
        if b is not None:
            return self._mk(i, "Rectangle", False, b, avg_bot - height, h2[1])
        return None

    # ---- confluence ----
    def confluence(self, d: Detection, i: int, chop_ok: bool) -> int:
        rr = abs(d.target - d.entry_claimed) / max(1e-12, abs(d.entry_claimed - d.stop))
        score = 2 if rr >= MIN_RR else (1 if rr >= 1.0 else 0)
        bull, bear = self.htf_state(i)
        score += 2 if (d.bull and bull) or (not d.bull and bear) else 0
        score += 1 if chop_ok else 0
        piv_total = len(self.ph) + len(self.pl)
        score += 2 if piv_total >= 12 else (1 if piv_total >= 6 else 0)
        offs = i - d.breakout_idx
        if 0 <= offs < i and not np.isnan(self.vol_sma[d.breakout_idx]) and self.vol_sma[d.breakout_idx] > 0:
            score += 1 if self.v[d.breakout_idx] >= self.vol_sma[d.breakout_idx] * VOL_MULT else 0
        score += 1 if self._valid_size(abs(d.target - d.entry_claimed), i) else 0
        return min(score, 10)

    # ---- main scan ----
    def scan(self) -> pd.DataFrame:
        rows = []
        frozen = None
        for i in range(self.n):
            self._confirm_pivots(i)
            if i <= WARMUP_GATE or len(self.ph) < 2 or len(self.pl) < 2 or i >= self.n - 1:
                continue
            chop_ok = self.chop[i] < CHOP_MAX
            if not chop_ok:
                continue
            best, best_conf = None, -1
            for det in (self.d_double, self.d_triple, self.d_hs, self.d_flag,
                        self.d_wedge, self.d_triangle, self.d_rect, self.d_cup):
                d = det(i)
                if d is None:
                    continue
                conf = self.confluence(d, i, chop_ok)
                if conf > best_conf:
                    best, best_conf = d, conf
            if best is None or best_conf < MIN_CONF:
                continue
            if frozen is not None and abs(best.start_idx - frozen) <= COOLDOWN:
                continue
            frozen = best.start_idx
            honest_entry = self.o[i + 1]
            sign = 1 if best.bull else -1
            hindsight_gap = sign * (honest_entry - best.entry_claimed) / best.entry_claimed * 100
            bull, bear = self.htf_state(i)
            rows.append({
                "sig_idx": i, "time": int(self.t[i]),
                "pattern": best.name, "direction": "long" if best.bull else "short",
                "entry_claimed": best.entry_claimed, "entry_honest": honest_entry,
                "stop_claimed": best.stop, "target": best.target,
                "conf": best_conf,
                "bars_since_break": i - best.breakout_idx,
                "hindsight_gap_pct": round(hindsight_gap, 4),
                "htf_aligned": (best.bull and bull) or (not best.bull and bear),
                "chop_idx": round(float(self.chop[i]), 2),
                "vol_spike": bool(self.v[best.breakout_idx] >= (self.vol_sma[best.breakout_idx] or np.inf) * VOL_MULT)
                             if not np.isnan(self.vol_sma[best.breakout_idx]) else False,
            })
        return pd.DataFrame(rows)
