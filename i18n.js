/* Language switcher — EN / JA (extensible to ZH, KO, etc.)
 * Usage: add data-en="..." data-ja="..." to any element with text.
 *        For HTML content (bold, spans): also add data-html="true".
 *        For href swaps: add data-href-en="..." data-href-ja="...".
 * Lang persisted in localStorage key 'sachin_lang'.
 */
(function () {
  var LANG_KEY = 'sachin_lang';
  function getStoredLang() {
    try {
      return window.localStorage ? localStorage.getItem(LANG_KEY) : null;
    } catch (e) {
      return null;
    }
  }

  function setStoredLang(lang) {
    try {
      if (window.localStorage) {
        localStorage.setItem(LANG_KEY, lang);
      }
    } catch (e) {
      // Language switching should still work if storage is blocked.
    }
  }

  var currentLang = getStoredLang() || 'en';

  function applyLang(lang) {
    currentLang = lang;
    setStoredLang(lang);
    document.documentElement.lang = lang === 'ja' ? 'ja' : 'en';

    // Translate text/html nodes
    document.querySelectorAll('[data-en]').forEach(function (el) {
      var text = el.getAttribute('data-' + lang) || el.getAttribute('data-en');
      if (!text) return;
      if (el.getAttribute('data-html') === 'true') {
        el.innerHTML = text;
      } else {
        el.textContent = text;
      }
    });

    // Swap hrefs (e.g. EN/JA resume downloads)
    document.querySelectorAll('[data-href-en]').forEach(function (el) {
      el.href = (lang === 'ja')
        ? (el.getAttribute('data-href-ja') || el.getAttribute('data-href-en'))
        : el.getAttribute('data-href-en');
    });

    // Page title
    var titleEn = document.body && document.body.getAttribute('data-title-en');
    var titleJa = document.body && document.body.getAttribute('data-title-ja');
    if (lang === 'ja' && titleJa) {
      document.title = titleJa;
    } else if (titleEn) {
      document.title = titleEn;
    }

    // Active button state
    document.querySelectorAll('.lang-btn').forEach(function (btn) {
      var isActive = btn.getAttribute('data-lang') === lang;
      btn.classList.toggle('lang-btn--active', isActive);
      btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
  }

  // Public API
  window.setLang = function (lang) { applyLang(lang); };

  document.addEventListener('DOMContentLoaded', function () {
    applyLang(currentLang);
    document.querySelectorAll('.lang-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        setLang(btn.getAttribute('data-lang'));
      });
    });
  });
})();
