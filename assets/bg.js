/* Optional full-page background animation.
 *
 * Which one runs (if any) is picked in _build/config.yaml under
 * options.background_animation, and lands on <body data-bg="...">.
 * Nothing here does anything unless that attribute names one of the
 * patterns registered below. All patterns are intentionally very subtle
 * (low opacity, slow motion) - they sit behind the page content and must
 * never compete with it for attention.
 *
 * Respects prefers-reduced-motion (skips entirely) and pauses while the
 * tab is hidden. The canvas is purely decorative (aria-hidden, no pointer
 * events) and never affects layout or reading order.
 */
(function () {
  "use strict";

  var body = document.body;
  var key = body && body.getAttribute("data-bg");
  if (!key || key === "none") return;
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  var canvas = document.getElementById("bg-anim");
  if (!canvas) return;
  var ctx = canvas.getContext("2d");

  function accent() {
    var v = getComputedStyle(document.documentElement).getPropertyValue("--acc");
    return (v || "#10635c").trim();
  }
  function rgba(hex, a) {
    hex = hex.replace("#", "");
    if (hex.length === 3) hex = hex.split("").map(function (c) { return c + c; }).join("");
    var r = parseInt(hex.slice(0, 2), 16), g = parseInt(hex.slice(2, 4), 16), b = parseInt(hex.slice(4, 6), 16);
    return "rgba(" + r + "," + g + "," + b + "," + a + ")";
  }
  var W = 0, H = 0, DPR = Math.min(window.devicePixelRatio || 1, 1.5);
  function resize() {
    W = canvas.width = Math.round(window.innerWidth * DPR);
    H = canvas.height = Math.round(window.innerHeight * DPR);
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
  }
  window.addEventListener("resize", resize);
  resize();
  function s(w) { return Math.min(w / 1400, 2); }   // scale factor for a full-page canvas

  var running = true;
  document.addEventListener("visibilitychange", function () {
    running = document.visibilityState === "visible";
  });

  /* ---------------------------------------------------------------------
   *  Patterns - each returns a draw(t) function bound to the live canvas.
   * ------------------------------------------------------------------- */
  var patterns = {};

  patterns.lattice = function () {
    return function (t) {
      var ac = accent(), step = 68 * s(W);
      var ox = Math.sin(t * 0.00025) * step * 0.4, oy = Math.cos(t * 0.0002) * step * 0.3;
      var cols = Math.ceil(W / step) + 2, rows = Math.ceil(H / step) + 2;
      var pts = [];
      for (var i = -1; i < cols; i++) for (var j = -1; j < rows; j++) {
        pts.push([i * step + ox + (j % 2 ? step * 0.5 : 0), j * step * 0.87 + oy]);
      }
      ctx.lineWidth = 1 * s(W);
      ctx.strokeStyle = rgba(ac, 0.07);
      for (var a = 0; a < pts.length; a++) for (var b = 0; b < pts.length; b++) {
        var dx = pts[a][0] - pts[b][0], dy = pts[a][1] - pts[b][1], d = Math.hypot(dx, dy);
        if (d > 0 && d < step * 1.05) { ctx.beginPath(); ctx.moveTo(pts[a][0], pts[a][1]); ctx.lineTo(pts[b][0], pts[b][1]); ctx.stroke(); }
      }
      ctx.fillStyle = rgba(ac, 0.20);
      for (var k = 0; k < pts.length; k++) {
        var x = pts[k][0], y = pts[k][1];
        var pulse = 1.5 + Math.sin(t * 0.0016 + x * 0.02 + y * 0.02) * 0.7;
        ctx.beginPath(); ctx.arc(x, y, pulse * s(W), 0, Math.PI * 2); ctx.fill();
      }
    };
  };

  patterns.contours = function () {
    function field(x, y, tt) {
      return Math.sin(x * 0.008 + tt * 0.0002) + Math.cos(y * 0.009 - tt * 0.00015) + Math.sin((x + y) * 0.005 + tt * 0.00025);
    }
    return function (t) {
      var ac = accent();
      var levels = [-1.4, -0.8, -0.2, 0.4, 1.0, 1.6];
      var cell = 12 * s(W);
      levels.forEach(function (lv, li) {
        ctx.beginPath();
        ctx.strokeStyle = rgba(ac, 0.055 + (li % 2) * 0.035);
        ctx.lineWidth = 1;
        for (var x = 0; x < W; x += cell) {
          var started = false;
          for (var y = 0; y < H; y += cell) {
            var v = field(x, y, t);
            if (Math.abs(v - lv) < 0.06) {
              if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
            } else started = false;
          }
        }
        ctx.stroke();
      });
    };
  };

  patterns.orbits = function () {
    return function (t) {
      var ac = accent();
      var centers = [[W * 0.18, H * 0.3], [W * 0.82, H * 0.65], [W * 0.5, H * 0.85], [W * 0.85, H * 0.15]];
      centers.forEach(function (c, ci) {
        var rx = (30 + ci * 9) * s(W), ry = (16 + ci * 5) * s(W);
        ctx.strokeStyle = rgba(ac, 0.07);
        ctx.beginPath(); ctx.ellipse(c[0], c[1], rx, ry, ci * 0.6, 0, Math.PI * 2); ctx.stroke();
        for (var k = 0; k < 2; k++) {
          var speed = 0.00035 + ci * 0.00012 + k * 0.00018;
          var ang = t * speed * (k ? 1 : -1) + k * Math.PI + ci;
          var x = c[0] + Math.cos(ang) * rx * Math.cos(ci * 0.6) - Math.sin(ang) * ry * Math.sin(ci * 0.6);
          var y = c[1] + Math.cos(ang) * rx * Math.sin(ci * 0.6) + Math.sin(ang) * ry * Math.cos(ci * 0.6);
          ctx.fillStyle = rgba(ac, 0.35);
          ctx.beginPath(); ctx.arc(x, y, 2.4 * s(W), 0, Math.PI * 2); ctx.fill();
        }
      });
    };
  };

  patterns.diffusion = function () {
    var parts = null;
    function ensure() {
      if (parts) return;
      var n = Math.round((W * H) / 16000);
      parts = [];
      for (var i = 0; i < n; i++) parts.push({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - 0.5) * 0.05, vy: (Math.random() - 0.5) * 0.05 });
    }
    return function (t) {
      ensure();
      var ac = accent(), step = 56 * s(W);
      ctx.strokeStyle = rgba(ac, 0.03);
      ctx.lineWidth = 1;
      for (var x = 0; x < W; x += step) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
      for (var y = 0; y < H; y += step) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
      if (running) parts.forEach(function (p) {
        p.x += p.vx * 16; p.y += p.vy * 16;
        if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
        if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
      });
      ctx.fillStyle = rgba(ac, 0.24);
      parts.forEach(function (p) { ctx.beginPath(); ctx.arc(p.x, p.y, 1.5 * s(W), 0, Math.PI * 2); ctx.fill(); });
      ctx.strokeStyle = rgba(ac, 0.09);
      for (var i = 0; i < parts.length; i++) for (var j = i + 1; j < parts.length; j++) {
        var dx = parts[i].x - parts[j].x, dy = parts[i].y - parts[j].y, d = Math.hypot(dx, dy);
        if (d < step * 0.6) { ctx.beginPath(); ctx.moveTo(parts[i].x, parts[i].y); ctx.lineTo(parts[j].x, parts[j].y); ctx.stroke(); }
      }
    };
  };

  patterns.waves = function () {
    return function (t) {
      var ac = accent();
      var blobs = [
        [0.25 + Math.sin(t * 0.00016) * 0.12, 0.3 + Math.cos(t * 0.00013) * 0.10, 0.55],
        [0.75 + Math.cos(t * 0.00015) * 0.12, 0.65 + Math.sin(t * 0.00018) * 0.10, 0.46],
        [0.5 + Math.sin(t * 0.0002 + 2) * 0.10, 0.2 + Math.cos(t * 0.00016 + 1) * 0.12, 0.4],
      ];
      blobs.forEach(function (bl) {
        var cx = bl[0] * W, cy = bl[1] * H, r = bl[2] * Math.max(W, H);
        var g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
        g.addColorStop(0, rgba(ac, 0.10));
        g.addColorStop(1, rgba(ac, 0));
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, W, H);
      });
    };
  };

  patterns.wavefunction = function () {
    return function (t) {
      var ac = accent();
      var lobes = [[0.28, 0.4], [0.72, 0.4], [0.5, 0.78]];
      lobes.forEach(function (l, i) {
        var cx = l[0] * W, cy = l[1] * H;
        var breathe = 0.72 + 0.28 * Math.sin(t * 0.0008 + i * Math.PI * 0.7);
        var r = Math.min(W, H) * 0.22 * breathe;
        var rr = Math.max(r, 1);
        var g = ctx.createRadialGradient(cx, cy, 0, cx, cy, rr);
        g.addColorStop(0, rgba(ac, 0.14));
        g.addColorStop(0.6, rgba(ac, 0.05));
        g.addColorStop(1, rgba(ac, 0));
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.ellipse(cx, cy, rr, rr * 0.62, 0, 0, Math.PI * 2); ctx.fill();
      });
    };
  };

  /* Dispersionskurven / band structure - denser and closer to a real DFT
     band-structure plot: more bands, varying curvature per band (some
     nearly flat/core-like, some strongly dispersive/free-electron-like),
     plus faint dashed high-symmetry-point guides like a Gamma-X-M-Gamma path. */
  patterns.bands = function () {
    var bandDefs = [
      { base: 0.94, amp: 0.010, freq: 1.0, freq2: 2.3, ph: 0.2 },
      { base: 0.87, amp: 0.014, freq: 1.3, freq2: 2.1, ph: 1.1 },
      { base: 0.79, amp: 0.028, freq: 0.9, freq2: 2.6, ph: 0.4 },
      { base: 0.70, amp: 0.045, freq: 1.6, freq2: 1.8, ph: 2.0 },
      { base: 0.60, amp: 0.060, freq: 1.1, freq2: 2.4, ph: 0.8 },
      { base: 0.50, amp: 0.055, freq: 1.8, freq2: 1.5, ph: 1.6 },
      { base: 0.40, amp: 0.075, freq: 1.0, freq2: 2.9, ph: 0.3 },
      { base: 0.30, amp: 0.095, freq: 1.4, freq2: 1.7, ph: 1.9 },
      { base: 0.20, amp: 0.070, freq: 2.0, freq2: 2.2, ph: 0.6 },
      { base: 0.12, amp: 0.045, freq: 1.5, freq2: 1.9, ph: 2.5 },
    ];
    var kx = [0, 0.24, 0.5, 0.74, 1.0];
    return function (t) {
      var ac = accent();
      ctx.setLineDash([2 * s(W), 5 * s(W)]);
      ctx.strokeStyle = rgba(ac, 0.05);
      ctx.lineWidth = 1;
      kx.forEach(function (f) {
        var x = f * W;
        ctx.beginPath(); ctx.moveTo(x, H * 0.05); ctx.lineTo(x, H * 0.98); ctx.stroke();
      });
      ctx.setLineDash([]);

      var step = 3 * s(W);
      bandDefs.forEach(function (bd, bi) {
        ctx.beginPath();
        ctx.strokeStyle = rgba(ac, 0.075 + (bi % 3) * 0.018);
        ctx.lineWidth = 1.15 * s(W);
        for (var x = 0; x <= W; x += step) {
          var k = x / W * Math.PI * 2;
          var y = H * bd.base
            - Math.sin(k * bd.freq + bd.ph + t * 0.00015) * H * bd.amp
            - Math.sin(k * bd.freq2 + bd.ph * 1.6) * H * bd.amp * 0.3;
          if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.stroke();
      });
    };
  };

  patterns.mdtraj = function () {
    var atoms = null;
    function ensure() {
      if (atoms) return;
      var cols = 7, rows = 5;
      atoms = [];
      for (var i = 0; i < cols; i++) for (var j = 0; j < rows; j++) {
        atoms.push({ bx: (i + 0.5) / cols * W, by: (j + 0.5) / rows * H, ph: Math.random() * 1000, amp: 6 + Math.random() * 6, trail: [] });
      }
    }
    return function (t) {
      ensure();
      var ac = accent();
      atoms.forEach(function (a) {
        var x = a.bx + Math.sin(t * 0.0012 + a.ph) * a.amp * s(W);
        var y = a.by + Math.cos(t * 0.0009 + a.ph * 1.3) * a.amp * 0.8 * s(W);
        if (running) { a.trail.push([x, y]); if (a.trail.length > 16) a.trail.shift(); }
        ctx.beginPath();
        a.trail.forEach(function (p, i) { if (i === 0) ctx.moveTo(p[0], p[1]); else ctx.lineTo(p[0], p[1]); });
        ctx.strokeStyle = rgba(ac, 0.10); ctx.lineWidth = 1;
        ctx.stroke();
        ctx.fillStyle = rgba(ac, 0.30);
        ctx.beginPath(); ctx.arc(x, y, 2 * s(W), 0, Math.PI * 2); ctx.fill();
      });
    };
  };

  patterns.interference = function () {
    return function (t) {
      var ac = accent();
      var sources = [[W * 0.35, H * 0.5], [W * 0.65, H * 0.5]];
      var maxR = 0.5 * Math.max(W, H);
      sources.forEach(function (src) {
        for (var ring = 0; ring < 6; ring++) {
          var r = (t * 0.5 * s(W) + ring * 40 * s(W)) % maxR;
          ctx.beginPath();
          ctx.strokeStyle = rgba(ac, 0.09 * (1 - r / maxR));
          ctx.lineWidth = 1;
          ctx.arc(src[0], src[1], r, 0, Math.PI * 2);
          ctx.stroke();
        }
      });
    };
  };

  patterns.levels = function () {
    var levelsY = [0.85, 0.68, 0.52, 0.38, 0.26, 0.16];
    var from = 3, to = 3, segStart = 0, segDur = 650, holdUntil = 900;
    return function (t) {
      var ac = accent();
      levelsY.forEach(function (ly) {
        ctx.beginPath();
        ctx.strokeStyle = rgba(ac, 0.10);
        ctx.lineWidth = 1.2;
        ctx.moveTo(W * 0.1, ly * H); ctx.lineTo(W * 0.9, ly * H);
        ctx.stroke();
      });
      if (running && t > holdUntil) {
        from = to;
        var next = from + (Math.random() < 0.5 ? -1 : 1);
        next = Math.max(0, Math.min(levelsY.length - 1, next));
        to = next; segStart = t; holdUntil = t + segDur + 700 + Math.random() * 900;
      }
      var p = Math.min(1, Math.max(0, (t - segStart) / segDur));
      var yy = (levelsY[from] + (levelsY[to] - levelsY[from]) * p) * H;
      ctx.fillStyle = rgba(ac, 0.4);
      ctx.beginPath(); ctx.arc(W * 0.5, yy, 3 * s(W), 0, Math.PI * 2); ctx.fill();
    };
  };

  patterns.hopping = function () {
    var sites = null, hoppers = null;
    function neighborOf(i) {
      var p = sites[i], best = -1, bd = 1e9;
      for (var j = 0; j < sites.length; j++) {
        if (j === i) continue;
        var d = Math.hypot(p[0] - sites[j][0], p[1] - sites[j][1]);
        if (d < bd) { bd = d; best = j; }
      }
      return best;
    }
    function ensure() {
      if (sites) return;
      var step = 62 * s(W);
      sites = [];
      var cols = Math.max(2, Math.floor(W / step)), rows = Math.max(2, Math.floor(H / step));
      for (var i = 1; i < cols; i++) for (var j = 1; j < rows; j++) sites.push([i * step, j * step]);
      hoppers = [];
      for (var k = 0; k < 6; k++) {
        var f = Math.floor(Math.random() * sites.length);
        hoppers.push({ from: f, to: f, segStart: 0, segDur: 500, holdUntil: Math.random() * 1500 });
      }
    }
    return function (t) {
      ensure();
      var ac = accent();
      ctx.fillStyle = rgba(ac, 0.12);
      sites.forEach(function (p) { ctx.beginPath(); ctx.arc(p[0], p[1], 1.6 * s(W), 0, Math.PI * 2); ctx.fill(); });
      hoppers.forEach(function (hp) {
        if (running && t > hp.holdUntil) {
          hp.from = hp.to; hp.to = neighborOf(hp.from); hp.segStart = t;
          hp.holdUntil = t + hp.segDur + 500 + Math.random() * 900;
        }
        var p = Math.min(1, Math.max(0, (t - hp.segStart) / hp.segDur));
        var a = sites[hp.from], b = sites[hp.to];
        var x = a[0] + (b[0] - a[0]) * p, y = a[1] + (b[1] - a[1]) * p;
        ctx.fillStyle = rgba(ac, 0.42);
        ctx.beginPath(); ctx.arc(x, y, 2.6 * s(W), 0, Math.PI * 2); ctx.fill();
      });
    };
  };

  patterns.front = function () {
    var dots = null;
    function ensure() {
      if (dots) return;
      var n = Math.round((W * H) / 4200);
      dots = [];
      for (var i = 0; i < n; i++) dots.push({ x: Math.random() * W, y: Math.random() * H });
    }
    return function (t) {
      ensure();
      var ac = accent(), cyc = 9000;
      var frontX = ((t % cyc) / cyc) * W * 1.3 - W * 0.15;
      var g = ctx.createLinearGradient(Math.max(0, frontX - 60), 0, frontX + 60, 0);
      g.addColorStop(0, rgba(ac, 0));
      g.addColorStop(1, rgba(ac, 0.07));
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, Math.max(0, frontX + 60), H);
      dots.forEach(function (d) {
        if (d.x < frontX) { ctx.fillStyle = rgba(ac, 0.26); ctx.beginPath(); ctx.arc(d.x, d.y, 1.6 * s(W), 0, Math.PI * 2); ctx.fill(); }
      });
      ctx.strokeStyle = rgba(ac, 0.14); ctx.lineWidth = 1.2 * s(W);
      ctx.beginPath(); ctx.moveTo(frontX, 0); ctx.lineTo(frontX, H); ctx.stroke();
    };
  };

  patterns.phase = function () {
    var blobs = null;
    function ensure() {
      if (blobs) return;
      blobs = [];
      for (var i = 0; i < 9; i++) blobs.push({ x: Math.random() * W, y: Math.random() * H, ph: Math.random() * 1000, base: 14 + Math.random() * 18 });
    }
    return function (t) {
      ensure();
      var ac = accent();
      blobs.forEach(function (b) {
        var r = (b.base * s(W)) * (1.1 + Math.sin(t * 0.0006 + b.ph) * 0.7);
        var rr = Math.max(r, 1);
        var g = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, rr);
        g.addColorStop(0, rgba(ac, 0.11));
        g.addColorStop(1, rgba(ac, 0));
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(b.x, b.y, rr, 0, Math.PI * 2); ctx.fill();
      });
    };
  };

  patterns.tank = function () {
    var dots = null;
    function ensure() {
      if (dots) return;
      var n = Math.round((W * H) / 3000);
      dots = [];
      for (var i = 0; i < n; i++) dots.push({ x: Math.random() * W, y: Math.random() * H });
    }
    return function (t) {
      ensure();
      var ac = accent();
      var level = 0.5 + 0.42 * Math.sin(t * 0.00025);
      var x0 = W * 0.36, x1 = W * 0.64, y0 = H * 0.08, y1 = H * 0.92;
      var fillY = y1 - (y1 - y0) * ((level + 1) / 2);
      ctx.strokeStyle = rgba(ac, 0.12); ctx.lineWidth = 1.2 * s(W);
      ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
      ctx.fillStyle = rgba(ac, 0.045);
      ctx.fillRect(x0, fillY, x1 - x0, Math.max(0, y1 - fillY));
      dots.forEach(function (d) {
        if (d.y > fillY && d.x > x0 && d.x < x1) { ctx.fillStyle = rgba(ac, 0.26); ctx.beginPath(); ctx.arc(d.x, d.y, 1.4 * s(W), 0, Math.PI * 2); ctx.fill(); }
      });
    };
  };

  patterns.dissociation = function () {
    return function (t) {
      var ac = accent();
      var surfY = H * 0.68;
      ctx.strokeStyle = rgba(ac, 0.11); ctx.lineWidth = 1.2 * s(W);
      ctx.beginPath(); ctx.moveTo(0, surfY); ctx.lineTo(W, surfY); ctx.stroke();
      var step = 34 * s(W);
      ctx.strokeStyle = rgba(ac, 0.07);
      for (var x = 0; x < W; x += step) { ctx.beginPath(); ctx.moveTo(x, surfY); ctx.lineTo(x - 7, surfY + 12); ctx.stroke(); }

      var cyc = 5200, p = (t % cyc) / cyc;
      var cx = W * 0.5;
      if (p < 0.45) {
        var yy = H * 0.12 + (surfY - H * 0.12 - 16) * (p / 0.45);
        var sep = 7 * s(W);
        ctx.fillStyle = rgba(ac, 0.34);
        ctx.beginPath(); ctx.arc(cx - sep, yy, 3 * s(W), 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.arc(cx + sep, yy, 3 * s(W), 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = rgba(ac, 0.18);
        ctx.beginPath(); ctx.moveTo(cx - sep, yy); ctx.lineTo(cx + sep, yy); ctx.stroke();
      } else {
        var pp = (p - 0.45) / 0.55, yy2 = surfY - 16, dxv = pp * W * 0.32;
        ctx.fillStyle = rgba(ac, 0.3 * (1 - pp * 0.4));
        ctx.beginPath(); ctx.arc(cx - 7 - dxv, yy2, 3 * s(W), 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.arc(cx + 7 + dxv, yy2, 3 * s(W), 0, Math.PI * 2); ctx.fill();
      }
    };
  };

  /* ---------------------------------------------------------------------
   *  Boot
   * ------------------------------------------------------------------- */
  var make = patterns[key];
  if (!make) return;
  var draw = make();
  var t = 0;
  function frame() {
    if (running) {
      ctx.clearRect(0, 0, W, H);
      draw(t);
      t += 16;
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
