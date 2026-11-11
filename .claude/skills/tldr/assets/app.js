/* tldr document behaviour: one page at a time (hash routing), section highlighting in the
   contents, copy buttons, appearance settings. Everything degrades to a plain long document. */
(function () {
  "use strict";
  var root = document.documentElement;
  root.classList.add("js");

  /* ---- appearance (Wikipedia-style: text size, width, color) ---- */
  var KEY = "tldr-appearance";
  var DEFAULTS = { size: "m", width: "std", theme: "auto" };
  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; }
  }
  function save(s) {
    try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) { /* private mode */ }
  }
  var prefs = load();
  Object.keys(DEFAULTS).forEach(function (k) {
    var v = prefs[k] || DEFAULTS[k];
    root.setAttribute("data-" + k, v);
    var input = document.querySelector('.appearance input[name="' + k + '"][value="' + v + '"]');
    if (input) input.checked = true;
  });
  document.querySelectorAll(".appearance input").forEach(function (input) {
    input.addEventListener("change", function () {
      prefs[input.name] = input.value;
      root.setAttribute("data-" + input.name, input.value);
      save(prefs);
    });
  });

  /* ---- contents: open on wide screens, collapsible on narrow ones ---- */
  var tocBox = document.querySelector(".toc details");
  var wide = window.matchMedia("(min-width: 961px)");
  function syncToc() { if (tocBox) tocBox.open = wide.matches; }
  syncToc();
  if (wide.addEventListener) wide.addEventListener("change", syncToc);

  /* ---- one page at a time ---- */
  var pages = Array.prototype.slice.call(document.querySelectorAll("article.page"));
  var bundleTitle = document.body.getAttribute("data-bundle") || document.title;
  var observer = null;

  function pageFor(id) {
    if (!id) return null;
    var el = document.getElementById(id);
    if (!el) return null;
    return el.matches("article.page") ? el : el.closest("article.page");
  }

  function show(hash, scroll) {
    var id = decodeURIComponent((hash || "").replace(/^#/, ""));
    var page = pageFor(id) || pages[0];
    if (!page) return;
    pages.forEach(function (p) { p.hidden = p !== page; });
    root.classList.add("routed");
    document.querySelectorAll(".toc-pages > li").forEach(function (li) {
      li.classList.toggle("active", li.getAttribute("data-page") === page.id);
    });
    var t = page.getAttribute("data-title");
    document.title = t && pages.length > 1 && page !== pages[0] ? t + " – " + bundleTitle : bundleTitle;
    var target = id && id !== page.id ? document.getElementById(id) : null;
    if (scroll !== false) {
      if (target) target.scrollIntoView();
      else window.scrollTo(0, 0);
    }
    if (!wide.matches && tocBox && target === null) tocBox.open = false;
    spy(page);
  }

  /* highlight the section being read */
  function spy(page) {
    if (observer) observer.disconnect();
    if (!("IntersectionObserver" in window)) return;
    var links = {};
    document.querySelectorAll('.toc-pages > li[data-page="' + page.id + '"] .toc-secs a').forEach(function (a) {
      links[a.getAttribute("href").slice(1)] = a;
    });
    var heads = Array.prototype.filter.call(page.querySelectorAll("h2[id], h3[id]"), function (h) { return links[h.id]; });
    if (!heads.length) return;
    var visible = {};
    observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { visible[e.target.id] = e.isIntersecting; });
      var current = null;
      for (var i = 0; i < heads.length; i++) {
        if (heads[i].getBoundingClientRect().top < window.innerHeight * 0.35) current = heads[i].id;
      }
      Object.keys(links).forEach(function (k) { links[k].classList.toggle("current", k === current); });
    }, { rootMargin: "0px 0px -60% 0px", threshold: [0, 1] });
    heads.forEach(function (h) { observer.observe(h); });
  }

  if (pages.length > 1) {
    window.addEventListener("hashchange", function () { show(location.hash); });
    show(location.hash, Boolean(location.hash));
  } else if (pages[0]) {
    spy(pages[0]);
  }

  /* ---- copy buttons on code (not on diagrams) ---- */
  document.querySelectorAll("figure.code").forEach(function (fig) {
    var pre = fig.querySelector("pre");
    if (!pre || fig.classList.contains("output")) return;
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy";
    btn.textContent = "Copy";
    btn.setAttribute("aria-label", "Copy code");
    btn.addEventListener("click", function () {
      var clone = pre.cloneNode(true);
      clone.querySelectorAll(".p").forEach(function (n) { n.remove(); });
      var text = clone.textContent.replace(/\n$/, "");
      var done = function () {
        btn.textContent = "Copied";
        btn.classList.add("done");
        setTimeout(function () { btn.textContent = "Copy"; btn.classList.remove("done"); }, 1400);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () {});
      }
    });
    var slot = fig.querySelector(":scope > figcaption .cap-right");
    if (slot) { btn.classList.add("in-cap"); slot.appendChild(btn); } else { fig.appendChild(btn); }
  });

  /* ---- print everything, answers included ---- */
  window.addEventListener("beforeprint", function () {
    document.querySelectorAll("details").forEach(function (d) { d.setAttribute("data-was", d.open ? "1" : ""); d.open = true; });
  });
  window.addEventListener("afterprint", function () {
    document.querySelectorAll("details[data-was]").forEach(function (d) { d.open = d.getAttribute("data-was") === "1"; d.removeAttribute("data-was"); });
  });
})();
