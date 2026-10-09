// Shared by Docs and the FAQ page; grounded in the released 1.3.0 guides.
export const HARNESS_FAQ_ITEMS = [
  {
    question: 'What is Attune Harness?',
    answer:
      'Attune Harness is an open-source toolkit for AI-assisted engineering. It helps you define scoped work, record permitted actions, and inspect the results and the checks behind them.',
  },
  {
    question: 'Can I use it for specification development?',
    answer:
      'Work with your agent to develop requirements, constraints and acceptance criteria, then agree with the scope before authorizing execution. Harness supports planning, building, repair and test journeys. Native planning and building are experimental in 1.3.0; use the documented agent paths and review their limits.',
  },
  {
    question: 'How do I get started with Harness?',
    answer:
      "Follow the Harness Quick Start: create a separate Python 3.10+ environment, install attune-harness[all]==1.3.0, confirm the version and run the local example. Redis use needs a running service; Voyage retrieval needs an API key and makes paid calls.",
  },
  {
    question: 'What does a receipt tell me?',
    answer:
      'A receipt records the task outcome, captured output and check evidence. Look for independent checks alongside the output, and keep unchecked behavior separate. A passing check establishes only what that check assessed; it does not guarantee a correct change or a reliable model.',
  },
  {
    question: 'Which agents and models can I use with Attune Harness?',
    answer:
      'Harness has documented setup paths for Claude Code and Codex. Models and authentication depend on the host and participants configured for the task. Installing the Python package does not install agent plugins or skills. Native planning and building are experimental in 1.3.0. Browser forms in that release support draft intake, preview and intent approval; browser build dispatch is not available. Intent approval is separate from permission to execute paid work.',
  },
  {
    question: 'Does Harness replace Attune AI?',
    answer:
      'Harness runs without Attune AI, but does not yet replace every Attune AI workflow. Keep the two packages in separate environments and check the migration guide before changing an existing setup. The earlier Attune AI references remain available for existing users.',
  },
  {
    question: 'Does Harness keep all my data local?',
    answer:
      'Harness can read local memory and keep receipts on disk. Redis may run locally or remotely, depending on your setup. Authorized model calls or Voyage retrieval can send selected task context, source text or queries to a provider. Review the chosen workflow, destination and permissions before execution.',
  },
] as const;
