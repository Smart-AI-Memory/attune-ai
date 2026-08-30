# Fix MCP Apps transport

<task id="1" name="fix-mcp-apps-transport">
  <status>
    Implementation, focused tests, broader MCP regression, package build,
    source-tree stdio probes, and installed-wheel stdio probes pass.
    Different-model boundary review remains before promotion.
  </status>
  <objective>
    Project the released attune-forms 0.10.0 MCP Apps transport through
    attune-ai's existing Fix preview tool without moving or weakening the
    server-owned revision, nonce, contract-hash, or collector boundary.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      The low-level MCP adapter lists tools/resources and serializes the
      application result. It currently has no resources/read handler and
      does not negotiate MCP Apps tool metadata.
    </existing-code>
    <existing-code path="src/attune/mcp/tool_schemas.py">
      fix_workspace_preview and fix_workspace_collect_action already expose
      the validated server-side preview/collector contract.
    </existing-code>
    <constraint>
      Only clients advertising io.modelcontextprotocol/ui with the released
      HTML MIME profile receive tool metadata. Unsupported clients retain the
      current content-only HTML/Markdown result.
    </constraint>
    <constraint>
      The shared ui:// resource comes from attune-forms; attune-ai must not
      copy or fork its HTML bridge.
    </constraint>
    <constraint>
      The MCP App posts the full authority-bound response to
      fix_workspace_collect_action. The browser surface never authorizes or
      executes Fix.
    </constraint>
  </context>

  <files-to-modify>
    <file path="pyproject.toml">Raise the attune-forms floor to 0.10.0.</file>
    <file path="uv.lock">Resolve the released 0.10.0 wheel and hashes.</file>
    <file path="src/attune/mcp/server.py">
      Negotiate tool metadata, register/read the shared UI resource,
      advertise the extension, and return the response collector descriptor.
    </file>
    <file path="tests/unit/mcp/test_request_handler.py">
      Pin metadata negotiation, resource listing/reading, and fallback.
    </file>
    <file path="tests/unit/mcp/test_server_handlers.py">
      Pin initialization options and stdio delegation.
    </file>
    <file path="tests/unit/elicitation/test_fix_workspace.py">
      Pin the real Fix preview's response collector descriptor.
    </file>
    <file path="CHANGELOG.md">Document negotiated MCP Apps rendering and fallback.</file>
  </files-to-modify>

  <validation>
    <check>Unsupported/no-context tool listing contains no MCP Apps metadata.</check>
    <check>Advertised UI capability adds metadata only to fix_workspace_preview.</check>
    <check>The listed ui:// resource reads the exact attune-forms HTML/MIME payload.</check>
    <check>Initialization advertises the stable extension and MIME profile.</check>
    <check>The live application server returns collect_mode=response and preserves execution_started=false.</check>
    <check>Focused tests, changed-file lint/format, package build, and isolated stdio protocol smoke pass.</check>
  </validation>

  <risks>
    <risk>Client capability objects may be absent outside request context; negotiation must fail closed to no metadata.</risk>
    <risk>Changing the generic tool return shape could break legacy clients; keep the existing content serialization path.</risk>
  </risks>
</task>
