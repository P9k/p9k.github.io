/* Structure gallery (gallery.html): draws each paper's structure as a small
 * ball-and-stick vector graphic, with search, filters, sorting and a pop-up
 * that rotates the structure (drag to turn it by hand).
 *
 * The data comes from build.py (assets/gallery-data.js): atoms in Å,
 * optional unit cell, element colours (Jmol, overridable in config.yaml) and
 * covalent radii. No 3D engine: plain SVG, so the page stays light; only the
 * open pop-up animates, and nothing moves for visitors who prefer reduced
 * motion.
 */
(function () {
  "use strict";
  // data: assets/gallery-data.js (window.GDATA), written by build.py
  var DATA = window.GDATA;
  if (!DATA) {
    var node = document.getElementById("gdata");
    if (!node) return;
    DATA = JSON.parse(node.textContent);
  }
  var ITEMS = DATA.items, COL = DATA.colors, RAD = DATA.radii, NOBLE = {};
  DATA.noble.forEach(function (e) { NOBLE[e] = true; });
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function shade(hex, f) {
    var n = parseInt(hex.slice(1), 16), c = [n >> 16, (n >> 8) & 255, n & 255];
    return "#" + c.map(function (v) {
      v = Math.round(f < 0 ? v * (1 + f) : v + (255 - v) * f);
      return Math.max(0, Math.min(255, v)).toString(16).padStart(2, "0");
    }).join("");
  }
  // Unicode sub-/superscripts (₂, ⁴⁺ ...) -> <sub>/<sup>: many fonts have no
  // or ugly glyphs for them, real sub/sup render cleanly in the text font.
  var SUB = "₀₁₂₃₄₅₆₇₈₉₊₋₍₎", SUBN = "0123456789+−()", SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁽⁾", SUPN = "0123456789+−()";
  function chem(s) {
    return esc(s || "").replace(/[₀-₉₊₋₍₎]+/g, function (m) {
      return "<sub>" + m.split("").map(function (c) { return SUBN.charAt(SUB.indexOf(c)); }).join("") + "</sub>";
    }).replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁽⁾]+/g, function (m) {
      return "<sup>" + m.split("").map(function (c) { return SUPN.charAt(SUP.indexOf(c)); }).join("") + "</sup>";
    });
  }
  function col(e) { return COL[e] || "#ff1493"; }
  function rcov(e) { return RAD[e] || 1.5; }

  /* ---- geometry prepared once per structure ---- */
  function prepare(it) {
    var A = it.atoms, n = A.length, bonds = [], dmin = Infinity;
    for (var i = 0; i < n; i++) for (var j = i + 1; j < n; j++) {
      var d = Math.hypot(A[i][1] - A[j][1], A[i][2] - A[j][2], A[i][3] - A[j][3]);
      if (d > 0.3 && d < dmin) dmin = d;
      if (!it.bonds || NOBLE[A[i][0]] || NOBLE[A[j][0]] || d < 0.4) continue;
      if (d < it.bonds * (rcov(A[i][0]) + rcov(A[j][0]))) bonds.push([i, j]);
    }
    var fill = !bonds.length;               // no bonds: space-filling spheres
    it._bonds = bonds;
    it._r = A.map(function (a) {
      var r = rcov(a[0]);
      return fill ? Math.min(r, isFinite(dmin) ? dmin * 0.48 : r) : Math.max(0.2, Math.min(0.75, 0.18 + 0.28 * r));
    });
    if (it.cell) {
      var c = it.cell, h = [0, 0, 0], v = [];
      // cell centred like the atoms (build.py shifts by half the cell diagonal)
      for (var k = 0; k < 3; k++) h[k] = (c[0][k] + c[1][k] + c[2][k]) / 2;
      [0, 1].forEach(function (a) { [0, 1].forEach(function (b) { [0, 1].forEach(function (g) {
        v.push([0, 1, 2].map(function (k) { return a * c[0][k] + b * c[1][k] + g * c[2][k] - h[k]; }));
      }); }); });
      it._cell = v;
    }
    var yaw = 0.55, pitch = 0.35;
    if (it.view) { yaw = it.view[0] * Math.PI / 180; pitch = it.view[1] * Math.PI / 180; }
    it._yaw = yaw; it._pitch = pitch;
  }

  function rot(p, yaw, pitch) {
    var cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    var x1 = cy * p[0] + sy * p[2], z1 = -sy * p[0] + cy * p[2];
    return [x1, cp * p[1] - sp * z1, sp * p[1] + cp * z1];
  }

  var gid = 0;
  function render(svg, it, yaw, pitch) {
    var A = it.atoms, P = A.map(function (a) { return rot([a[1], a[2], a[3]], yaw, pitch); });
    var R = 0;
    P.forEach(function (p, i) { R = Math.max(R, Math.hypot(p[0], p[1]) + it._r[i]); });
    var C = it._cell ? it._cell.map(function (v) { return rot(v, yaw, pitch); }) : null;
    if (C) C.forEach(function (p) { R = Math.max(R, Math.hypot(p[0], p[1])); });
    var S = 0.9 / (R || 1), out = [], pre = "g" + (gid++), defs = "", used = {};
    if (C) {
      [[0,1],[0,2],[0,4],[1,3],[1,5],[2,3],[2,6],[3,7],[4,5],[4,6],[5,7],[6,7]].forEach(function (e) {
        var a = C[e[0]], b = C[e[1]];
        out.push({ z: -1e9, s: '<line x1="' + a[0] * S + '" y1="' + -a[1] * S + '" x2="' + b[0] * S + '" y2="' + -b[1] * S +
          '" class="gcell"/>' });
      });
    }
    it._bonds.forEach(function (bd) {
      var i = bd[0], j = bd[1], pa = P[i], pb = P[j];
      var L = Math.hypot(pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]) || 1;
      var u = [(pb[0] - pa[0]) / L, (pb[1] - pa[1]) / L, (pb[2] - pa[2]) / L];
      var ra = it._r[i] * 0.8, rb = it._r[j] * 0.8;
      var a = [pa[0] + u[0] * ra, pa[1] + u[1] * ra], b = [pb[0] - u[0] * rb, pb[1] - u[1] * rb];
      out.push({ z: Math.min(pa[2], pb[2]) - 1e-3, s: '<line x1="' + a[0] * S + '" y1="' + -a[1] * S + '" x2="' + b[0] * S +
        '" y2="' + -b[1] * S + '" class="gbond" stroke-width="' + (0.16 * S) + '"/>' });
    });
    A.forEach(function (a, i) {
      var e = a[0], p = P[i];
      if (!used[e]) {
        used[e] = 1;
        var c = col(e);
        defs += '<radialGradient id="' + pre + e + '" cx="35%" cy="32%" r="70%"><stop offset="0" stop-color="' +
          shade(c, 0.75) + '"/><stop offset=".3" stop-color="' + c + '"/><stop offset="1" stop-color="' + shade(c, -0.5) +
          '"/></radialGradient>';
      }
      out.push({ z: p[2], s: '<circle cx="' + p[0] * S + '" cy="' + -p[1] * S + '" r="' + it._r[i] * S +
        '" fill="url(#' + pre + e + ')"/>' });
    });
    out.sort(function (u, v) { return u.z - v.z; });
    svg.innerHTML = "<defs>" + defs + "</defs>" + out.map(function (o) { return o.s; }).join("");
  }

  ITEMS.forEach(prepare);

  function cardInner(it) {
    return '<svg viewBox="-1 -1 2 2" aria-hidden="true"></svg><span class="gcapt"><span class="gname">' +
      chem(it.label || it.title) + '</span><span class="gyr">' + (it.year || "") + (it.journal ? " · " + esc(it.journal) : "") + "</span></span>";
  }

  /* ---- homepage: a fresh random pick on every visit ---- */
  var pick = document.getElementById("gpick");
  if (pick) {
    var n = parseInt(pick.getAttribute("data-n"), 10) || 4, pool = ITEMS.slice();
    for (var i = pool.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1)), t = pool[i];
      pool[i] = pool[j]; pool[j] = t;
    }
    pool.slice(0, n).forEach(function (it) {
      var a = document.createElement("a");
      a.className = "gcard";
      a.href = "gallery.html#s=" + encodeURIComponent(it.key);
      a.setAttribute("aria-label", it.title);
      a.innerHTML = cardInner(it);
      render(a.querySelector("svg"), it, it._yaw, it._pitch);
      pick.appendChild(a);
    });
    return;
  }

  /* ---- gallery grid, filters, sorting ---- */
  var grid = document.getElementById("ggrid");
  if (!grid) return;
  var q = document.getElementById("gq"), ft = document.getElementById("gtile"),
      fe = document.getElementById("gel"), fs = document.getElementById("gsort"),
      cnt = document.getElementById("gcount");

  ITEMS.forEach(function (it, idx) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "gcard";
    b.setAttribute("aria-label", it.title);
    b.innerHTML = cardInner(it);
    render(b.querySelector("svg"), it, it._yaw, it._pitch);
    b.addEventListener("click", function () { openModal(it); });
    it._el = b;
    it._idx = idx;
    it._search = (it.label + " " + it.title + " " + it.journal + " " + it.topics.join(" ") + " " +
      it.elements.join(" ")).toLowerCase();
  });

  function apply() {
    var s = (q.value || "").trim().toLowerCase(), tile = ft.value, el = fe.value, mode = fs.value;
    var list = ITEMS.filter(function (it) {
      return (!s || it._search.indexOf(s) >= 0) &&
             (!tile || it.tiles.indexOf(tile) >= 0) &&
             (!el || it.elements.indexOf(el) >= 0);
    });
    list.sort(function (a, b) {
      if (mode === "old") return a.year - b.year || a._idx - b._idx;
      if (mode === "name") return (a.label || a.title).localeCompare(b.label || b.title);
      if (mode === "size") return b.n - a.n;
      return b.year - a.year || b._idx - a._idx;     // default: newest first
    });
    grid.textContent = "";
    list.forEach(function (it) { grid.appendChild(it._el); });
    cnt.textContent = list.length + " of " + ITEMS.length;
  }
  [q, ft, fe, fs].forEach(function (el) { el.addEventListener("input", apply); });
  apply();

  /* ---- pop-up ---- */
  var dlg = document.getElementById("gdlg"), msvg = document.getElementById("gsvg"),
      view = document.getElementById("gview");
  var cur = null, yaw = 0, pitch = 0, raf = 0, dragging = false, lx = 0, ly = 0;
  function spin() {
    raf = requestAnimationFrame(function () {
      if (!dlg.open) return;
      if (!dragging) { yaw += 0.004; render(msvg, cur, yaw, pitch); }
      spin();
    });
  }
  function openModal(it) {
    cur = it; yaw = it._yaw; pitch = it._pitch;
    var sys = document.getElementById("gsys");
    sys.innerHTML = chem(it.label);
    sys.hidden = !it.label;
    document.getElementById("gtitle").innerHTML = chem(it.title);
    document.getElementById("gau").innerHTML = it.authors;     // already escaped by build.py
    // Angewandte Chemie style: <i>Acta Mater.</i> <b>2025</b>, <i>298</i>, 121398.
    var head = [], ref = [];
    if (it.journal) head.push("<i>" + esc(it.journal) + "</i>");
    if (it.year) head.push("<b>" + it.year + "</b>");
    if (head.length) ref.push(head.join(" "));
    if (it.volume && it.volume !== "0") ref.push("<i>" + esc(it.volume) + "</i>");
    if (it.pages) ref.push(esc(it.pages));
    document.getElementById("gj").innerHTML = ref.length ? ref.join(", ") + "." : "";
    var cap = document.getElementById("gcap");
    cap.innerHTML = chem(it.caption);
    cap.hidden = !it.caption;
    var doi = document.getElementById("gdoi");
    doi.hidden = !it.doi;
    if (it.doi) doi.href = it.doi;
    render(msvg, it, yaw, pitch);
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", "");
    if (!reduce) spin();
  }
  function closeModal() { cancelAnimationFrame(raf); if (dlg.close) dlg.close(); else dlg.removeAttribute("open"); }
  document.getElementById("gclose").addEventListener("click", closeModal);
  dlg.addEventListener("click", function (e) { if (e.target === dlg) closeModal(); });
  dlg.addEventListener("close", function () { cancelAnimationFrame(raf); });
  view.addEventListener("pointerdown", function (e) {
    dragging = true; lx = e.clientX; ly = e.clientY;
    if (view.setPointerCapture) view.setPointerCapture(e.pointerId);
  });
  view.addEventListener("pointermove", function (e) {
    if (!dragging || !cur) return;
    yaw += (e.clientX - lx) * 0.01; pitch += (e.clientY - ly) * 0.01;
    lx = e.clientX; ly = e.clientY;
    render(msvg, cur, yaw, pitch);
  });
  ["pointerup", "pointercancel"].forEach(function (t) { view.addEventListener(t, function () { dragging = false; }); });

  /* ---- gallery.html#s=<key> (links from the homepage) opens that structure ---- */
  function fromHash() {
    var m = /(?:^#|&)s=([^&]+)/.exec(location.hash);
    if (!m) return;
    var k = decodeURIComponent(m[1]);
    for (var i = 0; i < ITEMS.length; i++) {
      if (ITEMS[i].key === k) {
        if (!dlg.open) openModal(ITEMS[i]);
        if (ITEMS[i]._el && ITEMS[i]._el.scrollIntoView) ITEMS[i]._el.scrollIntoView({ block: "center" });
        return;
      }
    }
  }
  window.addEventListener("hashchange", fromHash);
  fromHash();
})();
