/* Jin Zeng — profile. Progressive enhancement only: every feature below is a
   bonus on top of markup that already works with JavaScript switched off. */
(function () {
  'use strict';

  var root = document.documentElement;
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  root.classList.add('js');

  var $ = function (sel, ctx) { return (ctx || document).querySelector(sel); };
  var $$ = function (sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); };

  /* ------------------------------------------------------------------- i18n
     English lives in the HTML; assets/js/i18n.js holds zh and fr keyed by the
     English source string. Nothing here is required for the page to work — with
     JavaScript off, a visitor simply reads the English.

     t() is exported to the modules below so any string they generate at runtime
     (theme label, filter counts) follows the chosen language too. */
  var LANG_STORE = 'jz-lang';
  var lang = 'en';

  function t(str, vars) {
    var dict = (window.JZ_I18N || {})[lang];
    var out = (dict && dict[str]) || str;
    if (vars) {
      out = out.replace(/\{(\w+)\}/g, function (m, k) {
        return Object.prototype.hasOwnProperty.call(vars, k) ? vars[k] : m;
      });
    }
    return out;
  }

  (function i18n() {
    var I18N = window.JZ_I18N;
    var group = $('[data-lang-toggle]');
    if (!I18N || !group) return;

    var ATTRS = ['aria-label', 'title', 'alt', 'data-caption', 'data-alt'];
    var texts = [];   // { node, en, lead, trail, key }
    var attrs = [];   // { el, name, en }
    var titleEn = document.title;

    function skip(el) { return !!(el && el.closest && el.closest('[data-no-i18n]')); }

    // Snapshot the English source once, before anything else rewrites the DOM.
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (!n.nodeValue || !n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        var p = n.parentNode;
        if (!p || p.nodeName === 'SCRIPT' || p.nodeName === 'STYLE') return NodeFilter.FILTER_REJECT;
        return skip(p) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
      }
    });
    for (var n; (n = walker.nextNode());) {
      var raw = n.nodeValue;
      var m = /^(\s*)([\s\S]*?)(\s*)$/.exec(raw);
      texts.push({
        node: n, en: raw, lead: m[1], trail: m[3],
        key: m[2].replace(/\s+/g, ' ')
      });
    }

    $$('[' + ATTRS.join('],[') + ']').forEach(function (el) {
      if (skip(el)) return;
      ATTRS.forEach(function (name) {
        var v = el.getAttribute(name);
        if (v && v.trim()) attrs.push({ el: el, name: name, en: v });
      });
    });

    function apply(next) {
      lang = next;
      var dict = I18N[next];
      var meta = (I18N.meta || {})[next];

      texts.forEach(function (item) {
        var hit = dict && dict[item.key];
        item.node.nodeValue = hit ? item.lead + hit + item.trail : item.en;
      });
      attrs.forEach(function (item) {
        var key = item.en.replace(/\s+/g, ' ').trim();
        var hit = dict && dict[key];
        item.el.setAttribute(item.name, hit || item.en);
      });

      root.setAttribute('lang', meta ? meta.code : 'en');
      document.title = meta && meta.title ? meta.title : titleEn;

      $$('button', group).forEach(function (b) {
        b.setAttribute('aria-pressed', String(b.getAttribute('data-lang') === next));
      });

      // Let modules that build their own strings re-render in the new language.
      document.dispatchEvent(new CustomEvent('jz:lang', { detail: { lang: next } }));
    }

    group.addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-lang]');
      if (!btn) return;
      var next = btn.getAttribute('data-lang');
      if (next === lang) return;
      apply(next);
      try { localStorage.setItem(LANG_STORE, next); } catch (err) { /* private mode */ }
    });

    var saved = null;
    try { saved = localStorage.getItem(LANG_STORE); } catch (err) { /* ignore */ }
    if (saved && I18N[saved]) apply(saved);
  }());

  /* ---------------------------------------------------------------- theme */
  (function theme() {
    var btn = $('[data-theme-toggle]');
    if (!btn) return;
    var label = $('.themetoggle__label', btn);

    function paint(mode) {
      var dark = mode === 'dark';
      root.setAttribute('data-theme', mode);
      btn.setAttribute('aria-pressed', String(dark));
      if (label) label.textContent = dark ? t('Light mode') : t('Dark mode');
      btn.setAttribute('title', dark ? t('Switch to light mode') : t('Switch to dark mode'));
    }
    document.addEventListener('jz:lang', function () {
      paint(root.getAttribute('data-theme') || 'light');
    });

    paint(root.getAttribute('data-theme') ||
          (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));

    btn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      paint(next);
      try { localStorage.setItem('jz-theme', next); } catch (e) { /* private mode */ }
    });
  }());

  /* ------------------------------------------------------------ mobile nav */
  (function nav() {
    var btn = $('.navtoggle');
    var panel = $('#sitenav');
    if (!btn || !panel) return;

    function set(open) {
      panel.classList.toggle('is-open', open);
      btn.setAttribute('aria-expanded', String(open));
    }
    btn.addEventListener('click', function () {
      set(btn.getAttribute('aria-expanded') !== 'true');
    });
    panel.addEventListener('click', function (e) {
      if (e.target.closest('a')) set(false);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && btn.getAttribute('aria-expanded') === 'true') { set(false); btn.focus(); }
    });
  }());

  /* --------------------------------------------------- current nav section */
  (function currentSection() {
    if (!('IntersectionObserver' in window)) return;
    var links = $$('.sitenav a[href^="#"]');
    var map = {};
    var targets = [];

    links.forEach(function (a) {
      var el = document.getElementById(a.getAttribute('href').slice(1));
      if (el) { map[el.id] = a; targets.push(el); }
    });
    if (!targets.length) return;

    var seen = {};
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { seen[en.target.id] = en.isIntersecting ? en.intersectionRatio : 0; });

      var bestId = null, best = 0;
      Object.keys(seen).forEach(function (id) { if (seen[id] > best) { best = seen[id]; bestId = id; } });

      links.forEach(function (a) { a.removeAttribute('aria-current'); });
      if (bestId && map[bestId]) map[bestId].setAttribute('aria-current', 'true');
    }, { rootMargin: '-25% 0px -55% 0px', threshold: [0, 0.15, 0.4, 0.75, 1] });

    targets.forEach(function (el) { io.observe(el); });
  }());

  /* ------------------------------------------------------ engagement chart */
  (function chart() {
    var fig = $('[data-chart]');
    if (!fig) return;

    var bars = $$('.bar', fig);
    bars.forEach(function (bar, i) {
      bar.style.setProperty('--i', bar.getAttribute('data-i') || String(i + 1));
    });

    if (reduceMotion.matches) return;

    if (!('IntersectionObserver' in window)) { fig.classList.add('is-anim'); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        fig.classList.add('is-anim');
        io.disconnect();
      });
    }, { threshold: 0.2 });
    io.observe(fig);
  }());

  /* -------------------------------------------------- engagement filtering */
  (function filters() {
    var group = $('.filters');
    var list = $('[data-projects]');
    var status = $('[data-filter-status]');
    if (!group || !list) return;

    var chips = $$('.chip', group);
    var items = $$('.proj', list);

    function apply(family) {
      var shown = 0;
      items.forEach(function (item) {
        var fams = (item.getAttribute('data-family') || '').split(/\s+/);
        var match = family === 'all' || fams.indexOf(family) !== -1;
        item.hidden = !match;
        if (match) shown++;
      });
      chips.forEach(function (c) {
        c.setAttribute('aria-pressed', String(c.getAttribute('data-family') === family));
      });
      if (status) {
        if (family === 'all') {
          status.textContent = t('Showing all {n} engagements.', { n: shown });
        } else {
          var chip = chips.filter(function (c) { return c.getAttribute('data-family') === family; })[0];
          var name = chip.textContent.replace(/\s*\d+\s*$/, '').trim();
          status.textContent = t(shown === 1
            ? 'Showing {n} engagement in {family}.'
            : 'Showing {n} engagements in {family}.', { n: shown, family: name });
        }
      }
      shownFamily = family;
    }
    var shownFamily = 'all';
    document.addEventListener('jz:lang', function () { apply(shownFamily); });

    chips.forEach(function (c) {
      c.addEventListener('click', function () { apply(c.getAttribute('data-family')); });
    });

    // Arriving from a chart bar must never land on a hidden project.
    window.addEventListener('hashchange', function () {
      var el = document.getElementById(location.hash.slice(1));
      if (el && el.classList.contains('proj') && el.hidden) apply('all');
    });
  }());

  /* --------------------------------------------------------- gallery albums */
  (function albums() {
    var group = $('.gallery__filters');
    var grid = $('#gallery-grid');
    var count = $('.gallery__count');
    if (!group || !grid) return;

    var chips = $$('.chip', group);
    var items = $$('.gallery__item', grid);
    var total = items.length;

    group.addEventListener('click', function (e) {
      var chip = e.target.closest('.chip');
      if (!chip) return;
      var album = chip.getAttribute('data-album');
      var shown = 0;

      items.forEach(function (item) {
        var match = album === 'all' || item.getAttribute('data-album') === album;
        item.hidden = !match;
        if (match) shown++;
      });
      chips.forEach(function (c) {
        c.setAttribute('aria-pressed', String(c.getAttribute('data-album') === album));
      });
      if (count) {
        count.textContent = album === 'all'
          ? t('Showing all {n} photos.', { n: total })
          : t('Showing {n} of {total} photos in {album}.',
              { n: shown, total: total, album: chip.textContent.trim() });
      }
      shownAlbum = album;
    });

    var shownAlbum = 'all';
    document.addEventListener('jz:lang', function () {
      if (!count) return;
      if (shownAlbum === 'all') {
        count.textContent = t('Showing all {n} photos.', { n: total });
      } else {
        var chip = chips.filter(function (c) { return c.getAttribute('data-album') === shownAlbum; })[0];
        var shown = items.filter(function (i) { return !i.hidden; }).length;
        count.textContent = t('Showing {n} of {total} photos in {album}.',
          { n: shown, total: total, album: chip.textContent.trim() });
      }
    });
  }());

  /* --------------------------------------------------------------- lightbox */
  (function lightbox() {
    var dlg = $('#lightbox');
    var grid = $('#gallery-grid');
    if (!dlg || !grid || typeof dlg.showModal !== 'function') return;

    var img = $('[data-lb-img]', dlg);
    var cap = $('[data-lb-cap]', dlg);
    var num = $('[data-lb-count]', dlg);
    var shots = [];
    var at = 0;
    var opener = null;
    var blank = img.getAttribute('src');   // inert placeholder, restored on close

    var webp = (function () {
      try {
        return document.createElement('canvas')
          .toDataURL('image/webp').indexOf('data:image/webp') === 0;
      } catch (e) { return false; }
    }());

    function visible() {
      return $$('.gallery__item', grid)
        .filter(function (li) { return !li.hidden; })
        .map(function (li) { return $('.shot', li); })
        .filter(Boolean);
    }

    function show(i) {
      if (!shots.length) return;
      at = (i + shots.length) % shots.length;
      var s = shots[at];
      var src = webp ? s.getAttribute('data-full-webp') : s.getAttribute('data-full');
      img.src = src || s.getAttribute('data-full');
      img.alt = s.getAttribute('data-alt') || '';
      cap.textContent = s.getAttribute('data-caption') || '';
      num.textContent = (at + 1) + ' / ' + shots.length;
    }

    grid.addEventListener('click', function (e) {
      var shot = e.target.closest('.shot');
      if (!shot) return;
      shots = visible();
      var i = shots.indexOf(shot);
      if (i === -1) return;
      opener = shot;
      show(i);
      dlg.showModal();
    });

    $('[data-lb-close]', dlg).addEventListener('click', function () { dlg.close(); });
    $('[data-lb-prev]', dlg).addEventListener('click', function () { show(at - 1); });
    $('[data-lb-next]', dlg).addEventListener('click', function () { show(at + 1); });

    dlg.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft') { e.preventDefault(); show(at - 1); }
      if (e.key === 'ArrowRight') { e.preventDefault(); show(at + 1); }
    });

    // Click the backdrop (outside the figure) to dismiss.
    dlg.addEventListener('click', function (e) {
      if (e.target === dlg) dlg.close();
    });

    dlg.addEventListener('close', function () {
      img.setAttribute('src', blank);
      img.alt = '';
      if (opener) { opener.focus(); opener = null; }
    });
  }());

  /* ----------------------------------------------------------- scroll reveal */
  (function reveal() {
    if (!('IntersectionObserver' in window) || reduceMotion.matches) return;

    var targets = $$('.roles > .row, .projects > .row, .card, .hobbies > li, .gallery__item, .tally, .langs');
    if (!targets.length) return;

    targets.forEach(function (el) { el.classList.add('reveal'); });

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        en.target.classList.add('is-in');
        io.unobserve(en.target);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

    targets.forEach(function (el) { io.observe(el); });
  }());

  /* --------------------------------------------------------------- footer year */
  (function year() {
    var el = $('[data-year]');
    if (el) el.textContent = String(new Date().getFullYear());
  }());

}());
