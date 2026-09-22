/* Small progressive enhancements. The site works without JavaScript. */
(function () {
  "use strict";

  /* ---------- colour theme ----------
     The chosen theme is remembered in localStorage.  That covers the site as
     soon as it is served over http(s).  When the pages are opened straight
     from disk, browsers give every file:// document its own storage area, so
     localStorage would be empty again on the next page; there the choice is
     carried along in the link hash instead. */
  var root = document.documentElement;
  var storageWorks = (function () {
    try {
      localStorage.setItem("__themeprobe", "1");
      localStorage.removeItem("__themeprobe");
      return true;
    } catch (e) { return false; }
  })();
  // file:// reports working storage but keeps a separate area per document,
  // so the hash is needed there as well.
  var byHash = !storageWorks || location.protocol === "file:";

  function systemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function carryThemeInLinks(theme) {
    if (!byHash) return;
    var links = document.getElementsByTagName("a");
    for (var i = 0; i < links.length; i++) {
      var href = links[i].getAttribute("href");
      if (!href || /^([a-z]+:|\/\/|#)/i.test(href)) continue;   // external, mail, anchors
      if (!/\.html([#?]|$)/.test(href)) continue;               // only site pages
      links[i].setAttribute("href", href.split("#")[0] + "#theme=" + theme);
    }
  }

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    try { localStorage.setItem("theme", theme); } catch (e) {}
    carryThemeInLinks(theme);
  }

  // A theme that arrived through the hash is already applied by the inline
  // script in <head>; keep passing it on, then tidy the address bar.
  if (root.getAttribute("data-theme")) {
    carryThemeInLinks(root.getAttribute("data-theme"));
    if (/^#theme=(dark|light)$/.test(location.hash) && window.history.replaceState) {
      try {
        window.history.replaceState(null, "", location.pathname + location.search);
      } catch (e) {}
    }
  }

  var btn = document.getElementById("themebtn");
  if (btn) {
    btn.addEventListener("click", function () {
      applyTheme((root.getAttribute("data-theme") || systemTheme()) === "dark"
                 ? "light" : "dark");
    });
  }

  /* ---------- BibTeX toggles ---------- */
  document.addEventListener("click", function (ev) {
    var t = ev.target;
    if (!t.classList || !t.classList.contains("bibtn")) return;
    var box = document.getElementById("bib-" + t.dataset.key);
    if (!box) return;
    box.hidden = !box.hidden;
    t.textContent = box.hidden ? "BibTeX" : "hide BibTeX";
  });

  /* ---------- publication filters ---------- */
  var q = document.getElementById("q");
  if (!q) return;
  var fy = document.getElementById("fy");
  var ft = document.getElementById("ft");
  var cnt = document.getElementById("cnt");
  var pubs = [].slice.call(document.querySelectorAll(".pub"));
  var groups = [].slice.call(document.querySelectorAll(".pubyear"));

  function apply() {
    var needle = q.value.trim().toLowerCase();
    var year = fy.value;
    var topic = ft.value.toLowerCase();
    var shown = 0;

    pubs.forEach(function (p) {
      var ok = true;
      if (needle && p.dataset.search.indexOf(needle) === -1) ok = false;
      if (ok && year && p.dataset.year !== year) ok = false;
      if (ok && topic && p.dataset.topics.indexOf(topic) === -1) ok = false;
      p.hidden = !ok;
      if (ok) shown++;
    });

    groups.forEach(function (g) {
      g.hidden = !g.querySelector(".pub:not([hidden])");
    });

    cnt.textContent = shown === pubs.length
      ? pubs.length + " publications"
      : shown + " of " + pubs.length;
  }

  [q, fy, ft].forEach(function (el) {
    el.addEventListener("input", apply);
    el.addEventListener("change", apply);
  });
  apply();
})();
