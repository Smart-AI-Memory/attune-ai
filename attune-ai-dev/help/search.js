// Client-side help search over the static index (no server).
(function () {
  var input = document.getElementById("help-search");
  var results = document.getElementById("search-results");
  if (!input || !results) return;
  var index = [];
  fetch("/help/search-index.json").then(function (r) { return r.json(); })
    .then(function (data) { index = data; });
  function tokens(s) { return s.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean); }
  function render(hits) {
    results.innerHTML = hits.map(function (h) {
      return '<li><a href="' + h.url + '"><strong>' + h.title +
        '</strong> <span class="r-kind">' + h.feature + " / " + h.kind +
        '</span><span class="r-snip">' + (h.snippet || "") + "</span></a></li>";
    }).join("");
  }
  input.addEventListener("input", function () {
    var q = tokens(input.value);
    if (!q.length) { results.innerHTML = ""; return; }
    var scored = index.map(function (it) {
      var feat = (it.feature || "").toLowerCase();
      var title = (it.title || "").toLowerCase();
      var kw = (it.keywords || "").toLowerCase();
      // Weight: feature-name match >> title match > body keyword.
      var score = q.reduce(function (acc, t) {
        return acc + (feat.indexOf(t) >= 0 ? 3 : 0) +
          (title.indexOf(t) >= 0 ? 2 : 0) + (kw.indexOf(t) >= 0 ? 1 : 0);
      }, 0);
      return { it: it, score: score };
    }).filter(function (x) { return x.score > 0; });
    // Sort by score desc, then prefer concept/quickstart kinds, then title.
    var order = { concept: 0, quickstart: 1, task: 2, reference: 3 };
    scored.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      var ak = order[a.it.kind] === undefined ? 9 : order[a.it.kind];
      var bk = order[b.it.kind] === undefined ? 9 : order[b.it.kind];
      return ak - bk;
    });
    render(scored.slice(0, 20).map(function (x) { return x.it; }));
  });
})();
