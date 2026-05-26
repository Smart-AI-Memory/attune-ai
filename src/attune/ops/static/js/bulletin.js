/* Multi-actor bulletin polling — renders the "Now running across
   actors" strip on the Workflows page.

   Polls /api/bulletin/active every BULLETIN_POLL_MS and rewrites the
   chips container. Hides the whole section when zero entries are
   active so single-actor sessions don't see chrome they don't need.

   The strip is intentionally additive — it shows runs from the
   current actor too, which doubles as a "the bulletin is alive"
   confirmation. Filtering "self" is a future refinement once we
   expose the dashboard's own actor_id to the page.

   See docs/specs/multi-actor-bulletin/ for the data model.
*/

(function () {
  "use strict";

  var BULLETIN_POLL_MS = 5000;
  var BULLETIN_ENDPOINT = "/api/bulletin/active";

  var section = document.getElementById("bulletin-strip");
  var chipsEl = document.getElementById("bulletin-strip-chips");
  var countEl = document.getElementById("bulletin-strip-count");

  if (!section || !chipsEl || !countEl) {
    // Page doesn't have the strip — nothing to do.
    return;
  }

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function ageSeconds(iso) {
    if (!iso) return null;
    var parsed = Date.parse(iso);
    if (isNaN(parsed)) return null;
    return Math.max(0, Math.round((Date.now() - parsed) / 1000));
  }

  function ageLabel(iso) {
    var s = ageSeconds(iso);
    if (s == null) return "";
    if (s < 60) return s + "s ago";
    if (s < 3600) return Math.round(s / 60) + "m ago";
    return Math.round(s / 3600) + "h ago";
  }

  function renderChip(entry) {
    // Stale = heartbeat older than 60s (the server filters >90s; the
    // 60-90s window shows muted to telegraph "this actor may be gone").
    var age = ageSeconds(entry.last_heartbeat);
    var staleClass = age != null && age > 60 ? " bulletin-chip-stale" : "";
    var scope = entry.scope ? " — " + escapeHtml(entry.scope) : "";
    var tooltip =
      "Actor: " +
      escapeHtml(entry.actor_id) +
      "\nKind: " +
      escapeHtml(entry.actor_kind) +
      "\nStarted: " +
      escapeHtml(entry.started_at) +
      "\nLast heartbeat: " +
      escapeHtml(entry.last_heartbeat) +
      " (" +
      escapeHtml(ageLabel(entry.last_heartbeat)) +
      ")";
    return (
      '<span class="bulletin-chip' +
      staleClass +
      '" data-tooltip="' +
      tooltip +
      '">' +
      '<span class="bulletin-chip-actor">' +
      escapeHtml(entry.actor_id) +
      "</span>" +
      '<span class="bulletin-chip-workflow"> · ' +
      escapeHtml(entry.workflow) +
      "</span>" +
      '<span class="bulletin-chip-scope">' +
      scope +
      "</span>" +
      "</span>"
    );
  }

  function render(entries) {
    if (!entries || entries.length === 0) {
      section.hidden = true;
      chipsEl.innerHTML = "";
      countEl.textContent = "0";
      return;
    }
    countEl.textContent = String(entries.length);
    chipsEl.innerHTML = entries.map(renderChip).join("");
    section.hidden = false;
  }

  function poll() {
    fetch(BULLETIN_ENDPOINT, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    })
      .then(function (resp) {
        if (!resp.ok) throw new Error("bulletin: HTTP " + resp.status);
        return resp.json();
      })
      .then(function (body) {
        render(body.entries || []);
      })
      .catch(function (err) {
        // Best-effort: log and try again next tick. The bulletin is
        // advisory; an outage doesn't break the page.
        if (window.console && console.warn) console.warn(err);
      });
  }

  // Initial fetch + recurring poll.
  poll();
  setInterval(poll, BULLETIN_POLL_MS);
})();
