/*
 * Scroll-triggered animation for the marketing pages: fade+rise on entry
 * (.reveal / .reveal-stagger, see shared/css/base.css) and a count-up
 * animation for stat numbers (data-count-to="12"). Runs immediately since
 * this script tag sits at the end of <body>, after the elements it
 * targets already exist. No library — plain IntersectionObserver.
 */

// ------------------------------------------
// FADE + RISE ON SCROLL — every .reveal element gets .visible once shown
// ------------------------------------------
const revealTargets = document.querySelectorAll(".reveal");
if (!("IntersectionObserver" in window)) {
  revealTargets.forEach((el) => el.classList.add("visible"));
} else {
  const revealObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });
  revealTargets.forEach((el) => revealObserver.observe(el));
}

// ------------------------------------------
// COUNT-UP STAT NUMBERS — data-count-to="21+" counts up to 21 then appends "+"
// ------------------------------------------
function animateCount(el) {
  const target = el.dataset.countTo;
  const match = target.match(/[\d.]+/);
  if (!match) { el.textContent = target; return; }
  const numTarget = parseFloat(match[0]);
  const prefix = target.slice(0, match.index);
  const suffix = target.slice(match.index + match[0].length);
  const duration = 900;
  const start = performance.now();

  function tick(now) {
    const progress = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = prefix + Math.round(numTarget * eased) + suffix;
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

const counters = document.querySelectorAll("[data-count-to]");
if ("IntersectionObserver" in window) {
  const countObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        animateCount(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.6 });
  counters.forEach((el) => countObserver.observe(el));
} else {
  counters.forEach((el) => { el.textContent = el.dataset.countTo; });
}
