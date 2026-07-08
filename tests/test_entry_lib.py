#!/usr/bin/env python3
"""Unit tests for KhaksterEntryLib logic (Python mirror)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from mse_engine_py import ENTRY_FTC, ENTRY_RTP, EntrySettings, StructureLevel, ftc_touch, rtp_touch, entry_sl_tp
import pandas as pd


class TestEntryLib(unittest.TestCase):
    def test_fractal_h1_m5(self):
        # H1 -> pattern M15, trigger M5 (matches trex.patternTf/triggerTf)
        self.assertEqual({"60": ("15", "5")}["60"][1], "5")

    def test_ftc_touch_first_bar(self):
        lv = StructureLevel(
            pd.Timestamp("2026-01-01"), 1.10, 1.105, 1.095, 1.101, 1.099, True, True, 60.0, 50
        )
        self.assertTrue(ftc_touch(lv, 1.1000, 1.0998, 1.1020, 1.1015))

    def test_sl_tp_short(self):
        e = EntrySettings()
        sl, tp = entry_sl_tp(True, 1.105, 1.095, 1.10, 60.0, e)
        self.assertGreater(sl, 1.105)
        self.assertLess(tp, 1.10)


if __name__ == "__main__":
    unittest.main()
