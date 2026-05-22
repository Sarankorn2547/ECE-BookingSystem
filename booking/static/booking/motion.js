/* =========================================
   ECE MOTION SYSTEM — JavaScript
   Scroll Reveal + Auto-tag elements
   ========================================= */

document.addEventListener('DOMContentLoaded', function () {

  // --- Auto-tag elements with reveal classes ---
  const revealMap = [
    // Dashboard
    { sel: '.home-action-card', cls: 'reveal', stagger: true },
    { sel: '.home-recent-card', cls: 'reveal' },
    // Booking form
    { sel: '.ece-card', cls: 'reveal', stagger: true },
    { sel: '.room-select-card', cls: 'reveal-scale', stagger: true },
    // Calendar
    { sel: '.cal-controls', cls: 'reveal' },
    { sel: '.cal-room-filter', cls: 'reveal' },
    { sel: '.cal-legend', cls: 'reveal' },
    { sel: '#calendar', cls: 'reveal' },
    // My Bookings
    { sel: '.ece-tab-bar', cls: 'reveal' },
    { sel: '.ece-booking-card', cls: 'reveal', stagger: true },
    // Admin
    { sel: '.ece-detail-box', cls: 'reveal', stagger: true },
    // Tables
    { sel: '.table-responsive', cls: 'reveal' },
  ];

  revealMap.forEach(function (item) {
    var els = document.querySelectorAll(item.sel);
    els.forEach(function (el, i) {
      if (!el.classList.contains('reveal') &&
          !el.classList.contains('reveal-left') &&
          !el.classList.contains('reveal-right') &&
          !el.classList.contains('reveal-scale')) {
        el.classList.add(item.cls);
      }
      if (item.stagger && i > 0) {
        var delay = Math.min(i, 4);
        el.classList.add('reveal-delay-' + delay);
      }
    });
  });

  // --- Intersection Observer for scroll reveal ---
  var revealEls = document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale');

  if ('IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -40px 0px'
    });

    revealEls.forEach(function (el) {
      observer.observe(el);
    });
  } else {
    // Fallback: show everything
    revealEls.forEach(function (el) {
      el.classList.add('visible');
    });
  }

  // --- Parallax-lite on hero/page-header backgrounds ---
  var heroBg = document.querySelector('.home-hero-bg, .page-header-bg, .login-bg-image');
  if (heroBg) {
    var ticking = false;
    window.addEventListener('scroll', function () {
      if (!ticking) {
        window.requestAnimationFrame(function () {
          var scrollY = window.pageYOffset;
          heroBg.style.transform = 'translateY(' + (scrollY * 0.3) + 'px)';
          ticking = false;
        });
        ticking = true;
      }
    });
  }

  // --- Ripple effect on buttons ---
  var btns = document.querySelectorAll('.ece-btn-primary, .login-btn, .cal-room-pill, .cal-view-btn');
  btns.forEach(function (btn) {
    btn.style.position = 'relative';
    btn.style.overflow = 'hidden';
    btn.addEventListener('click', function (e) {
      var rect = btn.getBoundingClientRect();
      var ripple = document.createElement('span');
      var size = Math.max(rect.width, rect.height);
      ripple.style.cssText =
        'position:absolute;border-radius:50%;background:rgba(255,255,255,0.35);' +
        'width:' + size + 'px;height:' + size + 'px;' +
        'left:' + (e.clientX - rect.left - size / 2) + 'px;' +
        'top:' + (e.clientY - rect.top - size / 2) + 'px;' +
        'transform:scale(0);animation:rippleAnim 0.6s ease-out;pointer-events:none;';
      btn.appendChild(ripple);
      setTimeout(function () { ripple.remove(); }, 600);
    });
  });

  // Add ripple keyframes dynamically
  if (!document.getElementById('ripple-style')) {
    var style = document.createElement('style');
    style.id = 'ripple-style';
    style.textContent = '@keyframes rippleAnim{to{transform:scale(2.5);opacity:0;}}';
    document.head.appendChild(style);
  }

  // --- Counter animation for stats ---
  var counters = document.querySelectorAll('[data-count]');
  counters.forEach(function (el) {
    var target = parseInt(el.getAttribute('data-count'), 10);
    var duration = 1200;
    var start = 0;
    var startTime = null;

    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(eased * target);
      if (progress < 1) requestAnimationFrame(step);
    }

    var countObs = new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) {
        requestAnimationFrame(step);
        countObs.unobserve(el);
      }
    }, { threshold: 0.5 });
    countObs.observe(el);
  });
});
