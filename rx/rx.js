// Replaces the Next.js runtime: header state, menu panel, home hero (video → carousel),
// and a mailto fallback for the contact form. No scroll-triggered animations.

(function () {
  var header = document.getElementById('rx-header');
  if (header && !header.dataset.solid) {
    var onScroll = function () { header.classList.toggle('rx-solid', window.scrollY > 40); };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  var menu = document.getElementById('rx-menu');
  var openBtn = document.getElementById('rx-menu-btn');
  var closeBtn = document.getElementById('rx-menu-close');
  if (menu && openBtn) {
    var here = location.pathname.replace(/\/$/, '');
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

  var hero = document.querySelector('.rx-hero');
  if (hero) {
    var video = document.getElementById('rx-hero-video');
    var slides = hero.querySelectorAll('.rx-slide');
    var dotsWrap = hero.querySelector('.rx-dots');
    var sound = hero.querySelector('.rx-sound');
    var current = 0, timer = null;
    slides.forEach(function (_, i) {
      var b = document.createElement('button');
      b.setAttribute('aria-label', 'Image ' + (i + 1));
      b.addEventListener('click', function () { show(i); restart(); });
      dotsWrap.appendChild(b);
    });
    var dots = dotsWrap.querySelectorAll('button');
    var show = function (i) {
      slides[current].classList.remove('on'); dots[current].classList.remove('on');
      current = i;
      slides[current].classList.add('on'); dots[current].classList.add('on');
    };
    var restart = function () {
      clearInterval(timer);
      timer = setInterval(function () { show((current + 1) % slides.length); }, 5000);
    };
    var startCarousel = function () {
      if (hero.classList.contains('carousel')) return;
      hero.classList.add('carousel');
      show(0); restart();
      if (video) video.pause();
    };
    if (video) {
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

  // The original form posted to the CMS API, which a static copy does not have.
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
