/**
 * Pishro Joosh — product rail carousels
 * 15 items / rail, 5 visible, auto-rotate (RTL)
 *
 * Edit PJ_SPECIAL_PRODUCTS / PJ_SUGGESTED_PRODUCTS below.
 * When Bagisto products exist, you can also set:
 *   window.PJ_PRODUCTS_API = "/api/products?limit=15"
 */
(function () {
  "use strict";

  var IMG = "https://raw.githubusercontent.com/vitoali/farhad/cursor/pishro-slanted-header-7149/header/products/img/";

  /* ---------- Sample catalog (replace urls/images with real products) ---------- */
  window.PJ_SPECIAL_PRODUCTS = window.PJ_SPECIAL_PRODUCTS || [
    { name: "BÖHLER FOX EV 50", brand: "voestalpine Böhler Welding", url: "https://pishrojoosh.com/page/Voestalpine-Bohler-Welding", image: IMG + "bohler-fox-ev-50.png" },
    { name: "ESAB OK 46.00", brand: "ESAB", url: "https://pishrojoosh.com/page/ESAB", image: IMG + "esab-ok-46.png" },
    { name: "Excalibur 7018", brand: "Lincoln Electric", url: "https://pishrojoosh.com/page/Lincoln-Electric", image: IMG + "lincoln-excalibur.png" },
    { name: "UTP 68", brand: "UTP Maintenance", url: "https://pishrojoosh.com/page/UTP-Maintenance", image: IMG + "utp-68.png" },
    { name: "BÖHLER FOX OHV", brand: "voestalpine Böhler Welding", url: "https://pishrojoosh.com/page/Voestalpine-Bohler-Welding", image: IMG + "bohler-fox-ohv.png" },
    { name: "ESAB OK 48.00", brand: "ESAB", url: "https://pishrojoosh.com/page/ESAB", image: IMG + "esab-ok-48.png" },
    { name: "Fleetweld 5P+", brand: "Lincoln Electric", url: "https://pishrojoosh.com/page/Lincoln-Electric", image: IMG + "lincoln-fleetweld.png" },
    { name: "Hardface CN", brand: "Welding Alloys", url: "https://pishrojoosh.com/page/Welding-Alloys", image: IMG + "wa-hardface.png" },
    { name: "LB-52U", brand: "Kobelco", url: "https://pishrojoosh.com/", image: IMG + "kobelco-lb52.png" },
    { name: "BÖHLER FOX EV 60", brand: "voestalpine Böhler Welding", url: "https://pishrojoosh.com/page/Voestalpine-Bohler-Welding", image: IMG + "bohler-fox-ev-60.png" },
    { name: "ESAB OK 53.70", brand: "ESAB", url: "https://pishrojoosh.com/page/ESAB", image: IMG + "esab-ok-53.png" },
    { name: "14A Red Powder", brand: "Magnaflux", url: "https://pishrojoosh.com/page/Magnaflux", image: IMG + "magnaflux-14a.png" },
    { name: "MagicWave 230i", brand: "Fronius", url: "https://pishrojoosh.com/", image: IMG + "fronius-magicwave.png" },
    { name: "PMET 2209", brand: "Polymet", url: "https://pishrojoosh.com/", image: IMG + "polymet-2209.png" },
    { name: "Haynes 556 Wire", brand: "Haynes", url: "https://pishrojoosh.com/", image: IMG + "haynes-556.png" }
  ];

  window.PJ_SUGGESTED_PRODUCTS = window.PJ_SUGGESTED_PRODUCTS || [
    { name: "ESAB OK 46.00", brand: "ESAB", url: "https://pishrojoosh.com/page/ESAB", image: IMG + "esab-ok-46.png" },
    { name: "BÖHLER FOX EV 50", brand: "voestalpine Böhler Welding", url: "https://pishrojoosh.com/page/Voestalpine-Bohler-Welding", image: IMG + "bohler-fox-ev-50.png" },
    { name: "LB-52U", brand: "Kobelco", url: "https://pishrojoosh.com/", image: IMG + "kobelco-lb52.png" },
    { name: "Excalibur 7018", brand: "Lincoln Electric", url: "https://pishrojoosh.com/page/Lincoln-Electric", image: IMG + "lincoln-excalibur.png" },
    { name: "Hardface CN", brand: "Welding Alloys", url: "https://pishrojoosh.com/page/Welding-Alloys", image: IMG + "wa-hardface.png" },
    { name: "UTP 68", brand: "UTP Maintenance", url: "https://pishrojoosh.com/page/UTP-Maintenance", image: IMG + "utp-68.png" },
    { name: "ESAB OK 48.00", brand: "ESAB", url: "https://pishrojoosh.com/page/ESAB", image: IMG + "esab-ok-48.png" },
    { name: "BÖHLER FOX OHV", brand: "voestalpine Böhler Welding", url: "https://pishrojoosh.com/page/Voestalpine-Bohler-Welding", image: IMG + "bohler-fox-ohv.png" },
    { name: "14A Red Powder", brand: "Magnaflux", url: "https://pishrojoosh.com/page/Magnaflux", image: IMG + "magnaflux-14a.png" },
    { name: "Fleetweld 5P+", brand: "Lincoln Electric", url: "https://pishrojoosh.com/page/Lincoln-Electric", image: IMG + "lincoln-fleetweld.png" },
    { name: "MagicWave 230i", brand: "Fronius", url: "https://pishrojoosh.com/", image: IMG + "fronius-magicwave.png" },
    { name: "BÖHLER FOX EV 60", brand: "voestalpine Böhler Welding", url: "https://pishrojoosh.com/page/Voestalpine-Bohler-Welding", image: IMG + "bohler-fox-ev-60.png" },
    { name: "PMET 2209", brand: "Polymet", url: "https://pishrojoosh.com/", image: IMG + "polymet-2209.png" },
    { name: "ESAB OK 53.70", brand: "ESAB", url: "https://pishrojoosh.com/page/ESAB", image: IMG + "esab-ok-53.png" },
    { name: "Haynes 556 Wire", brand: "Haynes", url: "https://pishrojoosh.com/", image: IMG + "haynes-556.png" }
  ];

  function visibleCount(rail) {
    var w = rail.clientWidth || window.innerWidth;
    if (w <= 560) return 2;
    if (w <= 860) return 3;
    if (w <= 1100) return 4;
    return 5;
  }

  function cardHTML(item) {
    var name = escapeHtml(item.name || "");
    var brand = escapeHtml(item.brand || "");
    var url = item.url || "#";
    var image = item.image || "";
    return (
      '<a class="pj-prod-card" href="' + escapeAttr(url) + '" title="' + name + '">' +
        '<div class="pj-prod-card__body">' +
          '<div class="pj-prod-card__media">' +
            '<img src="' + escapeAttr(image) + '" alt="' + name + '" loading="lazy" width="148" height="148" />' +
          "</div>" +
          '<h3 class="pj-prod-card__name">' + name + "</h3>" +
          '<p class="pj-prod-card__brand">' + brand + "</p>" +
        "</div>" +
      "</a>"
    );
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, "&#39;");
  }

  function initRail(root, items) {
    if (!root || !items || !items.length) return;

    var track = root.querySelector(".pj-prod-rail__track");
    var viewport = root.querySelector(".pj-prod-rail__viewport");
    var prevBtn = root.querySelector('[data-dir="prev"]');
    var nextBtn = root.querySelector('[data-dir="next"]');
    var dotsWrap = root.querySelector(".pj-prod-rail__dots");
    if (!track || !viewport) return;

    // Keep up to 15
    items = items.slice(0, 15);
    track.innerHTML = items.map(cardHTML).join("");

    var index = 0;
    var timer = null;
    var gap = 22;

    function maxIndex() {
      return Math.max(0, items.length - visibleCount(viewport));
    }

    function readGap() {
      var styles = window.getComputedStyle(track);
      gap = parseFloat(styles.columnGap || styles.gap) || 22;
    }

    function layoutCards() {
      var n = visibleCount(viewport);
      root.style.setProperty("--pj-prod-visible", String(n));
      readGap();
      var vw = viewport.clientWidth;
      var w = (vw - gap * (n - 1)) / n;
      track.querySelectorAll(".pj-prod-card").forEach(function (card) {
        card.style.flex = "0 0 " + w + "px";
        card.style.width = w + "px";
        card.style.maxWidth = w + "px";
      });
      return w;
    }

    function goTo(i, animate) {
      var max = maxIndex();
      index = ((i % (max + 1)) + (max + 1)) % (max + 1);
      var w = layoutCards();
      var step = w + gap;
      // RTL: positive translateX moves content to the right (reveals leftward / next in RTL visual)
      var x = index * step;
      if (animate === false) track.style.transition = "none";
      track.style.transform = "translate3d(" + x + "px,0,0)";
      if (animate === false) {
        void track.offsetHeight;
        track.style.transition = "";
      }
      renderDots();
    }

    function renderDots() {
      if (!dotsWrap) return;
      var pages = maxIndex() + 1;
      if (pages <= 1) {
        dotsWrap.innerHTML = "";
        return;
      }
      var html = "";
      for (var i = 0; i < pages; i++) {
        html +=
          '<button type="button" class="pj-prod-rail__dot' +
          (i === index ? " is-active" : "") +
          '" data-i="' +
          i +
          '" aria-label="اسلاید ' +
          (i + 1) +
          '"></button>';
      }
      dotsWrap.innerHTML = html;
    }

    function next() {
      goTo(index + 1);
    }
    function prev() {
      goTo(index - 1);
    }

    function start() {
      stop();
      timer = setInterval(next, 4200);
    }
    function stop() {
      if (timer) clearInterval(timer);
      timer = null;
    }

    if (prevBtn) prevBtn.addEventListener("click", function () { prev(); start(); });
    if (nextBtn) nextBtn.addEventListener("click", function () { next(); start(); });
    if (dotsWrap) {
      dotsWrap.addEventListener("click", function (e) {
        var btn = e.target.closest(".pj-prod-rail__dot");
        if (!btn) return;
        goTo(parseInt(btn.getAttribute("data-i"), 10) || 0);
        start();
      });
    }

    root.addEventListener("mouseenter", stop);
    root.addEventListener("mouseleave", start);
    root.addEventListener("focusin", stop);
    root.addEventListener("focusout", start);

    // Touch swipe
    var startX = 0;
    viewport.addEventListener(
      "touchstart",
      function (e) {
        startX = e.changedTouches[0].clientX;
        stop();
      },
      { passive: true }
    );
    viewport.addEventListener(
      "touchend",
      function (e) {
        var dx = e.changedTouches[0].clientX - startX;
        if (Math.abs(dx) > 40) {
          // RTL: swipe left (dx<0) => prev visually / next index
          if (dx < 0) next();
          else prev();
        }
        start();
      },
      { passive: true }
    );

    window.addEventListener("resize", function () {
      goTo(Math.min(index, maxIndex()), false);
    });

    goTo(0, false);
    start();
  }

  function mount() {
    var special = document.getElementById("pjSpecialProducts");
    var suggested = document.getElementById("pjSuggestedProducts");
    initRail(special, window.PJ_SPECIAL_PRODUCTS);
    initRail(suggested, window.PJ_SUGGESTED_PRODUCTS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
