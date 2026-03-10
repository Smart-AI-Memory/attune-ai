# LinkedIn Post: Attune AI v4.0 — Agent SDK

---

**Your AI security audit just got a team.**

One model can't be a security expert, a performance
specialist, and a documentation reviewer at the same time.
So we stopped asking it to be.

Attune AI v4.0 gives every workflow its own team of Claude
subagents. A security audit now runs 4 specialists in
parallel:

--- CODE START ---
attune workflow run security-audit
--- CODE END ---

Behind the scenes:
- Dependency checker scans your requirements
- Injection detector reviews your code paths
- Secrets scanner catches leaked credentials
- Report writer synthesizes everything

Same command you already know. Same output format.
The only difference: depth.

15 workflows now have Agent SDK adapters. Each one
assembles 2-6 specialist subagents depending on the task.

The best part: zero configuration.

If you have claude-agent-sdk installed, you get the
multi-agent version. If not, you get the single-model
version. Attune picks the right one automatically.

--- CODE START ---
pip install attune-ai[developer]
pip install claude-agent-sdk
--- CODE END ---

One install and your next run uses the full agent team.

Other things that shipped in v4.0:
- Smart workflow routing with transparent SDK/API fallback
- Deduplicated workflow listing with [SDK]/[API] tags
- Bug fixes across 18 modules
- 11,800+ tests at 80% coverage

Full blog post + changelog:
https://github.com/Smart-AI-Memory/attune-ai

What workflows do you wish had specialist AI teams?

#AIDevelopment #ClaudeAI #AgentSDK #DeveloperTools
#Python #OpenSource

---

## Alternative Hooks

**Version B (question lead):**
Would you trust one person to do your security audit,
performance review, and documentation check all at once?

Then why trust one AI model to do it?

Attune AI v4.0 gives each workflow its own team of Claude
subagents...

**Version C (data lead):**
15 workflows. Up to 6 subagents each. All running in
parallel.

That's what we shipped in Attune AI v4.0...

**Version D (builder's perspective):**
I spent the last month turning single-model workflows
into multi-agent teams.

The insight that drove it: a security audit and a code
review shouldn't use the same approach. One needs a
dependency checker. The other needs a style analyzer.
Both need a report writer. None of them need to wait
for each other...
