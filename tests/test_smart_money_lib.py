#!/usr/bin/env python3
"""Unit tests for Smart Money zone confluence logic."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))


def zones_overlap(t1, b1, t2, b2):
    return not (b1 > t2 or t1 < b2)


def overlap_ratio(t1, b1, t2, b2):
    h1 = t1 - b1
    top = min(t1, t2)
    bot = max(b1, b2)
    return 0.0 if h1 <= 0 else max(top - bot, 0.0) / h1


def volume_confirms(z_top, z_bot, poc, va_top, va_bot, min_ratio=0.15):
    poc_in = z_bot <= poc <= z_top
    va_hit = zones_overlap(va_top, va_bot, z_top, z_bot) and overlap_ratio(z_top, z_bot, va_top, va_bot) >= min_ratio
    return poc_in or va_hit


def confluence(z_top, z_bot, is_high, liq, ob, vol, min_conf=2):
    cnt = sum([liq, ob, vol])
    return cnt >= min_conf, cnt


class TestSmartMoney(unittest.TestCase):
    def test_overlap(self):
        self.assertTrue(zones_overlap(1.10, 1.09, 1.095, 1.085))

    def test_volume_poc_in_zone(self):
        self.assertTrue(volume_confirms(1.10, 1.09, 1.095, 1.11, 1.08))

    def test_confluence_two_of_three(self):
        ok, cnt = confluence(1.10, 1.09, True, True, True, False, 2)
        self.assertTrue(ok)
        self.assertEqual(cnt, 2)

    def test_confluence_needs_two(self):
        ok, _ = confluence(1.10, 1.09, True, True, False, False, 2)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
