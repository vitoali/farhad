# هدر مورب پیشرو جوش (استایل Ozmetalsan)

بازطراحی هدر [pishrojoosh.com](https://pishrojoosh.com/) با الگوی نوار مورب [ozmetalsan.com](https://www.ozmetalsan.com/).

## نتیجه طراحی

| ناحیه | رنگ / رفتار |
|--------|-------------|
| از ابتدای صفحه (راست در RTL) تا پایان لوگو | **سفید یکدست** `#FFFFFF` با برش مورب `skewX` (هم‌رنگ بک‌گراند لوگو) |
| بقیه نوار منو | تیره `#1D1D1D` مثل ozmetalsan |
| لینک‌های منو | سفید؛ هاور نارنجی برند `#FD7402` |
| جستجو | آیکن دایره‌ای؛ با کلیک نوار نارنجی پایین هدر با `slideToggle` باز می‌شود (مثل ozmetalsan) |

## فایل‌ها

- `header/index.html` — دمو زنده برای پیش‌نمایش
- `header/header.css` — استایل کامل RTL
- `header/bagisto-snippet.blade.php` — اسنیپت جایگزینی در قالب Bagisto
- `assets/logo.png` — لوگوی فعلی سایت
- `assets/pishro-header-mockup.png` — ماکاپ بصری

## نصب سریع روی سایت

1. `header.css` را به عنوان مثلاً `public/css/pj-header.css` کپی کنید.
2. محتوای هدر فعلی (بلوک `v-desktop-header` / Blade هدر) را با `bagisto-snippet.blade.php` عوض کنید.
3. مسیر لوگو را با فایل واقعی storage تنظیم کنید.
4. در صورت نیاز رنگ سفید سربی را از متغیر `--pj-lead-white` تغییر دهید.

## پیش‌نمایش محلی

فایل `header/index.html` را در مرورگر باز کنید.
