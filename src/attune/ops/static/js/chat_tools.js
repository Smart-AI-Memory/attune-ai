/**
 * Tools inventory — "Use in chat" copy-to-clipboard handler.
 *
 * Each [data-copy-chat] button carries the trigger phrase (skill
 * natural-language phrase, or slash command "/foo") as its
 * data-copy-chat attribute. On click, the phrase is copied to the
 * clipboard so the user can paste it into Claude Code chat. The
 * button briefly flashes "Copied ✓" / "Copy failed" feedback inline.
 *
 * Mirrors the existing run_view.js copyReportToClipboard pattern;
 * kept separate so the workflows-page concern stays isolated from
 * the run-view concern. Graceful no-op when
 * navigator.clipboard.writeText is unavailable (old browsers /
 * insecure contexts).
 *
 * See docs/specs/dashboard-tools-inventory/decisions.md.
 */
(function () {
  "use strict";

  function flashCopyState(btn, message, ok) {
    var prev = btn.textContent;
    btn.textContent = message;
    btn.classList.toggle("is-copied", !!ok);
    btn.classList.toggle("is-failed", !ok);
    setTimeout(function () {
      btn.textContent = prev;
      btn.classList.remove("is-copied");
      btn.classList.remove("is-failed");
    }, 1500);
  }

  function copyTriggerToClipboard(btn) {
    var phrase = btn.getAttribute("data-copy-chat") || "";
    if (!phrase) {
      flashCopyState(btn, "Nothing to copy", false);
      return Promise.resolve(false);
    }
    if (!navigator.clipboard || !navigator.clipboard.writeText) {
      // Same fallback shape as run_view.js: surface the error rather
      // than silently fail. Users on insecure contexts (http://)
      // need to know the clipboard API is gated; modern browsers in
      // secure contexts (https://, localhost) work normally.
      flashCopyState(btn, "Clipboard unavailable", false);
      return Promise.resolve(false);
    }
    return navigator.clipboard.writeText(phrase).then(
      function () {
        flashCopyState(btn, "Copied ✓", true);
        return true;
      },
      function () {
        flashCopyState(btn, "Copy failed", false);
        return false;
      }
    );
  }

  function wireCopyChatButtons() {
    var buttons = document.querySelectorAll("[data-copy-chat]");
    for (var i = 0; i < buttons.length; i++) {
      (function (btn) {
        btn.addEventListener("click", function () {
          copyTriggerToClipboard(btn);
        });
      })(buttons[i]);
    }
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", wireCopyChatButtons);
    } else {
      wireCopyChatButtons();
    }
  }

  // Test hook — exposed for unit tests that simulate clicks without
  // a real DOMContentLoaded cycle. Production code doesn't call this.
  if (typeof window !== "undefined") {
    window.__attuneChatTools = {
      copyTriggerToClipboard: copyTriggerToClipboard,
      wireCopyChatButtons: wireCopyChatButtons,
    };
  }
})();
