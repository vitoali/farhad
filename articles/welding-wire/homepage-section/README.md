# سکشن مقالات صفحه اول پیشرو جوش

جایگذاری: **آخر صفحه اول، دقیقاً قبل از `#brands-section`**

الهام طراحی:
- [Böhler Welding – Latest News](https://www.voestalpine.com/welding/)
- [Lincoln Electric Newsroom](https://www.lincolnelectric.com/en/newsroom)

## فایل‌ها
| فایل | کاربرد |
|---|---|
| `FOR-BAGISTO-PASTE.html` | کپی داخل Custom HTML صفحه اصلی |
| `pj-articles-section.READY.html` | نسخه لوکال با عکس‌های همین پوشه |
| `preview/index.html` | پیش‌نمایش کامل |
| `assets/*.jpg` | سه کاور کارت مقالات |

## نصب روی pishrojoosh.com

1. سه تصویر `assets/` را در پنل آپلود کنید (مثلاً مسیر پیشنهادی):
   - `/storage/theme/articles/article-card-wire-types.jpg`
   - `/storage/theme/articles/article-card-co2-mig.jpg`
   - `/storage/theme/articles/article-card-brands.jpg`
2. محتوای `FOR-BAGISTO-PASTE.html` را در بلوک HTML سفارشی صفحه اول بچسبانید؛ **قبل از سکشن برندها**.
3. لینک هر کارت (`href`) را به آدرس واقعی مقاله در سایت عوض کنید.
4. اگر صفحه آرشیو مقالات دارید، لینک «همه مقالات» را هم آپدیت کنید.

## رفتار UI
- ۳ کارت؛ اولی عریض‌تر (featured)
- تصویر فول‌bleed + گرادیان تیره
- تگ قرمز برند `#c8102e`
- هاور با زوم ملایم تصویر

## محتوای پیشنهادی ۳ کارت
1. راهنمای کامل انواع سیم جوش
2. سیم جوش CO2؛ قطر، گاز و تنظیمات
3. Böhler و Lincoln در برابر بازار ایران
