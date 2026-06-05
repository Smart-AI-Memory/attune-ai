// Specs tab: click-to-edit status pills.
//
// Read mode: compact pill (dot + 3-letter code) with full status in
// title attribute. Click swaps in a <select> for editing; on change
// or blur, PUT to /api/specs/.../status and swap back to a pill with
// the new value. Optimistic UI with rollback on server error.
(function () {
  "use strict";

  var EDITABLE_OPTIONS = ["draft", "in-review", "approved", "complete"];

  function statusCode(status) {
    var s = (status || "").toLowerCase().trim();
    if (s === "draft") return "drf";
    if (s === "in-review" || s === "review") return "rvw";
    if (s === "approved") return "apv";
    if (s === "complete" || s === "completed" || s === "done") return "cpl";
    if (s.length > 8) return s.substring(0, 8) + "…";
    return s;
  }

  function chipClassFor(status) {
    var s = (status || "").toLowerCase().trim();
    if (
      s === "approved" ||
      s === "complete" ||
      s === "completed" ||
      s === "done"
    ) {
      return "chip-ok";
    }
    if (s === "in-review" || s === "review") return "chip-warn";
    if (s === "draft") return "chip-muted";
    return "chip-custom";
  }

  function isCustom(status) {
    var s = (status || "").toLowerCase().trim();
    if (!s) return false;
    return [
      "draft",
      "in-review",
      "review",
      "approved",
      "complete",
      "completed",
      "done",
    ].indexOf(s) === -1;
  }

  function escapeHTML(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function flash(el, ok) {
    el.classList.add(ok ? "flash-ok" : "flash-err");
    setTimeout(function () {
      el.classList.remove("flash-ok", "flash-err");
    }, 1200);
  }

  function applyPillState(pill, status) {
    pill.classList.remove("chip-ok", "chip-warn", "chip-muted", "chip-custom");
    pill.classList.add(chipClassFor(status));
    if (isCustom(status)) {
      pill.classList.add("status-pill-custom");
    } else {
      pill.classList.remove("status-pill-custom");
    }
    pill.dataset.original = status;
    pill.setAttribute("data-tooltip", status || "(no status)");
    pill.setAttribute(
      "aria-label",
      "Status for " +
        pill.dataset.phase +
        " of " +
        pill.dataset.slug +
        ": " +
        (status || "no status") +
        ". Click to edit."
    );
    var code = statusCode(status) || "(none)";
    pill.innerHTML =
      '<span class="status-dot" aria-hidden="true"></span>' +
      '<span class="status-code">' +
      escapeHTML(code) +
      "</span>";
  }

  async function submitChange(pill, prev, next) {
    var slug = pill.dataset.slug;
    var phase = pill.dataset.phase;
    try {
      var resp = await fetch(
        "/api/specs/" +
          encodeURIComponent(slug) +
          "/" +
          encodeURIComponent(phase) +
          "/status",
        {
          method: "PUT",
          headers: attuneClientHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({ status: next }),
        }
      );
      if (!resp.ok) {
        var body = await resp.text();
        console.error("status flip failed:", resp.status, body);
        applyPillState(pill, prev);
        flash(pill, false);
        pill.setAttribute("data-tooltip", "Failed: " + resp.status + " " + body);
        return false;
      }
      applyPillState(pill, next);
      flash(pill, true);
      return true;
    } catch (err) {
      console.error("status flip exception:", err);
      applyPillState(pill, prev);
      flash(pill, false);
      pill.setAttribute("data-tooltip", "Network error: " + err);
      return false;
    }
  }

  function enterEditMode(pill) {
    if (pill.dataset.editing === "1") return;
    pill.dataset.editing = "1";

    var prev = pill.dataset.original || "";
    var pillDisplay = pill.style.display;
    pill.style.display = "none";

    var select = document.createElement("select");
    select.className = "status-edit-select";
    select.setAttribute("aria-label", pill.getAttribute("aria-label") || "");

    var seen = false;
    EDITABLE_OPTIONS.forEach(function (opt) {
      var o = document.createElement("option");
      o.value = opt;
      o.textContent = opt;
      if (prev.toLowerCase() === opt) {
        o.selected = true;
        seen = true;
      }
      select.appendChild(o);
    });
    if (!seen && prev) {
      var custom = document.createElement("option");
      custom.value = prev;
      // Truncate the displayed text — a long custom status like
      // "phase 0 complete + skills survey complete; **spec retired**"
      // would otherwise widen the <select> past its cell. The full
      // value is still in option.value so the form submits correctly,
      // and the title shows it on hover.
      var label = prev.length > 12 ? prev.substring(0, 10) + "…" : prev;
      custom.textContent = label + " (current)";
      custom.title = prev;
      custom.selected = true;
      select.appendChild(custom);
    }

    pill.parentNode.insertBefore(select, pill);

    var done = false;
    async function finish(commit) {
      if (done) return;
      done = true;
      var next = select.value;
      select.remove();
      pill.style.display = pillDisplay;
      pill.dataset.editing = "";
      if (commit && next !== prev) {
        await submitChange(pill, prev, next);
      }
      pill.focus();
    }

    select.addEventListener("change", function () {
      finish(true);
    });
    // Blur CANCELS — does not commit. Previously this committed on any
    // blur (commit=true), which fired PUT /api/specs/.../status whenever
    // focus left the select for any reason: alt-tab, screen-reader
    // navigation, an a11y-tree traversal by an automated tool. Browsing
    // the Specs page with a snapshotting/accessibility tool was enough
    // to flip status across multiple specs without any user click. See
    // docs/specs/ops-specs-features/phase4-findings.md Finding 0.
    //
    // Cancel-on-blur is the standard form pattern: only an explicit
    // `change` event saves; clicking anywhere else closes the dropdown
    // without writing.
    select.addEventListener("blur", function () {
      finish(false);
    });
    select.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        finish(false);
      }
    });

    select.focus();
    if (typeof select.showPicker === "function") {
      try {
        select.showPicker();
      } catch (_) {
        /* fall back to focus only */
      }
    }
  }

  function attach(pill) {
    pill.addEventListener("click", function () {
      enterEditMode(pill);
    });
    pill.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        enterEditMode(pill);
      }
    });
  }

  // Relative-time rendering for the Last-modified column.
  // Server provides ISO 8601 UTC in data-mtime; we render "2h ago"
  // style strings client-side so the user's local clock is the
  // reference. data-tooltip already holds the absolute string for
  // hover via the CSS tooltip layer.
  function relativeTime(isoString) {
    var then = Date.parse(isoString);
    if (isNaN(then)) return "?";
    var now = Date.now();
    var secs = Math.round((now - then) / 1000);
    if (secs < 0) return "in the future";
    if (secs < 60) return "just now";
    var mins = Math.round(secs / 60);
    if (mins < 60) return mins + "m ago";
    var hours = Math.round(mins / 60);
    if (hours < 24) return hours + "h ago";
    var days = Math.round(hours / 24);
    if (days < 14) return days + "d ago";
    var weeks = Math.round(days / 7);
    if (weeks < 9) return weeks + "w ago";
    var months = Math.round(days / 30);
    if (months < 18) return months + "mo ago";
    var years = (days / 365).toFixed(1);
    return years + "y ago";
  }

  // Browser-localized absolute timestamp for the tooltip — replaces
  // the raw ISO string the server emits with something readable in
  // the user's locale, e.g. "May 12, 2026, 3:05 PM" in en-US or
  // "12. Mai 2026 um 15:05" in de-DE. Falls back to the raw ISO if
  // parsing fails.
  function localizedAbsolute(isoString) {
    var d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    try {
      return d.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch (_) {
      return d.toLocaleString();
    }
  }

  function renderMtime(el) {
    var iso = el.getAttribute("data-mtime");
    if (!iso) return;
    var rel = relativeTime(iso);
    var abs = localizedAbsolute(iso);
    el.textContent = rel;
    // Browser-localized absolute timestamp for the hover tooltip
    // (replaces the raw ISO that the server emitted).
    el.setAttribute("data-tooltip", abs);
    // Keep aria-label in sync with the visible relative time so screen
    // readers announce "Updated 2h ago" instead of the raw ISO string.
    // The absolute timestamp remains accessible via the datetime
    // attribute on <time> and the data-tooltip on hover.
    el.setAttribute("aria-label", "Updated " + rel + " (" + abs + ")");
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".status-pill-editable").forEach(attach);
    document.querySelectorAll(".spec-mtime[data-mtime]").forEach(renderMtime);
  });
})();
