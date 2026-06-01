// Workflows page — kebab action menu (A3b).
//
// Each row has a ⋯ button that opens a 3-item menu per decisions.md D5:
//   - View recent runs   → toggles the per-row .recent-runs strip
//   - Copy run command   → `attune workflow run <name>` (+ --path <scope>
//                          when the row's scope picker has a value)
//   - View docs          → /help/<workflow-name> in new tab (falls back
//                          to /help index if a per-workflow help page
//                          doesn't exist yet)
//
// Distinct from the Specs page kebab (which is about spec-metadata
// navigation): Workflows kebab is about run-management.
//
// Menu floats positioned via fixed coordinates anchored to the kebab
// cell, appended to <body> so it escapes table overflow. Closes on:
// outside click, Escape, item select.
//
// Read-only mode safe: all 3 actions are non-mutating. No allow_run
// gating needed.
//
// Exports window.__attuneWorkflowsKebab for source-grep tests +
// future PR hooks.

(function () {
  "use strict";

  // ---------------------------------------------------------------
  // State
  // ---------------------------------------------------------------

  var openMenu = null; // current open <div.kebab-menu> or null
  var openTrigger = null; // the kebab button that opened it
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
    var workflowName = btn.getAttribute("data-kebab") || "";

    var menu = document.createElement("div");
    menu.className = "kebab-menu";
    menu.setAttribute("role", "menu");
    menu.setAttribute("aria-label", "Actions for " + workflowName);

    menu.innerHTML = [
      '<button type="button" role="menuitem" class="kebab-menu-item" ' +
        'data-action="recent">View recent runs</button>',
      '<button type="button" role="menuitem" class="kebab-menu-item" ' +
        'data-action="copy">Copy run command</button>',
      '<button type="button" role="menuitem" class="kebab-menu-item" ' +
        'data-action="docs">View docs ' +
        '<span class="kebab-external-glyph" aria-hidden="true">↗</span>' +
        "</button>",
    ].join("");

    document.body.appendChild(menu);

    // Position: below + right-aligned to the kebab cell.
    var rect = btn.getBoundingClientRect();
    var menuRect = menu.getBoundingClientRect();
    menu.style.top = rect.bottom + window.scrollY + 4 + "px";
    menu.style.left = rect.right + window.scrollX - menuRect.width + "px";

    // Wire item handlers.
    var items = menu.querySelectorAll(".kebab-menu-item");
    items.forEach(function (item) {
      item.addEventListener("click", function (ev) {
        ev.stopPropagation();
        if (item.hasAttribute("disabled")) return;
        var action = item.getAttribute("data-action");
        handleAction(action, workflowName, tr);
        closeMenu();
      });
    });

    btn.setAttribute("aria-expanded", "true");
    openMenu = menu;
    openTrigger = btn;

    var firstEnabled = menu.querySelector(".kebab-menu-item:not([disabled])");
    if (firstEnabled) firstEnabled.focus();
  }

  // ---------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------

  function handleAction(action, workflowName, tr) {
    if (action === "recent") {
      // Toggle the existing per-row recent-runs strip. It's hidden
      // by default; runner.js populates it after the first run.
      var strip = tr.querySelector(
        '[data-recent-runs="' + cssEscape(workflowName) + '"]'
      );
      if (!strip) {
        showToast("No recent-runs strip on this row.");
        return;
      }
      strip.hidden = !strip.hidden;
      return;
    }
    if (action === "copy") {
      // Build the CLI command. If the row has a scope picker with a
      // non-empty value, include --path. Custom-path inputs (the
      // "Custom path…" option opens an input) aren't included unless
      // they have an actual value.
      var cmd = "attune workflow run " + workflowName;
      var picker = tr.querySelector(".scope-picker");
      var customInput = tr.querySelector(".scope-custom");
      var scope = "";
      if (
        customInput &&
        !customInput.hidden &&
        customInput.value &&
        customInput.value.trim()
      ) {
        scope = customInput.value.trim();
      } else if (picker && picker.value && picker.value !== "__custom__") {
        scope = picker.value;
      }
      if (scope) {
        cmd += " --path " + scope;
      }
      copyToClipboard(cmd).then(
        function () {
          showToast("Copied: " + cmd);
        },
        function () {
          showToast("Copy failed — clipboard unavailable.");
        }
      );
      return;
    }
    if (action === "docs") {
      // /help/<workflow-name> is the per-workflow help page (added in
      // the ops-help-page spec, PR #482-#484). If a per-workflow page
      // doesn't exist, the help route falls back to the index — no
      // 404. Open in a new tab to preserve the user's place on the
      // workflows list.
      var url = "/help/" + encodeURIComponent(workflowName);
      window.open(url, "_blank", "noopener,noreferrer");
      return;
    }
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
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
        if (ok) resolve();
        else reject(new Error("execCommand failed"));
      } catch (e) {
        reject(e);
      }
    });
  }

  function cssEscape(s) {
    // Minimal CSS.escape polyfill for the attribute selector. Workflow
    // names are alphanumeric + hyphens so this is mostly a no-op,
    // but if CSS.escape is available use it for safety.
    if (typeof CSS !== "undefined" && CSS.escape) return CSS.escape(s);
    return String(s).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
  }

  // ---------------------------------------------------------------
  // Toast feedback
  // ---------------------------------------------------------------

  function showToast(msg) {
    var t = document.getElementById("workflows-toast");
    if (!t) {
      // Inject a toast container lazily — same pattern as Specs page
      // but the workflows template doesn't include one by default.
      t = document.createElement("div");
      t.id = "workflows-toast";
      t.className = "specs-toast"; // reuse the styling
      t.setAttribute("role", "status");
      t.setAttribute("aria-live", "polite");
      document.body.appendChild(t);
    }
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
    document.querySelectorAll(".kebab-btn[data-kebab]").forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        if (openTrigger === btn) {
          closeMenu();
        } else {
          openMenuFor(btn);
        }
      });
    });
  }

  function wireGlobalClose() {
    document.addEventListener("click", function (ev) {
      if (!openMenu) return;
      if (openMenu.contains(ev.target)) return;
      if (openTrigger && openTrigger.contains(ev.target)) return;
      closeMenu();
    });
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
  window.__attuneWorkflowsKebab = {
    openMenuFor: openMenuFor,
    closeMenu: closeMenu,
    handleAction: handleAction,
    showToast: showToast,
    init: init,
  };
})();
