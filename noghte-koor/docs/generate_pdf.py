#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate Persian educational PDF for Blind Spot (نقطه کور) strategy."""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, KeepTogether, ListFlowable, ListItem, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
import arabic_reshaper
from bidi.algorithm import get_display

ROOT = "/workspace/noghte-koor"
OUT = os.path.join(ROOT, "docs", "آموزش-استراتژی-نقطه-کور.pdf")
ASSETS = os.path.join(ROOT, "assets")

# Fonts
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]

def pick_font(cands):
    for p in cands:
        if os.path.exists(p):
            return p
    raise SystemExit("No TTF font found")

pdfmetrics.registerFont(TTFont("Fa", pick_font(FONT_CANDIDATES)))
pdfmetrics.registerFont(TTFont("FaBold", pick_font(BOLD_CANDIDATES)))

C_BG = HexColor("#0B1220")
C_CARD = HexColor("#111827")
C_ACCENT = HexColor("#F59E0B")
C_BLUE = HexColor("#38BDF8")
C_GREEN = HexColor("#22C55E")
C_RED = HexColor("#EF4444")
C_TEXT = HexColor("#E5E7EB")
C_MUTED = HexColor("#94A3B8")

def fa(text: str) -> str:
    """Reshape Persian/Arabic for correct RTL display in ReportLab."""
    if text is None:
        return ""
    # Keep Latin/numbers mixed; reshape whole string
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)

def P(text, style):
    return Paragraph(fa(text), style)

def make_styles():
    styles = {}
    styles["title"] = ParagraphStyle(
        "title", fontName="FaBold", fontSize=22, leading=32,
        alignment=TA_CENTER, textColor=C_ACCENT, spaceAfter=12
    )
    styles["h1"] = ParagraphStyle(
        "h1", fontName="FaBold", fontSize=16, leading=26,
        alignment=TA_RIGHT, textColor=C_BLUE, spaceBefore=14, spaceAfter=8
    )
    styles["h2"] = ParagraphStyle(
        "h2", fontName="FaBold", fontSize=13, leading=22,
        alignment=TA_RIGHT, textColor=C_ACCENT, spaceBefore=10, spaceAfter=6
    )
    styles["body"] = ParagraphStyle(
        "body", fontName="Fa", fontSize=11, leading=20,
        alignment=TA_RIGHT, textColor=C_TEXT, spaceAfter=6
    )
    styles["bullet"] = ParagraphStyle(
        "bullet", fontName="Fa", fontSize=11, leading=19,
        alignment=TA_RIGHT, textColor=C_TEXT, rightIndent=8, spaceAfter=3
    )
    styles["note"] = ParagraphStyle(
        "note", fontName="Fa", fontSize=10, leading=17,
        alignment=TA_RIGHT, textColor=C_MUTED, spaceAfter=6
    )
    styles["center"] = ParagraphStyle(
        "center", fontName="Fa", fontSize=10, leading=16,
        alignment=TA_CENTER, textColor=C_MUTED
    )
    styles["code"] = ParagraphStyle(
        "code", fontName="Fa", fontSize=9, leading=14,
        alignment=TA_LEFT, textColor=HexColor("#D1FAE5"),
        backColor=HexColor("#064E3B"), borderPadding=6
    )
    return styles

def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(C_BG)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setStrokeColor(HexColor("#1F2937"))
    canvas.setLineWidth(0.5)
    canvas.line(1.8*cm, A4[1]-1.4*cm, A4[0]-1.8*cm, A4[1]-1.4*cm)
    canvas.line(1.8*cm, 1.4*cm, A4[0]-1.8*cm, 1.4*cm)
    canvas.setFont("Fa", 8)
    canvas.setFillColor(C_MUTED)
    canvas.drawCentredString(A4[0]/2, A4[1]-1.1*cm, fa("آموزش استراتژی نقطه کور | Blind Spot"))
    canvas.drawCentredString(A4[0]/2, 0.9*cm, fa(f"صفحه {doc.page}"))
    canvas.restoreState()

def add_image(path, w=16*cm):
    if not os.path.exists(path):
        return Spacer(1, 1)
    # maintain aspect
    from PIL import Image as PILImage
    im = PILImage.open(path)
    iw, ih = im.size
    h = w * ih / iw
    return Image(path, width=w, height=h)

