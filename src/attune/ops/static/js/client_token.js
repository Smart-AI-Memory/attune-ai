// Per-process client-token helper for the ops dashboard.
//
// Reads the token from the <meta name="attune-client-token"> tag that
// base.html renders once at page load, and exposes a header-merger that
// every mutating fetch() echoes as the X-Attune-Client header. The
// server's require_client_token dependency 403s any mutating request
// without it — blocking drive-by fetches from clients that never
// loaded the page. See docs/specs/ops-mutating-endpoint-auth/.
(function () {
  var meta = document.querySelector('meta[name="attune-client-token"]');
  var TOKEN = meta ? meta.getAttribute("content") || "" : "";

  // Merge the client token into a headers object (or a fresh one).
  // Use on every mutating fetch: fetch(url, { method: "POST",
  // headers: attuneClientHeaders({ "Content-Type": "application/json" }) }).
  window.attuneClientHeaders = function (extra) {
    var headers = Object.assign({}, extra || {});
    headers["X-Attune-Client"] = TOKEN;
    return headers;
  };
})();
