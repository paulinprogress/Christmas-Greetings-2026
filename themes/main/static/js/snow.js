/*
 * ASCII snow ✧
 * A smooth, parallax snowfall made of text symbols, drawn on a fullscreen canvas
 * behind your page. No dependencies.
 */
(() => {
  'use strict';

  // ---------------------------------------------------------------- settings
  const CONFIG = {
    // Symbols that make up the snowflakes. Repeat one to make it more common.
    glyphs: ['+', '*', '⋆', '⁺', '₊', '.', "'", '`', '✢', '✩', '✧', '✲', '✻', '·', '*', '⋆', '.'],
    font: "'DejaVu Sans Mono', 'Segoe UI Symbol', 'Apple Symbols', 'Noto Sans Symbols2', monospace",
    color: '180, 180, 255',   // RGB of the snow.
    size: [9, 12],            // px: farthest flake -> nearest flake
    speed: [16, 75],          // px/second: farthest -> nearest
    density: 1 / 15000,       // flakes per px² of screen
    minFlakes: 25,
    maxFlakes: 170,
    zIndex: -1,               // -1 = behind page content. If you can't see the snow, set to 0.
  };

  // Respect people who turned off animations in their OS
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  // ------------------------------------------------------------------ canvas
  const canvas = document.createElement('canvas');
  canvas.setAttribute('aria-hidden', 'true');
  Object.assign(canvas.style, {
    position: 'fixed',
    top: '0',
    left: '0',
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
    zIndex: String(CONFIG.zIndex),
  });
  document.body.prepend(canvas);
  const ctx = canvas.getContext('2d');

  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  let w = 0;
  let h = 0;
  const flakes = [];

  // ----------------------------------------------------------------- helpers
  const TAU = Math.PI * 2;
  const rand = (a, b) => a + Math.random() * (b - a);
  const lerp = (a, b, t) => a + (b - a) * t;

  // Each glyph is rendered once into a small offscreen sprite, which makes the
  // per-frame drawing very cheap (this is what keeps it smooth).
  function makeSprite(glyph, size, glow) {
    const box = Math.ceil(size * 2.2);
    const c = document.createElement('canvas');
    c.width = c.height = Math.ceil(box * dpr);
    const g = c.getContext('2d');
    g.scale(dpr, dpr);
    g.font = `${size}px ${CONFIG.font}`;
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.fillStyle = `rgb(${CONFIG.color})`;
    if (glow) {
      g.shadowColor = `rgba(${CONFIG.color}, 0.9)`;
      g.shadowBlur = size * 0.45;
    }
    g.fillText(glyph, box / 2, box / 2);
    return { sprite: c, box };
  }

  function makeFlake(anywhere) {
    // Bias towards "far away" flakes, so there are many small ones and a few big ones
    const z = Math.pow(Math.random(), 1.6);
    const size = lerp(CONFIG.size[0], CONFIG.size[1], z);
    const glyph = CONFIG.glyphs[Math.floor(Math.random() * CONFIG.glyphs.length)];
    const { sprite, box } = makeSprite(glyph, size, z > 0.75);
    return {
      x: rand(0, w),
      y: anywhere ? rand(-box, h) : -box,
      z,
      sprite,
      box,
      vy: lerp(CONFIG.speed[0], CONFIG.speed[1], z) * rand(0.85, 1.15),
      amp: rand(10, 30) * (0.5 + z),    // sideways sway distance
      freq: rand(0.35, 1.1),            // sway speed
      phase: rand(0, TAU),
      rot: rand(0, TAU),
      spin: rand(-0.7, 0.7) * (1 - z * 0.5),
      alpha: lerp(0.22, 0.95, z),
    };
  }

  function resize() {
    w = window.innerWidth;
    h = window.innerHeight;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);

    const target = Math.max(
      CONFIG.minFlakes,
      Math.min(CONFIG.maxFlakes, Math.round(w * h * CONFIG.density))
    );
    while (flakes.length < target) flakes.push(makeFlake(true));
    if (flakes.length > target) flakes.length = target;
  }

  // -------------------------------------------------------------- animation
  let last = performance.now();
  let t = 0;

  function frame(now) {
    // Delta time keeps the speed identical on 60Hz, 120Hz, etc.
    // The clamp avoids a big jump when returning to a background tab.
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    t += dt;

    // A slow, gentle wind that drifts left and right over time
    const wind = 14 * Math.sin(t * 0.11) + 9 * Math.sin(t * 0.27 + 1.3);

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (const f of flakes) {
      f.y += f.vy * dt;
      f.x += (wind * (0.3 + f.z) + Math.cos(t * f.freq + f.phase) * f.amp * f.freq) * dt;
      f.rot += f.spin * dt;

      // Wrap around the edges / respawn at the top
      if (f.y > h + f.box) {
        f.y = -f.box;
        f.x = rand(0, w);
      }
      if (f.x < -f.box) f.x = w + f.box;
      else if (f.x > w + f.box) f.x = -f.box;

      // Fade out softly near the bottom of the screen
      const fade = Math.min(1, Math.max(0, (h - f.y) / (h * 0.18)));
      ctx.globalAlpha = f.alpha * fade;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.translate(f.x, f.y);
      ctx.rotate(f.rot);
      ctx.drawImage(f.sprite, -f.box / 2, -f.box / 2, f.box, f.box);
    }

    requestAnimationFrame(frame);
  }

  // ------------------------------------------------------------------ start
  resize();
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, 150);
  });
  requestAnimationFrame(frame);
})();