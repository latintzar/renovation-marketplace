/**
 * Shared landing hero bootstrap — homeowners + professionals.
 * Runs before fluid-gradient-v4.js (defer order): reduced-motion skips WebGL; same ambient markup class hooks.
 */
(function () {
  'use strict';

  function applyReducedMotion() {
    try {
      var mq = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
      if (!mq || !mq.matches) return;
      document.documentElement.classList.add('leo-hero--reduced-motion');
      document.querySelectorAll('.hero-box.hero-fluid-live').forEach(function (box) {
        var c = box.querySelector('canvas.el-gradient__canvas');
        if (c) c.setAttribute('data-leo-fluid-skip', '1');
      });
    } catch (e) {
      console.warn('[leo-landing-hero] reduced-motion check failed', e);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyReducedMotion);
  } else {
    applyReducedMotion();
  }
})();
