// Replaces the Next.js runtime: header state, menu panel, home hero (video → carousel),
// brand slider, number count-up and a mailto fallback for the contact form.
// Content is never hidden waiting for a scroll animation.

(function () {
  var rtl = document.documentElement.dir === 'rtl';
  var pad = function (n) { return (n < 10 ? '0' : '') + n; };

  // ---------- Header: solid after the hero, hides on scroll down, returns on scroll up
  var header = document.getElementById('rx-header');
  if (header) {
    var lastY = window.scrollY;
    var onScroll = function () {
      var y = window.scrollY;
      if (!header.dataset.solid) header.classList.toggle('rx-solid', y > 40);
      var menuOpen = document.body.classList.contains('rx-menu-open');
      header.classList.toggle('rx-hide', !menuOpen && y > 240 && y > lastY);
      lastY = y;
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  // ---------- Menu panel
  var menu = document.getElementById('rx-menu');
  var openBtn = document.getElementById('rx-menu-btn');
  var closeBtn = document.getElementById('rx-menu-close');
  if (menu && openBtn) {
    var here = location.pathname.replace(/\/(index\.html)?$/, '');
    menu.querySelectorAll('nav a').forEach(function (a) {
      if (a.getAttribute('href') === here) a.classList.add('active');
    });
    var setMenu = function (open) {
      menu.classList.toggle('open', open);
      document.body.classList.toggle('rx-menu-open', open);
      openBtn.setAttribute('aria-expanded', String(open));
      if (open) closeBtn.focus();
    };
    openBtn.addEventListener('click', function () { setMenu(true); });
    closeBtn.addEventListener('click', function () { setMenu(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setMenu(false); });
  }

  // ---------- Home hero: brand video, then an auto-rotating image carousel
  var hero = document.querySelector('.rx-hero');
  if (hero) {
    var video = document.getElementById('rx-hero-video');
    var slides = hero.querySelectorAll('.rx-slide');
    var bar = hero.querySelector('.rx-progress i');
    var cur = hero.querySelector('.rx-cur');
    var tot = hero.querySelector('.rx-tot');
    var sound = hero.querySelector('.rx-sound');
    var SLIDE_MS = 6000;
    var current = 0, timer = null, started = 0, raf = null;
    if (tot) tot.textContent = pad(slides.length);

    var tick = function () {
      var p = Math.min(1, (performance.now() - started) / SLIDE_MS);
      bar.style.transform = 'scaleX(' + p + ')';
      raf = requestAnimationFrame(tick);
    };
    var show = function (i) {
      slides[current].classList.remove('on');
      current = (i + slides.length) % slides.length;
      void slides[current].offsetWidth; // restart the slow zoom
      slides[current].classList.add('on');
      if (cur) cur.textContent = pad(current + 1);
      started = performance.now();
    };
    var restart = function () {
      clearInterval(timer);
      timer = setInterval(function () { show(current + 1); }, SLIDE_MS);
      started = performance.now();
    };
    var startCarousel = function () {
      if (hero.classList.contains('carousel')) return;
      hero.classList.add('carousel');
      if (video) video.pause();
      show(0); restart();
      cancelAnimationFrame(raf); tick();
    };
    hero.querySelectorAll('.rx-arrow').forEach(function (b) {
      b.addEventListener('click', function () {
        var d = Number(b.dataset.dir) * (rtl ? -1 : 1);
        show(current + d); restart();
      });
    });

    if (video) {
      // While the film plays, the bar tracks its progress.
      video.addEventListener('timeupdate', function () {
        if (!hero.classList.contains('carousel') && video.duration) {
          bar.style.transform = 'scaleX(' + video.currentTime / video.duration + ')';
        }
      });
      video.addEventListener('ended', startCarousel);
      video.addEventListener('error', startCarousel);
      var p = video.play();
      if (p && p.catch) p.catch(startCarousel);
      if (sound) sound.addEventListener('click', function () {
        video.muted = !video.muted;
        sound.style.opacity = video.muted ? '' : '.6';
      });
    } else {
      startCarousel();
    }
  }

  // ---------- Numbers count up once when they first come into view (final value is in the HTML)
  var nums = document.querySelectorAll('.rx-num[data-to]');
  if (nums.length && 'IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        io.unobserve(en.target);
        var el = en.target, to = Number(el.dataset.to), t0 = performance.now(), D = 1400;
        var step = function (now) {
          var k = Math.min(1, (now - t0) / D);
          el.textContent = Math.round(to * (1 - Math.pow(1 - k, 3)));
          if (k < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      });
    }, { threshold: 0.6 });
    nums.forEach(function (n) { io.observe(n); });
  }

  // ---------- Brand slider: filter tabs, arrows, counter, drag to scroll
  document.querySelectorAll('.rx-portfolio').forEach(function (sec) {
    var track = sec.querySelector('.rx-track');
    var cards = Array.prototype.slice.call(track.querySelectorAll('.rx-bcard'));
    var cur = sec.querySelector('.rx-cur'), tot = sec.querySelector('.rx-tot');
    var arrows = sec.querySelectorAll('.rx-slider-nav .rx-arrow');
    var visible = function () { return cards.filter(function (c) { return !c.hidden; }); };
    var step = function () { var v = visible(); return v.length > 1 ? v[1].offsetLeft - v[0].offsetLeft : track.clientWidth; };
    var update = function () {
      var v = visible();
      var x = Math.abs(track.scrollLeft);
      var idx = Math.min(v.length - 1, Math.round(x / step()));
      var max = track.scrollWidth - track.clientWidth;
      if (cur) cur.textContent = pad(idx + 1);
      if (tot) tot.textContent = pad(v.length);
      if (arrows.length) {
        arrows[0].disabled = x <= 2;
        arrows[1].disabled = x >= max - 2;
      }
    };
    arrows.forEach(function (b) {
      b.addEventListener('click', function () {
        track.scrollBy({ left: Number(b.dataset.dir) * step() * (rtl ? -1 : 1) });
      });
    });
    track.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);

    sec.querySelectorAll('.rx-tab').forEach(function (tab) {
      tab.addEventListener('click', function () {
        sec.querySelectorAll('.rx-tab').forEach(function (t) { t.classList.toggle('on', t === tab); });
        var f = tab.dataset.filter;
        cards.forEach(function (c) { c.hidden = f !== 'all' && c.dataset.group !== f; });
        track.scrollTo({ left: 0 });
        update();
      });
    });

    // Mouse drag (touch devices already scroll natively)
    var down = false, sx = 0, sl = 0, moved = false;
    track.addEventListener('mousedown', function (e) { down = true; moved = false; sx = e.pageX; sl = track.scrollLeft; });
    window.addEventListener('mouseup', function () { down = false; track.classList.remove('dragging'); });
    track.addEventListener('mousemove', function (e) {
      if (!down) return;
      var dx = e.pageX - sx;
      if (Math.abs(dx) > 4) { moved = true; track.classList.add('dragging'); }
      track.scrollLeft = sl - dx;
    });
    track.addEventListener('click', function (e) { if (moved) { e.preventDefault(); moved = false; } }, true);
    track.addEventListener('dragstart', function (e) { e.preventDefault(); });
    update();
  });

  // ---------- Contact form: the original posted to the CMS API, which a static copy does not have
  var form = document.querySelector('main form');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var lines = [];
      form.querySelectorAll('input, select, textarea').forEach(function (f) {
        if (f.name && f.value) lines.push(f.name + ': ' + f.value);
      });
      location.href = 'mailto:info@rmalhospitality.ae?subject=' +
        encodeURIComponent('Website enquiry') + '&body=' + encodeURIComponent(lines.join('\n'));
    });
  }
})();
