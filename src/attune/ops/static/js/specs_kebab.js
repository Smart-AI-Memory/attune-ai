// Specs page — kebab action menu (A3b).
//
// Each row has a ⋯ button that opens a 3-item menu:
//   - Open in editor   → vscode://file/<abs path>
//   - Copy slug        → navigator.clipboard.writeText(slug) + toast
//   - View linked PRs  → github.com/<owner>/<repo>/pulls?q=<slug>
//
// The menu floats positioned via fixed coordinates anchored to the
// kebab cell, appended to <body> so it escapes any table overflow.
// Closes on: outside click, Escape, item select.
//
// Read-only mode safe: all 3 actions are non-mutating navigation /
// clipboard / external-link. No allow_run gating needed.
//
// Exports window.__attuneSpecsKebab so future PRs can hook the same
// open/close cycle (e.g. A3c URL-param-driven "open menu for slug=X").

(function () {
  "use strict";

  // ---------------------------------------------------------------
  // Config + state
  // ---------------------------------------------------------------

  function readConfig() {
    var node = document.getElementById("specs-config");
    if (!node) return { github_repo: "" };
    try {
      return JSON.parse(node.textContent) || { github_repo: "" };
    } catch (e) {
      return { github_repo: "" };
    }
  }

  var config = readConfig();
  var openMenu = null;       // current open <div.kebab-menu> or null
  var openTrigger = null;    // the kebab button that opened it
  var toastTimer = null;

  // ---------------------------------------------------------------
  // Menu open/close
  // ---------------------------------------------------------------

  function closeMenu() {
    if (openMenu && openMenu.parentNode) {
      openMenu.parentNode.removeChild(openMenu);
    }
    if (openTrigger) {
      openTrigger.setAttribute("aria-expanded", "false");
    }
    openMenu = null;
    openTrigger = null;
  }

  function openMenuFor(btn) {
    closeMenu();
    var tr = btn.closest("tr");
    if (!tr) return;
    var slug = btn.getAttribute("data-kebab") || "";
    var specPath = tr.getAttribute("data-spec-path") || "";

    var menu = document.createElement("div");
    menu.className = "kebab-menu";
    menu.setAttribute("role", "menu");
    menu.setAttribute("aria-label", "Actions for " + slug);

    var hasGithub = !!(config.github_repo && config.github_repo.length > 0);

    menu.innerHTML = [
      '<button type="button" role="menuitem" class="kebab-menu-item" ' +
        'data-action="editor">Open in editor</button>',
      '<button type="button" role="menuitem" class="kebab-menu-item" ' +
        'data-action="copy">Copy slug</button>',
      '<button type="button" role="menuitem" class="kebab-menu-item ' +
        (hasGithub ? "" : "kebab-menu-item-disabled") +
        '" data-action="prs"' + (hasGithub ? "" : " disabled aria-disabled=\"true\"") + '>' +
        'View linked PRs <span class="kebab-external-glyph" aria-hidden="true">↗</span></button>',
    ].join("");

    document.body.appendChild(menu);

    // Position: below + right-aligned to the kebab cell so the menu's
    // right edge meets the button's right edge (matches the wireframe).
    var rect = btn.getBoundingClientRect();
    var menuRect = menu.getBoundingClientRect();
    menu.style.top = (rect.bottom + window.scrollY + 4) + "px";
    menu.style.left = (rect.right + window.scrollX - menuRect.width) + "px";

    // Wire item handlers.
    var items = menu.querySelectorAll(".kebab-menu-item");
    items.forEach(function (item) {
      item.addEventListener("click", function (ev) {
        ev.stopPropagation();
        if (item.hasAttribute("disabled")) return;
        var action = item.getAttribute("data-action");
        handleAction(action, slug, specPath);
        closeMenu();
      });
    });

    btn.setAttribute("aria-expanded", "true");
    openMenu = menu;
    openTrigger = btn;

    // Focus first enabled item for keyboard users.
    var firstEnabled = menu.querySelector(".kebab-menu-item:not([disabled])");
    if (firstEnabled) firstEnabled.focus();
  }

  // ---------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------

  function handleAction(action, slug, specPath) {
    if (action === "editor") {
      // vscode://file/<abs-path> — works for VS Code, Cursor, Codium
      // forks. The path must be absolute; we get it from the row's
      // data-spec-path which the server populates from Path.resolve().
      if (!specPath) {
        showToast("No editor target — spec path unavailable.");
        return;
      }
      // Encode each path segment so spaces / special chars survive.
      var encoded = specPath.split("/").map(encodeURIComponent).join("/");
      window.location.href = "vscode://file/" + encoded;
      // No toast — the OS-level scheme handler takes over. If nothing
      // is registered for vscode://, the browser ignores it silently.
      return;
    }
    if (action === "copy") {
      copyToClipboard(slug).then(
        function () { showToast("Copied slug: " + slug); },
        function () { showToast("Copy failed — clipboard unavailable."); }
      );
      return;
    }
    if (action === "prs") {
      if (!config.github_repo) {
        showToast("No GitHub repo configured.");
        return;
      }
      var url = "https://github.com/" + config.github_repo +
                "/pulls?q=" + encodeURIComponent(slug);
      window.open(url, "_blank", "noopener,noreferrer");
      return;
    }
  }

  function copyToClipboard(text) {
    // Modern Clipboard API. Wrap in a Promise so the call site can
    // chain .then/.catch uniformly even when the API isn't present.
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    // Fallback: hidden textarea + execCommand. Works on older browsers
    // and non-HTTPS dev environments.
    return new Promise(function (resolve, reject) {
      try {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        var ok = document.execCommand && document.execCommand("copy");
        document.body.removeChild(ta);
        if (ok) resolve(); else reject(new Error("execCommand failed"));
      } catch (e) {
        reject(e);
      }
    });
  }

  // ---------------------------------------------------------------
  // Toast feedback
  // ---------------------------------------------------------------

  function showToast(msg) {
    var t = document.getElementById("specs-toast");
    if (!t) return;
    t.textContent = msg;
    t.classList.add("toast-visible");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      t.classList.remove("toast-visible");
    }, 2200);
  }

  // ---------------------------------------------------------------
  // Wiring
  // ---------------------------------------------------------------

  function wireKebabButtons() {
    document.querySelectorAll(".kebab-btn").forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        if (openTrigger === btn) {
          // Same button clicked again — close (toggle behavior).
          closeMenu();
        } else {
          openMenuFor(btn);
        }
      });
    });
  }

  function wireGlobalClose() {
    // Click outside the menu closes it.
    document.addEventListener("click", function (ev) {
      if (!openMenu) return;
      if (openMenu.contains(ev.target)) return;
      if (openTrigger && openTrigger.contains(ev.target)) return;
      closeMenu();
    });
    // Escape closes (and returns focus to the trigger).
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && openMenu) {
        var t = openTrigger;
        closeMenu();
        if (t) t.focus();
      }
    });
  }

  function init() {
    wireKebabButtons();
    wireGlobalClose();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Exports for future PR hooks + source-grep tests.
  window.__attuneSpecsKebab = {
    config: config,
    openMenuFor: openMenuFor,
    closeMenu: closeMenu,
    handleAction: handleAction,
    showToast: showToast,
    init: init,
  };
})();
