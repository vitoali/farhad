# هدر مورب پیشرو جوش (استایل Ozmetalsan)

بازطراحی هدر [pishrojoosh.com](https://pishrojoosh.com/) با الگوی نوار مورب [ozmetalsan.com](https://www.ozmetalsan.com/).

## نتیجه طراحی

| ناحیه | رنگ / رفتار |
|--------|-------------|
| بک‌گراند کل صفحه | `#F6F6F6` مثل ozmetalsan |
| هیرو زیر هدر | تیره صنعتی |
| هدر | تیره مدادی طرح‌دار + لوگو در بیضی سفید |
| دراپ‌داون محصولات | سربی `#C5C6C8` |
| دراپ‌داون برندها | رنگ‌های واقعی سایت |
| فوتر | `#161616` |
| جستجو | آیکن دایره‌ای؛ با کلیک نوار نارنجی با slide باز می‌شود |

## فایل‌ها

- `header/complete.html` — یک فایل کامل آماده اجرا
- `header/index.html` — دمو
- `header/header.css` — استایل هدر
- `header/page.css` — بک‌گراند صفحه / هیرو / دسته‌ها / فوتر
- `header/bagisto-snippet.blade.php` — اسنیپت Bagisto

## نصب روی Bagisto

```css
html, body { background: #f6f6f6 !important; }
```

و فایل‌های `header.css` + `page.css` را لود کنید.
