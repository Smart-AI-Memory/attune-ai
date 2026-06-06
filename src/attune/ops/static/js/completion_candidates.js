// Specs page: "Ready to close?" completion-candidates section.
//
// Loads on page load when the server-rendered shell
// (#completion-candidates) is present. Fetches candidates from
// /api/specs/completion-candidates, renders one card per candidate,
// and wires Confirm / Dismiss actions to the corresponding endpoints.
//
// On Confirm success: removes the card and updates the main specs
// table row's pill to "cpl" (complete). On Dismiss success: removes
// the card. On any failure: renders an inline error banner on the
// card; the card stays visible so the user can retry.
//
// Spec: docs/specs/ops-specs-completion-candidates/ (T5).
(function () {
  "use strict";

  var ROOT_ID = "completion-candidates";
  var LIST_ID = "cc-list";
  var COUNT_ID = "cc-count";
  var ENDPOINT = "/api/specs/completion-candidates";
  var DISMISS_TOOLTIP =
    "Hidden for 14 days. Re-surfaces immediately if a referenced PR " +
    "merges or tasks.md changes.";

  function fetchJson(url, options) {
    return fetch(url, options || {}).then(function (response) {
      if (!response.ok) {
        var err = new Error("HTTP " + response.status);
        err.status = response.status;
        return response
          .json()
          .catch(function () {
            return {};
          })
          .then(function (body) {
            err.detail = body && body.detail ? body.detail : null;
            throw err;
          });
      }
      return response.json();
    });
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === "class") {
          node.className = attrs[k];
        } else if (k === "text") {
          node.textContent = attrs[k];
        } else if (k.indexOf("data-") === 0 || k.indexOf("aria-") === 0) {
          node.setAttribute(k, attrs[k]);
        } else {
          node[k] = attrs[k];
        }
      });
    }
    (children || []).forEach(function (child) {
      if (child) node.appendChild(child);
    });
    return node;
  }

  function renderCard(candidate) {
    var evidenceItems = (candidate.evidence || []).map(function (e) {
      return el("li", { text: e });
    });
    var confirm = el("button", {
      class: "btn btn-confirm",
      type: "button",
      text: "Confirm complete",
    });
    var dismiss = el("button", {
      class: "btn btn-dismiss",
      type: "button",
      text: "Dismiss",
      "data-tooltip": DISMISS_TOOLTIP,
    });

    var banner = el("div", {
      class: "candidate-error",
      hidden: true,
      role: "alert",
    });

    var card = el(
      "li",
      {
        class: "candidate-card",
        "data-slug": candidate.slug,
        "data-snapshot-hash": candidate.snapshot_hash,
      },
      [
        el("div", { class: "candidate-head" }, [
          el("a", {
            class: "link candidate-slug",
            href: "/specs/" + encodeURIComponent(candidate.slug),
            text: candidate.slug,
          }),
          el("span", {
            class: "status-pill chip-ok candidate-current",
            text: candidate.current_status,
          }),
        ]),
        el("ul", { class: "candidate-evidence" }, evidenceItems),
        el("div", { class: "candidate-actions" }, [confirm, dismiss]),
        banner,
      ]
    );

    confirm.addEventListener("click", function () {
      onConfirm(card, candidate, banner, [confirm, dismiss]);
    });
    dismiss.addEventListener("click", function () {
      onDismiss(card, candidate, banner, [confirm, dismiss]);
    });
    return card;
  }

  function showError(banner, message) {
    banner.textContent = message;
    banner.hidden = false;
  }

  function setBusy(buttons, busy) {
    buttons.forEach(function (b) {
      b.disabled = busy;
    });
  }

  function flipMainTablePill(slug) {
    // After a successful Confirm, mirror the status flip into the main
    // specs table's decisions-phase pill so the page reflects reality
    // without a reload. Best-effort: if the row or pill isn't found
    // (e.g. layout changed), we silently no-op rather than fail the
    // candidate removal.
    var row = document.querySelector('tr[data-slug="' + cssEscape(slug) + '"]');
    if (!row) return;
    var cell = row.querySelector('td[data-phase="decisions"]');
    if (!cell) return;
    var pill = cell.querySelector(".status-pill");
    if (!pill) return;
    pill.classList.remove("chip-muted", "chip-warn", "chip-custom");
    pill.classList.add("chip-ok");
    pill.setAttribute("data-original", "complete");
    pill.setAttribute("data-tooltip", "complete");
    var code = pill.querySelector(".status-code");
    if (code) code.textContent = "cpl";
  }

  function cssEscape(value) {
    // Avoid window.CSS.escape (not in older browsers we care about).
    // Slugs are validated server-side to [a-z0-9-]+, so just guard
    // backslash and quote characters as a belt-and-suspenders measure.
    return String(value).replace(/(["\\])/g, "\\$1");
  }

  function onConfirm(card, candidate, banner, buttons) {
    setBusy(buttons, true);
    banner.hidden = true;
    var url =
      "/api/specs/" + encodeURIComponent(candidate.slug) + "/decisions/status";
    fetchJson(url, {
      method: "PUT",
      headers: attuneClientHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ status: "complete" }),
    })
      .then(function () {
        flipMainTablePill(candidate.slug);
        removeCard(card);
      })
      .catch(function (err) {
        setBusy(buttons, false);
        var msg =
          err && err.detail
            ? "Confirm failed: " + err.detail
            : "Confirm failed. Try again or refresh.";
        showError(banner, msg);
      });
  }

  function onDismiss(card, candidate, banner, buttons) {
    setBusy(buttons, true);
    banner.hidden = true;
    var url =
      "/api/specs/" +
      encodeURIComponent(candidate.slug) +
      "/completion-candidates/dismiss";
    fetchJson(url, {
      method: "POST",
      headers: attuneClientHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ snapshot_hash: candidate.snapshot_hash }),
    })
      .then(function () {
        removeCard(card);
      })
      .catch(function (err) {
        setBusy(buttons, false);
        var msg =
          err && err.detail
            ? "Dismiss failed: " + err.detail
            : "Dismiss failed. Try again or refresh.";
        showError(banner, msg);
      });
  }

  function removeCard(card) {
    var list = document.getElementById(LIST_ID);
    var section = document.getElementById(ROOT_ID);
    var count = document.getElementById(COUNT_ID);
    if (!list || !section) return;
    card.parentNode.removeChild(card);
    var remaining = list.children.length;
    if (count) count.textContent = String(remaining);
    if (remaining === 0) {
      // Hide the whole section when empty so the page doesn't show a
      // dangling "Ready to close? 0" header.
      section.hidden = true;
    }
  }

  function renderCandidates(candidates) {
    var list = document.getElementById(LIST_ID);
    var section = document.getElementById(ROOT_ID);
    var count = document.getElementById(COUNT_ID);
    if (!list || !section) return;
    list.innerHTML = "";
    candidates.forEach(function (c) {
      list.appendChild(renderCard(c));
    });
    if (count) count.textContent = String(candidates.length);
    section.hidden = candidates.length === 0;
  }

  function load() {
    var section = document.getElementById(ROOT_ID);
    if (!section) return; // feature disabled server-side; nothing to do.
    fetchJson(ENDPOINT)
      .then(function (body) {
        if (!body || !body.enabled) return;
        renderCandidates(body.candidates || []);
      })
      .catch(function () {
        // Silent failure: the section stays hidden. Logging via the
        // existing dashboard surface is out-of-scope for V1.
      });
  }

  // Expose for tests / debugging. Not strictly necessary for runtime.
  window.__attuneCompletionCandidates = {
    load: load,
    renderCandidates: renderCandidates,
    onConfirm: onConfirm,
    onDismiss: onDismiss,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", load);
  } else {
    load();
  }
})();
