#!/usr/bin/env python3
"""Generate Persian PDF report for 5m/15m scalp backtest results."""
from __future__ import annotations

from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from fpdf import FPDF

FONT_FA = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"
FONT_FA_B = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf"
FONT_EN = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_EN_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
OUT = Path(__file__).parent / "results" / "backtest_scalp_5m_15m_report.pdf"


def fa(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


def has_persian(text: str) -> bool:
    return any("\u0600" <= c <= "\u06FF" for c in text)


class ReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("FA", "", FONT_FA)
        self.add_font("FA", "B", FONT_FA_B)
        self.add_font("EN", "", FONT_EN)
        self.add_font("EN", "B", FONT_EN_B)
        self.set_auto_page_break(auto=True, margin=15)

    def _txt(self, text: str, bold: bool = False):
        if has_persian(text):
            self.set_font("FA", "B" if bold else "", 10 if not bold else 11)
            return fa(text)
        self.set_font("EN", "B" if bold else "", 9 if not bold else 10)
        return text

    def header(self):
        self.set_font("FA", "B", 12)
        self.cell(0, 8, fa("گزارش بک‌تست 5m و 15m — کریپتو و فارکس"), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_font("EN", "", 8)
        self.cell(0, 6, "farhad project | ~31 days | 50 indicators + 5 Farhad strategies", align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("FA", "", 8)
        self.cell(0, 8, fa(f"صفحه {self.page_no()}"), align="C")

    def h1(self, text: str):
        self.ln(4)
        self.set_font("FA", "B", 13)
        self.set_fill_color(230, 245, 255)
        self.cell(0, 10, fa(text), align="R", new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(2)

    def h2(self, text: str):
        self.ln(2)
        self.set_font("FA", "B", 11)
        self.set_text_color(20, 60, 120)
        self.cell(0, 8, fa(text), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def p(self, text: str):
        self.set_font("FA", "", 10)
        self.multi_cell(0, 6, fa(text), align="R")
        self.ln(1)

    def p_en(self, text: str):
        self.set_font("EN", "", 9)
        self.multi_cell(0, 5, text, align="L")
        self.ln(1)

    def table(self, headers: list[str], rows: list[list[str]], col_widths: list[int] | None = None):
        if col_widths is None:
            w = 190 / len(headers)
            col_widths = [w] * len(headers)
        self.set_font("FA", "B", 9)
        self.set_fill_color(220, 220, 220)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, fa(h), border=1, align="C", fill=True)
        self.ln()
        fill = False
        for row in rows:
            if fill:
                self.set_fill_color(248, 248, 248)
            else:
                self.set_fill_color(255, 255, 255)
            for i, cell in enumerate(row):
                if has_persian(cell):
                    self.set_font("FA", "", 8)
                    val = fa(cell)
                else:
                    self.set_font("EN", "", 8)
                    val = cell
                self.cell(col_widths[i], 7, val, border=1, align="C", fill=True)
            self.ln()
            fill = not fill
        self.ln(2)


def build():
    pdf = ReportPDF()
    pdf.add_page()

    pdf.p(
        "بک‌تست کامل روی تایم‌فریم‌های ۵ دقیقه و ۱۵ دقیقه انجام شد. "
        "۵۶۰ اجرا شامل ۵۰ اندیکاتور و ۵ حالت استراتژی Farhad. "
        "نمادها: BTC، HYPE، BEAT (کریپتو) | XAUUSD، EURUSD (فارکس). "
        "فایل داده: backtest/results/backtest_scalp_5m_15m.json"
    )

    # Crypto top
    pdf.h1("کریپتو — بهترین‌ها (میانگین ۵m + ۱۵m)")
    pdf.table(
        ["رتبه", "اندیکاتور", "avg PF", "avg WR", "بهترین ترکیب"],
        [
            ["1", "RSI Advanced", "4.07", "60.5%", "HYPE 5m PF=10.5"],
            ["2", "Quadapt ML", "2.01", "39.5%", "BTC 5m PF=5.2"],
            ["3", "IFVG", "1.47", "32.3%", "HYPE 5m PF=2.25"],
            ["4", "FVG Retest", "1.40", "43.3%", "BTC 15m"],
            ["5", "FORGE", "1.38", "56.3%", "BEAT 15m"],
            ["6", "Supply/Demand", "1.34", "46.5%", "HYPE 15m"],
            ["7", "KNN Pivot", "1.23", "53.8%", "BEAT 5m"],
            ["8", "Liquidity Shift", "1.16", "41.1%", "HYPE 15m"],
            ["9", "farhad_strict", "1.15", "49.7%", "HYPE 5m PF=2.14"],
        ],
        [12, 38, 22, 22, 96],
    )

    pdf.h2("کریپتو — تفکیک تایم‌فریم")
    pdf.p_en("5m: RSI Advanced (PF=5.0) > Quadapt > KNN Pivot > FORGE > IFVG")
    pdf.p_en("15m: RSI Advanced (PF=3.1) > Quadapt > FVG Retest > Supply/Demand > SR Breaks")

    pdf.h2("کریپتو — بهترین per نماد")
    pdf.table(
        ["نماد", "۵m", "۱۵m"],
        [
            ["BTC", "Quadapt PF=5.2", "FVG Retest PF=1.75"],
            ["HYPE", "RSI Advanced PF=10.5", "RSI Advanced PF=7.8"],
            ["BEAT", "KNN Pivot / FORGE", "Quadapt PF=4.2"],
        ],
        [30, 80, 80],
    )

    pdf.add_page()
    pdf.h1("فارکس — بهترین‌ها (میانگین ۵m + ۱۵m)")
    pdf.table(
        ["رتبه", "اندیکاتور", "avg PF", "avg WR", "بهترین ترکیب"],
        [
            ["1", "IFVG", "2.00", "39.1%", "XAU 15m PF=3.6"],
            ["2", "Supply/Demand", "1.65", "48.7%", "EUR 5m PF=2.04"],
            ["3", "Strong Pullback", "1.60", "60.2%", "XAU 5m PF=2.15"],
            ["4", "FORGE", "1.59", "32.7%", "XAU 5m"],
            ["5", "Liquidity Shift", "1.50", "47.1%", "XAU 15m PF=2.18"],
            ["6", "farhad_standard", "1.49", "58.8%", "XAU 15m PF=2.56"],
            ["7", "farhad_master_strict", "1.48", "40.1%", "EUR 5m PF=3.0"],
            ["8", "Mirage LSP", "1.36", "56.5%", "EUR 5m"],
        ],
        [12, 38, 22, 22, 96],
    )

    pdf.h2("فارکس — تفکیک تایم‌فریم")
    pdf.p_en("5m: farhad_master_strict (EUR PF=3.0) > Supply/Demand > Strong Pullback > IFVG")
    pdf.p_en("15m: IFVG (XAU PF=3.6) > Liquidity Shift > farhad_standard (XAU PF=2.56) > Strong Pullback")

    pdf.h2("فارکس — per نماد")
    pdf.table(
        ["نماد", "۵m", "۱۵m"],
        [
            ["XAUUSD", "Strong Pullback PF=2.15", "IFVG PF=3.6"],
            ["EURUSD", "farhad_master_strict PF=3.0", "Strong Pullback PF=1.9"],
        ],
        [30, 80, 80],
    )

    pdf.h1("استراتژی‌های Farhad روی اسکالپ")
    pdf.table(
        ["استراتژی", "کریپتو avg PF", "فارکس avg PF"],
        [
            ["farhad_strict", "1.15", "1.50"],
            ["farhad_standard", "0.57", "1.49"],
            ["farhad_master_strict", "0.72", "1.48"],
            ["farhad_master", "0.99", "1.19"],
            ["farhad_loose", "0.80", "0.73"],
        ],
        [55, 45, 45],
    )
    pdf.p(
        "نتیجه: Farhad روی فارکس ۵m/۱۵m خوب کار می‌کند؛ "
        "روی کریپتو اسکالپ اندیکاتورهای تکی (RSI Advanced، Quadapt) قوی‌ترند."
    )

    pdf.h1("جمع‌بندی برای ساخت اندیکاتور جدید")
    pdf.table(
        ["بازار", "۵m", "۱۵m"],
        [
            [
                "کریپتو",
                "RSI Advanced + Quadapt + IFVG",
                "RSI Advanced + FVG Retest + Supply/Demand",
            ],
            [
                "فارکس/طلا",
                "Strong Pullback + Supply/Demand + farhad_master_strict",
                "IFVG + Liquidity Shift + farhad_standard",
            ],
        ],
        [28, 81, 81],
    )

    pdf.ln(4)
    pdf.p("Profit Factor (PF) = مجموع سودها تقسیم بر مجموع ضررها | دوره: حدود ۳۱ روز")
    pdf.p("تاریخ گزارش: ۱۲ ژوئیه ۲۰۲۶")
    pdf.p_en("Data file: backtest/results/backtest_scalp_5m_15m.json")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    print(f"Saved: {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    build()
