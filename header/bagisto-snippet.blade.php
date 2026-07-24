<!--
  Snippet برای جایگزینی هدر فعلی Bagisto / Blade
  ۱) header.css را در layout لود کنید
  ۲) این مارک‌آپ را جایگزین v-desktop-header / بلوک header کنید
  ۳) مسیر لوگو را با storage واقعی سایت تنظیم کنید
-->

<link rel="stylesheet" href="{{ asset('css/pj-header.css') }}">

<header class="pj-header" id="pjHeader">
  <div class="pj-header__inner">
    <div class="pj-header__logo">
      <a href="{{ url('/') }}" aria-label="پیشرو جوش خاورمیانه">
        <img
          src="{{ core()->getConfigData('general.design.admin_logo.logo_image') ? Storage::url(core()->getConfigData('general.design.admin_logo.logo_image')) : asset('images/logo.png') }}"
          width="192"
          height="50"
          alt="{{ config('app.name') }}"
        />
      </a>
    </div>

    <nav class="pj-header__nav" aria-label="منوی اصلی">
      <ul class="pj-header__menu">
        <li class="has-dropdown">
          <a href="#product-carousel">محصولات</a>
          <ul class="pj-header__dropdown">
            <li><a href="{{ url('/page/welding-consumables') }}">مواد مصرفی جوشکاری</a></li>
            <li><a href="{{ url('/page/ndt-materials-equipment') }}">مواد و تجهیزات تست‌های غیرمخرب</a></li>
            <li><a href="{{ url('/page/welding-robots') }}">ربات‌های جوشکاری</a></li>
            <li><a href="{{ url('/page/welding-cutting-machines') }}">دستگاه‌های جوش و برش</a></li>
            <li><a href="{{ url('/page/radiographic-films') }}">فیلم‌های رادیوگرافی</a></li>
          </ul>
        </li>
        <li class="has-dropdown">
          <a href="#services-section">خدمات مهندسی</a>
          <ul class="pj-header__dropdown">
            <li><a href="#services-section">جوشکاری کلدینگ</a></li>
            <li><a href="#services-section">مشاوره فنی</a></li>
          </ul>
        </li>
        <li><a href="#price-inquiry-section">استعلام قیمت</a></li>
        <li class="has-dropdown">
          <a href="#">برندها</a>
          <ul class="pj-header__dropdown">
            <li><a href="#">Voestalpine Bohler Welding</a></li>
            <li><a href="#">Lincoln Electric</a></li>
            <li><a href="#">ESAB</a></li>
            <li><a href="#">Fronius</a></li>
            <li><a href="#">Welding Alloys</a></li>
          </ul>
        </li>
        <li><a href="#about-us-section">درباره ما</a></li>
        <li><a href="{{ url('/contact-us') }}">تماس با ما</a></li>
      </ul>
    </nav>

    <div class="pj-header__actions">
      <a class="pj-header__consult" href="tel:+9821">
        <span class="pj-header__consult-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M6.6 10.8c1.4 2.8 3.8 5.1 6.6 6.6l2.2-2.2c.3-.3.7-.4 1.1-.2 1.2.4 2.5.6 3.8.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C10.6 21 3 13.4 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.6.6 3.8.1.4 0 .8-.3 1.1L6.6 10.8z"/></svg>
        </span>
        <span>مشاوره</span>
      </a>

      <button type="button" class="pj-header__search-btn" id="pjSearchToggle" aria-label="جستجو" aria-expanded="false" aria-controls="pjSearchPanel">
        <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
      </button>

      <button type="button" class="pj-header__burger" id="pjBurger" aria-label="منو">
        <svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
      </button>
    </div>
  </div>

  <div class="pj-header__search-panel" id="pjSearchPanel" hidden>
    <div class="pj-header__search-panel-inner">
      <form class="pj-header__search-form" action="{{ url('/search') }}" method="get">
        <input type="search" name="query" placeholder="جستجوی محصولات..." required />
        <button type="submit" aria-label="جستجو">
          <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
        </button>
      </form>
    </div>
  </div>
</header>

<script>
  (function () {
    var header = document.getElementById("pjHeader");
    var burger = document.getElementById("pjBurger");
    var searchToggle = document.getElementById("pjSearchToggle");
    var searchPanel = document.getElementById("pjSearchPanel");

    if (burger) {
      burger.addEventListener("click", function () {
        burger.setAttribute("aria-expanded", header.classList.toggle("is-nav-open"));
      });
    }

    function slideToggle(el, open) {
      if (open) {
        el.hidden = false;
        el.style.display = "block";
        el.style.overflow = "hidden";
        el.style.height = "0px";
        el.style.paddingTop = "0px";
        el.style.paddingBottom = "0px";
        void el.offsetHeight;
        el.style.transition = "height 0.35s ease, padding 0.35s ease";
        el.style.height = el.scrollHeight + "px";
        el.style.paddingTop = "";
        el.style.paddingBottom = "";
        el.classList.add("is-open");
        setTimeout(function () {
          el.style.height = "";
          el.style.overflow = "";
          el.style.transition = "";
        }, 360);
      } else {
        el.style.overflow = "hidden";
        el.style.height = el.scrollHeight + "px";
        void el.offsetHeight;
        el.style.transition = "height 0.3s ease, padding 0.3s ease";
        el.style.height = "0px";
        el.style.paddingTop = "0px";
        el.style.paddingBottom = "0px";
        el.classList.remove("is-open");
        setTimeout(function () {
          el.hidden = true;
          el.style.display = "none";
          el.style.height = "";
          el.style.paddingTop = "";
          el.style.paddingBottom = "";
          el.style.overflow = "";
          el.style.transition = "";
        }, 310);
      }
    }

    if (searchToggle && searchPanel) {
      searchToggle.addEventListener("click", function (e) {
        e.preventDefault();
        var willOpen = !searchPanel.classList.contains("is-open");
        slideToggle(searchPanel, willOpen);
        searchToggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
        if (willOpen) {
          var input = searchPanel.querySelector("input");
          if (input) setTimeout(function () { input.focus(); }, 320);
        }
      });
    }
  })();
</script>
