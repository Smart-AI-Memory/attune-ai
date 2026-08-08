# redis-config-truth — tasks

**Status:** ladder drafted (2026-08-08) — awaiting chair review;
execution starts on a fresh chair go. Grounding: decisions.md D3
(15 files / 42 env reads; two existing resolver candidates).

Sequencing follows the roundtable's ratified order: resolver →
visibility → tests → migrations. T1 contains a chair checkpoint
(canonical home). Each task ships as its own PR with tests.

```xml
<task id="rct-1" name="canonical-resolver">
  <objective>
    Rule the canonical home for Redis connection resolution, then
    implement resolve_redis_connection() there with the R1
    five-step precedence (explicit-creds URL; REDIS_URL +
    REDIS_PASSWORD/REDIS_USER merge; PUBLIC/PRIVATE variants;
    host/port/db components; localhost default).
  </objective>
  <context>
    <existing-code path="src/attune/redis_config.py">
      Deprecated but comprehensive resolver (URL override,
      cloud/local, SSL, sentinel, mock). Docstring designates
      attune_redis.config.RedisPluginConfig as successor.
    </existing-code>
    <existing-code path="attune_redis/config.py">
      RedisPluginConfig — the designated successor, plugin-scoped.
    </existing-code>
    <existing-code path="src/attune/memory/config.py">
      Checks REDIS_URL / REDIS_PUBLIC_URL / REDIS_PRIVATE_URL
      today; requirements originally assumed the resolver lands
      here.
    </existing-code>
  </context>
  <files-to-create>
    <file path="(ruled home)/resolve_redis_connection">
      The single resolver + a dataclass/tuple result carrying URL,
      redacted-URL, source-map (which env var supplied each part).
      CHAIR CHECKPOINT: present a one-page audit of the three
      candidate homes with a recommendation BEFORE implementing.
    </file>
  </files-to-create>
  <validation>
    <check>Unit tests pin all five precedence steps, including the
      incident shape (password-less URL + REDIS_PASSWORD set).</check>
    <check>Conflicting settings raise an actionable diagnostic,
      not a silent pick.</check>
    <check>Redacted rendering never contains the password.</check>
  </validation>
  <risks>
    <risk severity="medium">Choosing a home that forces an import
      direction violation (attune_redis importing attune.memory or
      vice versa) — the audit must check the dependency
      graph.</risk>
  </risks>
</task>

<task id="rct-2" name="degradation-classification">
  <objective>
    R3: classify Redis failures (degraded_auth / degraded_connectivity
    / disabled / healthy) at the resolver-consumer seam; auth and
    invalid-config classes warn ONCE per session (structured log +
    SessionStart notice or health-snapshot line); server-absent
    stays silent; P15 never-block preserved.
  </objective>
  <context>
    <existing-code path="src/attune/memory/features.py">
      MemoryFeatures.check_redis() — the fail-open probe most
      consumers gate on today.
    </existing-code>
  </context>
  <files-to-modify>
    <file path="(resolver home + features.py)">
      <change location="failure paths">
        BEFORE: all failures collapse to silent mock-fallback
        AFTER: classified state, loud-once on non-self-healing
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>AuthenticationError produces exactly ONE visible notice
      per session (test both first and second call).</check>
    <check>ConnectionRefused produces none (silent degrade).</check>
    <check>No workflow blocks in any failure class.</check>
  </validation>
  <risks>
    <risk severity="low">Notice spam if "session" scoping is wrong —
      pin the once-per-process semantics in a test.</risk>
  </risks>
</task>

<task id="rct-3" name="doctor-diagnostic">
  <objective>
    R2: extend redis_health_check (and/or attune memory doctor)
    to report the redacted effective config: which env vars
    resolved, resulting URL shape, AUTH outcome, entry-point
    backend selected and why.
  </objective>
  <context>
    <existing-code path="src/attune/mcp (redis_health_check)">
      Existing MCP health tool — the natural surface.
    </existing-code>
  </context>
  <validation>
    <check>Doctor output on the incident shape names REDIS_URL as
      password-less and REDIS_PASSWORD as present-but-unmerged
      (pre-fix) or merged (post-fix).</check>
    <check>Output contains no secret material (grep the rendered
      text for the test password).</check>
  </validation>
  <risks>
    <risk severity="low">Diagnostic drift from resolver internals —
      derive the report FROM the resolver's source-map, never
      re-read env vars independently.</risk>
  </risks>
</task>

<task id="rct-4" name="consumer-migration">
  <objective>
    Migrate all direct env readers to the resolver — the
    grep-derived set (15 files incl. roundtable/board.py,
    roundtable/routine.py, memory/config.py, memory/features.py,
    redis_bootstrap.py, redis_auto_detect.py, recall_redis.py,
    recall_digest.py, unified.py, backend_init_mixin.py,
    cross_session.py, diagnosis/priors.py, attune_redis/config.py,
    attune_redis/signals.py, redis_config.py) — and add the AC
    drift-guard: a test failing on any direct
    os.environ.get("REDIS_URL")-family read outside the resolver
    module (allowlist seeded empty).
  </objective>
  <validation>
    <check>Drift-guard test proves it fires: a planted violation in
      a tmp module is caught.</check>
    <check>The R4 incident shape connects through EVERY migrated
      consumer (parametrized where practical).</check>
    <check>Full unit suite green; keyless CI semantics unchanged.</check>
  </validation>
  <risks>
    <risk severity="medium">attune_redis is a separate bundled
      package — import direction from the ruled resolver home must
      be validated in rct-1's audit before this task starts.</risk>
    <risk severity="medium">Behavior change for consumers that
      today IGNORE REDIS_PASSWORD: they start authenticating.
      That is the point, but staging/CI environments with stale
      passwords will surface — release-note it.</risk>
  </risks>
</task>

<task id="rct-5" name="requirepass-regression-lane">
  <objective>
    R4: a non-mocked round trip against a requirepass server —
    password-less REDIS_URL + REDIS_PASSWORD set resolves to an
    authenticated connection (skip cleanly when no local Redis or
    no auth configured).
  </objective>
  <validation>
    <check>Lane passes against the local requirepass server.</check>
    <check>Lane skips (not fails) on keyless CI and on hosts
      without Redis.</check>
  </validation>
  <risks>
    <risk severity="low">Machine-local test class — follow the
      session_hydrate_fail_open precedent (run where real, skip
      elsewhere).</risk>
  </risks>
</task>
```