def build():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    styles = make_styles()
    doc = SimpleDocTemplate(
        OUT, pagesize=A4,
        rightMargin=1.8*cm, leftMargin=1.8*cm,
        topMargin=2.0*cm, bottomMargin=2.0*cm
    )
    S = []

    # Cover
    S.append(Spacer(1, 2.2*cm))
    S.append(P("استراتژی نقطه کور", styles["title"]))
    S.append(P("Blind Spot Strategy — آموزش دقیق و کاربردی", styles["title"]))
    S.append(Spacer(1, 0.4*cm))
    S.append(HRFlowable(width="80%", color=C_ACCENT, thickness=2, spaceBefore=4, spaceAfter=12))
    S.append(P(
        "تحلیل یکپارچه بر اساس ویدیوهای آموزشی نقطه کور، مقاله IDR ترجمه‌شده، "
        "و جزوه پرایس‌اکشن رفتارشناسی حرکت قیمت (سعید خاکستر).",
        styles["body"]
    ))
    S.append(Spacer(1, 0.3*cm))
    S.append(P("شامل: منطق کلاسیک روزانه + نسخه لایو تایم‌فریم پایین‌تر + فرمول‌ها + چک‌لیست + کد اندیکاتور", styles["note"]))
    S.append(Spacer(1, 0.6*cm))
    S.append(add_image(os.path.join(ASSETS, "diagram_classic.png"), 15.5*cm))
    S.append(P("نمای شماتیک نقطه کور کلاسیک", styles["center"]))
    S.append(PageBreak())

    # 1. What is Blind Spot
    S.append(P("۱) نقطه کور چیست؟", styles["h1"]))
    S.append(P(
        "«نقطه کور» ترجمه‌ای از مفهوم Blind Spot در مباحث مرتبط با IDR/ATR است. "
        "ایده اصلی این است: وقتی قیمت یک سطح کلیدی را می‌شکند و به اندازه «توان حرکتی/رنج متوسط» "
        "از آن فاصله می‌گیرد، در کندل بعدی (در نسخه کلاسیک: روز بعد) احتمال بازگشت و تاچ دوباره همان سطح بالاست؛ "
        "چون بازار به‌طور متوسط ظرفیت حرکتی محدودی در هر دوره دارد و معمولاً بیش از آن را به‌راحتی ادامه نمی‌دهد.",
        styles["body"]
    ))
    S.append(P(
        "در ویدیوی اصلی تأکید می‌شود که این دیدگاه فقط وقتی اعتبار دارد که بازگشت در همان پنجره زمانی مجاز رخ دهد. "
        "اگر قیمت برنگشت، اردر لیمیت باید حذف شود.",
        styles["body"]
    ))

    # 2. Building blocks
    S.append(P("۲) سه متریک پایه: IDR ، ATR ، TH", styles["h1"]))

    S.append(P("IDR — میانگین رنج دوره (Intra/Daily Range)", styles["h2"]))
    S.append(P(
        "میانگین فاصله High تا Low در N کندل اخیر. مثال ویدیو برای GBPUSD روزانه حدود ۱۰۰ پیپ. "
        "در جزوه، برای میانگین پایدار روزانه حتی دوره نزدیک یک سال کاری فارکس (حدود ۲۶۴) پیشنهاد شده است.",
        styles["body"]
    ))
    S.append(P("IDR = میانگین(High − Low) روی N کندل", styles["code"]))

    S.append(P("ATR — Average True Range", styles["h2"]))
    S.append(P(
        "میانگین True Range که گپ و کلوز قبلی را هم لحاظ می‌کند. در جزوه، ATR ذهنیت نوسان واقعی را می‌سازد "
        "و برای تعریف مسترکندل، گام حرکتی، شکست سطح و اهداف استفاده می‌شود.",
        styles["body"]
    ))
    S.append(P("TrueRange = Max(High−Low , |High−Closeprev| , |Low−Closeprev|)", styles["code"]))

    S.append(P("TH — توان حرکتی (فرمول سعید خاکستر)", styles["h2"]))
    S.append(P(
        "توان حرکتی بر اساس قیمت جاری محاسبه می‌شود. طبق نکات پایانی جزوه:",
        styles["body"]
    ))
    S.append(P("گام بلند (TH) ≈ ۰٫۶۶٪ قیمت جاری  |  گام کوتاه ≈ ۰٫۸ × TH", styles["code"]))
    S.append(P(
        "نکته کاربردی جزوه: توان حرکتی بیشتر برای تایم ساختار است و گام حرکتی برای تایم پترن. "
        "برای EURUSD به‌صورت تقریبی گام‌های ساختار/پترن/تریگر حدود ۶۰ / ۲۰ / ۱۰ پیپ مطرح شده است.",
        styles["note"]
    ))

    data = [
        [fa("کاربرد"), fa("متریک"), fa("تعریف کوتاه")],
        [fa("فاصله از سطح شکسته‌شده"), fa("IDR / ATR / TH"), fa("حدود ۱ رنج برای «آرم» شدن نقطه کور")],
        [fa("تشخیص کندل شکست/مستر"), fa("ATR"), fa("استاندارد ≈ ۸۰٪–۱۲۰٪ ATR")],
        [fa("هدف و استاپ"), fa("مضرب رنج"), fa("TP حدود ۱ تا ۲ رنج؛ SL باقیمانده یا پشت سوئینگ")],
    ]
    t = Table(data, colWidths=[5.2*cm, 3.5*cm, 7.0*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1E293B")),
        ("TEXTCOLOR", (0, 0), (-1, -1), C_TEXT),
        ("FONTNAME", (0, 0), (-1, -1), "Fa"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#334155")),
        ("BACKGROUND", (0, 1), (-1, -1), HexColor("#0F172A")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    S.append(t)
    S.append(PageBreak())

    # 3. Classic strategy
    S.append(P("۳) نسخه کلاسیک نقطه کور (معمولاً Daily)", styles["h1"]))
    S.append(P("قوانین دقیق طبق ویدیوی آموزشی:", styles["body"]))

    steps = [
        "یک سطح معتبر پیدا کنید (معمولاً ناحیه Open/Close کندل‌های مهم، پیوت، یا سطح ساختار).",
        "صبر کنید قیمت سطح را Breakout کند (ترجیحاً کندل شکستِ قوی/لانگ‌بار نسبت به ATR).",
        "قیمت باید حدود ۱ Daily Range / ATR / TH از سطح فاصله بگیرد (مثال GBPUSD ≈ ۱۰۰ پیپ).",
        "فقط در کندل بعدی (روز بعد) روی همان سطح/ناحیه یک Limit Order بگذارید (Sell Limit بعد از شکست نزولی، Buy Limit بعد از شکست صعودی).",
        "اگر همان روز تاچ نشد، اردر را حذف کنید. اعتبار نقطه کور کلاسیک یک دوره است، نه چند روز.",
        "استاپ: پشت کندل شکست یا باقیمانده رنج تا ۱۰۰٪ (مثلاً ورود روی ۸۰٪ رنج ← استاپ ۲۰٪ باقیمانده).",
        "تارگت: حداقل حدود ۱ رنج تا ۲ رنج (ریسک به ریوارد حدود ۱:۲ در سناریوی تهاجمی‌تر).",
    ]
    for i, s in enumerate(steps, 1):
        S.append(P(f"{i}. {s}", styles["bullet"]))

    S.append(Spacer(1, 0.2*cm))
    S.append(P("چرا فقط یک روز؟", styles["h2"]))
    S.append(P(
        "چون فرض استراتژی این است که فاصله‌گرفتن به اندازه یک رنج، ظرفیت حرکتی آن دوره را مصرف کرده است. "
        "بازگشتِ همان دوره بعد یعنی بازار برای ادامه «سوخت» ندارد و واکنش به سطح شکسته‌شده محتمل‌تر است. "
        "اگر چند روز بگذرد، رژیم نوسان عوض شده و فرض Blind Spot دیگر تمیز نیست.",
        styles["body"]
    ))

    S.append(P("نمونه مدیریت پوزیشن از ویدیو", styles["h2"]))
    S.append(P(
        "اگر کل رنج ۱۰۰ پیپ باشد و شما روی ۸۰ پیپ فاصله اردر بگذارید، ۲۰ پیپ استاپ منطقی دارید. "
        "برای تارگت می‌توانید ۱۰۰ پیپ (۱:۵ نسبت به استاپ ۲۰) یا سناریوی ۲×رنج را در نظر بگیرید؛ "
        "اما دیدگاه پایه می‌گوید حرکتِ خیلی بزرگ‌تر از توان متوسط «نادر» است، نه غیرممکن.",
        styles["body"]
    ))
    S.append(add_image(os.path.join(ASSETS, "v1_0430.jpg"), 15.5*cm))
    S.append(P("فریم ویدیو: چارت روزانه GBPUSD در فضای رفتارشناسی حرکت قیمت", styles["center"]))
    S.append(PageBreak())

    # 4. Live version
    S.append(P("۴) نسخه آپدیت‌شده: نقطه کور لایو (تایم پایین‌تر)", styles["h1"]))
    S.append(P(
        "در ویدیوی دوم تأکید می‌شود نقطه کور برای استفاده روزمره آپدیت شده: "
        "به‌جای اینکه ماهانه یک سیگنال Daily بگیرید، همان منطق را روی کندل زنده تایم جاری اجرا کنید.",
        styles["body"]
    ))
    S.append(add_image(os.path.join(ASSETS, "diagram_live.png"), 15.5*cm))
    S.append(P("نمای شماتیک نقطه کور لایو", styles["center"]))

    S.append(P("شرایط تریگر لایو", styles["h2"]))
    live_steps = [
        "کندل جاری هنوز Close نشده (لایو است).",
        "رنج لایو کندل (High−Low یا فاصله از Open) به اندازه TH/ATR/TR همان تایم پر شده باشد.",
        "هنوز زمان کافی تا Close کندل باقی مانده باشد (مثلاً در H4 اگر طی ۲ ساعت اول رنج پر شد و ۲ ساعت مانده).",
        "ناحیه نقطه کور = Open و Close کندل قبلی (گاهی واکنش به شدو/Hidden Level هم مطرح است).",
        "انتظار بازگشت قیمت به آن ناحیه و ادامه در جهت شکست/جریان غالب.",
        "می‌توانید در همان تایم اسکالپ کنید یا برای تریگر دقیق‌تر به تایم پایین‌تر بروید.",
    ]
    for i, s in enumerate(live_steps, 1):
        S.append(P(f"{i}. {s}", styles["bullet"]))

    S.append(P("قانون طلایی زمان", styles["h2"]))
    S.append(P(
        "«طول کندل‌ها و زمان باقی‌مانده برای کلوز بسیار بسیار اهمیت دارد.» "
        "اگر رنج زود پر شود ولی زمان کافی برای ریتریس و پُر شدن مجدد بدنه نماند، ستاپ ضعیف است. "
        "اغلب کندل‌ها در دقایق پایانی فول‌بادی می‌شوند؛ پس صبر تا لحظات پایانی معنا دارد، "
        "اما شرط اولیه این است که پرشدگی رنج زودتر از پایان تایم رخ داده باشد.",
        styles["body"]
    ))
    S.append(add_image(os.path.join(ASSETS, "v1_1100.jpg"), 15.5*cm))
    S.append(P("فریم ویدیو: اجرای مفهوم روی تایم H1 و داشبورد چندتایم رنج", styles["center"]))
    S.append(PageBreak())

    # 5. Relation to book concepts
    S.append(P("۵) پیوند با مفاهیم جزوه پرایس‌اکشن", styles["h1"]))
    S.append(P(
        "نقطه کور یک «ستاپ مستقل جادویی» نیست؛ روی اسکلت رفتارشناسی حرکت قیمت سوار است:",
        styles["body"]
    ))
    links = [
        "شکست سطح: در جزوه، عبور معنادار قیمت از سطح با معیار ATR/توان حرکتی مطرح است؛ کندل شکست بهتر است لانگ‌بار و فول‌بادی/شدوی مخالف باشد.",
        "مسترکندل: طول حدود ۸۰٪ تا ۱۲۰٪ ATR و بدنه یا شدوی غالب.",
        "تایم ساختار / پترن / تریگر: سطح را در تایم مادر ببینید، الگو را در تایم میانی، ورود را در تریگر.",
        "FTC و پیوت تبصره‌ای: در ویدیوی دوم، شکست پیوت و پولبک لایو با منطق نقطه کور ترکیب می‌شود.",
        "Hidden Level / شدو: گاهی نقطه واکنش، نوک شدو یا ناحیه مخفی مارکر قبلی است نه فقط خط OC.",
    ]
    for s in links:
        S.append(P("• " + s, styles["bullet"]))

    S.append(P("۶) الگوریتم اجرایی خلاصه (چک‌لیست ترید)", styles["h1"]))
    checklist = [
        "آیا سطح متعلق به تایم درست است؟",
        "آیا شکست کندلی معتبر است (نه صرفاً ویک نفوذی)؟",
        "آیا فاصله از سطح ≥ ۱× رنج انتخابی (TH/ATR/IDR) شده؟",
        "آیا داخل پنجره زمانی مجاز هستیم؟ (کلاسیک: کندل بعدی / لایو: قبل از کلوز با زمان باقی‌مانده کافی)",
        "آیا ناحیه ورود (OC / سطح شکسته‌شده / هیدن) واضح است؟",
        "آیا SL و TP از پیش مشخص‌اند و RR منطقی است؟",
        "اگر تاچ نشد → حذف اردر. بدون تعصب.",
    ]
    for s in checklist:
        S.append(P("☐ " + s, styles["bullet"]))

    S.append(PageBreak())
    S.append(P("۷) نمونه پارامترهای پیشنهادی اندیکاتور", styles["h1"]))
    params = [
        [fa("توضیح"), fa("پیشنهاد اولیه"), fa("پارامتر")],
        [fa("میانگین True Range"), "14", "ATR Period"],
        [fa("میانگین High-Low"), "20", "IDR Period"],
        [fa("توان حرکتی"), "0.6666%", "TH %"],
        [fa("منبع فاصله"), fa("Max(TH,ATR,IDR)"), "Range Source"],
        [fa("اعتبار کلاسیک"), "1 bar", "Valid Bars"],
        [fa("ورود"), "80% of range", "Entry Offset"],
        [fa("تارگت"), "2 × range", "TP Mult"],
        [fa("پرشدگی لایو"), "≥ 100%", "Live Fill"],
    ]
    t2 = Table(params, colWidths=[7.5*cm, 4.2*cm, 4.0*cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1E293B")),
        ("TEXTCOLOR", (0, 0), (-1, -1), C_TEXT),
        ("FONTNAME", (0, 0), (-1, -1), "Fa"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#334155")),
        ("BACKGROUND", (0, 1), (-1, -1), HexColor("#0F172A")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    S.append(t2)

    S.append(P("۸) فایل‌های اندیکاتور همراه این پکیج", styles["h1"]))
    S.append(P("• TradingView Pine Script v5: indicators/NoghteKoor_BlindSpot.pine", styles["bullet"]))
    S.append(P("• MetaTrader 4: indicators/NoghteKoor_BlindSpot.mq4", styles["bullet"]))
    S.append(P(
        "اندیکاتور داشبورد TH/ATR/IDR/LiveRange را نشان می‌دهد، ناحیه نقطه کور کلاسیک را بعد از شکست+فاصله علامت می‌زند، "
        "و برای نسخه لایو ناحیه Open/Close کندل قبلی را هایلایت می‌کند.",
        styles["body"]
    ))

    S.append(P("۹) هشدار مهم", styles["h1"]))
    S.append(P(
        "این سند آموزشی است و توصیه مالی نیست. نقطه کور یک دیدگاه احتمالاتی روی ظرفیت نوسان است، نه سیگنال قطعی. "
        "تشخیص سطح، شکست، و مدیریت سرمایه همچنان بخش اصلی کارند. همیشه روی حساب دمو و با ریسک کنترل‌شده تست کنید.",
        styles["body"]
    ))

    S.append(Spacer(1, 0.8*cm))
    S.append(HRFlowable(width="100%", color=C_ACCENT, thickness=1))
    S.append(P(
        "منابع استفاده‌شده: ویدیوهای YouTube نقطه کور، جزوه کامل پرایس‌اکشن سعید خاکستر، "
        "و فریم‌های چارت آموزشی داخل ویدیوها.",
        styles["note"]
    ))

    doc.build(S, onFirstPage=header_footer, onLaterPages=header_footer)
    print("PDF written:", OUT, "size", os.path.getsize(OUT))

if __name__ == "__main__":
    build()
