#!/usr/bin/env python3
"""
Offline unit tests for MarketStructureEngine pure logic.
Pine Script itself runs only on TradingView; these tests mirror exported helpers.
"""
from __future__ import annotations

import re
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MSE = ROOT / "pine" / "market_structure_engine.pine"
CHART = ROOT / "pine" / "market_structure_chart.pine"
STRAT = ROOT / "pine" / "khakster_structure_strategy.pine"

PIVOT_REVERSE = 0
PIVOT_PULLBACK = 1
PIVOT_SETTLEMENT = 2

PIP = 0.0001  # non-JPY forex


def tr_to_price(tr_pips: float) -> float:
    return PIP * tr_pips


def zones_overlap(t1: float, b1: float, t2: float, b2: float) -> bool:
    return not (b1 > t2 or t1 < b2)


def tf_importance(tf: str) -> int:
    return {"M": 5, "W": 4, "D": 3, "240": 2, "60": 1}.get(tf, 0)


def pivot_kind_short(k: int) -> str:
    return "PB" if k == PIVOT_PULLBACK else "Set" if k == PIVOT_SETTLEMENT else "Rev"


def kind_score_bonus(k: int) -> int:
    return 15 if k == PIVOT_REVERSE else -18 if k == PIVOT_PULLBACK else -28


def is_settlement_pivot(revert_pips: float, tr_pips: float, candle_cls: int) -> bool:
    return revert_pips <= tr_pips * 1.15 and candle_cls <= 1


def level_birth_score(tf: str, ftc_cred: bool, candle_cls: int, pivot_kind: int) -> int:
    sc = tf_importance(tf) * 20
    sc += 25 if ftc_cred else 5
    sc += 8 if candle_cls == 2 else (4 if candle_cls >= 3 else 0)
    sc += kind_score_bonus(pivot_kind)
    return max(sc, 0)


def leg_node_top(opens: list[float], closes: list[float], off: int, span: int) -> float:
    n = None
    for i in range(off, off + span):
        v = max(opens[i], closes[i])
        n = v if n is None else max(n, v)
    return n


def leg_node_bot(opens: list[float], closes: list[float], off: int, span: int) -> float:
    n = None
    for i in range(off, off + span):
        v = min(opens[i], closes[i])
        n = v if n is None else min(n, v)
    return n


def price_in_zone(hi: float, lo: float, z_top: float, z_bot: float) -> bool:
    return hi >= z_bot and lo <= z_top


def price_break_zone(is_high: bool, c: float, z_top: float, z_bot: float) -> bool:
    return c > z_top if is_high else c < z_bot


def ftc_touch_signal(
    is_high: bool,
    hi: float,
    lo: float,
    prev_hi: float,
    prev_lo: float,
    ftc_top: float,
    ftc_bot: float,
    ftc_cred: bool,
    pivot_kind: int,
    broken: bool,
    ftc_spent: bool,
) -> bool:
    in_now = price_in_zone(hi, lo, ftc_top, ftc_bot)
    in_prev = price_in_zone(prev_hi, prev_lo, ftc_top, ftc_bot)
    return (
        pivot_kind == PIVOT_REVERSE
        and ftc_cred
        and not broken
        and not ftc_spent
        and in_now
        and not in_prev
    )


@dataclass
class MockLevel:
    tf: str
    zone_top: float
    zone_bot: float
    is_high: bool
    broken: bool = False


def suppressed_by_higher_tf(tf: str, z_top: float, z_bot: float, is_high: bool, existing: list[MockLevel]) -> bool:
    for lv in existing:
        if (
            not lv.broken
            and lv.is_high == is_high
            and tf_importance(lv.tf) > tf_importance(tf)
            and zones_overlap(z_top, z_bot, lv.zone_top, lv.zone_bot)
        ):
            return True
    return False


class TestMSELogic(unittest.TestCase):
    def test_zones_overlap(self):
        self.assertTrue(zones_overlap(1.10, 1.09, 1.095, 1.085))
        self.assertFalse(zones_overlap(1.10, 1.09, 1.08, 1.07))
        self.assertFalse(zones_overlap(1.10, 1.09, 1.20, 1.11))

    def test_tf_importance_order(self):
        self.assertGreater(tf_importance("M"), tf_importance("W"))
        self.assertGreater(tf_importance("D"), tf_importance("240"))

    def test_settlement_pivot(self):
        self.assertTrue(is_settlement_pivot(50, 52, 1))
        self.assertFalse(is_settlement_pivot(80, 52, 1))

    def test_level_birth_score_reverse_vs_pullback(self):
        rev = level_birth_score("D", True, 2, PIVOT_REVERSE)
        pb = level_birth_score("D", True, 2, PIVOT_PULLBACK)
        self.assertGreater(rev, pb)
        self.assertEqual(rev - pb, 15 - (-18))

    def test_leg_node(self):
        o = [1.0, 1.01, 1.02, 1.03, 1.04]
        c = [1.005, 1.015, 1.025, 1.035, 1.045]
        self.assertAlmostEqual(leg_node_top(o, c, 2, 3), 1.045)
        self.assertAlmostEqual(leg_node_bot(o, c, 2, 3), 1.02)

    def test_overlap_suppression(self):
        higher = MockLevel("D", 1.105, 1.095, True)
        self.assertTrue(suppressed_by_higher_tf("240", 1.104, 1.096, True, [higher]))
        self.assertFalse(suppressed_by_higher_tf("D", 1.104, 1.096, True, [higher]))

    def test_ftc_touch_signal(self):
        self.assertTrue(
            ftc_touch_signal(True, 1.1000, 1.0998, 1.1020, 1.1015, 1.101, 1.099, True, PIVOT_REVERSE, False, False)
        )
        self.assertFalse(
            ftc_touch_signal(True, 1.1005, 1.0995, 1.1005, 1.0995, 1.101, 1.099, True, PIVOT_REVERSE, False, False)
        )
        self.assertFalse(
            ftc_touch_signal(True, 1.1005, 1.0995, 1.1015, 1.1005, 1.101, 1.099, True, PIVOT_PULLBACK, False, False)
        )

    def test_price_break_zone(self):
        self.assertTrue(price_break_zone(True, 1.11, 1.10, 1.09))
        self.assertFalse(price_break_zone(True, 1.095, 1.10, 1.09))


class TestPineStatic(unittest.TestCase):
    def test_no_undefined_o2_c2(self):
        text = MSE.read_text()
        self.assertNotIn("o2", text)
        self.assertNotIn("c2", text)

    def test_pack_field_count_chart_match(self):
        chart = CHART.read_text()
        mse = MSE.read_text()
        self.assertIn("bKind, bTh", chart)
        self.assertIn("p.pivotKind, p.thPips", mse)
        # empty bear pack has 14 fields
        self.assertRegex(mse, r"\[0, 0\.0, 0\.0, 0\.0, 0, 1, 0\.0, 0\.0, 0\.0, 0\.0, 0, 0, 0, 0\.0\]")

    def test_score_label_signature(self):
        chart = CHART.read_text()
        mse = MSE.read_text()
        self.assertIn("scoreLabel(sc, cred, 0, pivotKind)", chart)
        self.assertIn("export scoreLabel(int sc, bool ftcCred, int touches, int pivotKind)", mse)

    def test_structure_level_has_pivot_kind(self):
        mse = MSE.read_text()
        self.assertIn("int pivotKind", mse)
        self.assertIn("p.pivotKind)", mse)

    def test_version_and_library_decl(self):
        for path in (MSE, CHART, STRAT):
            text = path.read_text()
            self.assertRegex(text, r"//@version=5")
        self.assertIn('library("MarketStructureEngine"', MSE.read_text())

    def test_tf_desc_poll_order(self):
        chart = CHART.read_text()
        self.assertIn("structureTfCodesDesc()", chart)

    def test_strategy_uses_reverse_only(self):
        strat = STRAT.read_text()
        self.assertIn("PIVOT_REVERSE", strat)
        self.assertIn("ftcTouchSignal", strat)


def run_static_lint() -> list[str]:
    """Lightweight Pine sanity checks."""
    issues: list[str] = []
    for path in (MSE, CHART, STRAT):
        text = path.read_text()
        if "YOUR_USER" in text:
            issues.append(f"INFO {path.name}: YOUR_USER placeholder (expected before publish)")
        opens = text.count("(") + text.count("[")
        # rough bracket balance
        if text.count("(") != text.count(")"):
            issues.append(f"WARN {path.name}: unbalanced parentheses")
        if text.count("[") != text.count("]"):
            issues.append(f"WARN {path.name}: unbalanced brackets")
    return issues


if __name__ == "__main__":
    print("=== MarketStructureEngine — static lint ===")
    for msg in run_static_lint():
        print(msg)
    print()
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestMSELogic))
    suite.addTests(loader.loadTestsFromTestCase(TestPineStatic))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
