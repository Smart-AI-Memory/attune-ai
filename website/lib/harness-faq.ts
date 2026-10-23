import { HARNESS_PUBLISHED, HARNESS_RELEASE_NOTICE, HARNESS_VERSION } from '@/lib/harness-help/release';

// Shared by Docs and FAQ; release identity is maintained with the Help Center.
export const HARNESS_FAQ_ITEMS = [
  {
    question: 'What is Attune Harness?',
    answer:
      'Attune Harness is an open-source toolkit for AI-assisted engineering. It helps you define scoped work, record permitted actions, and inspect the results and the checks behind them.',
  },
  {
    question: 'Can I use it for specification development?',
    answer:
      `Work with your agent to develop requirements, constraints and acceptance criteria, then agree on the scope before authorizing execution. Harness supports planning, building, repair and test journeys. Native planning and building remain experimental in ${HARNESS_VERSION}; use the documented agent paths and review their limits.`,
  },
  {
    question: 'How do I get started with Harness?',
    answer:
      `Open the Harness Help Center and choose a goal or the ${HARNESS_VERSION} installation guide. ${HARNESS_RELEASE_NOTICE} ${HARNESS_PUBLISHED ? "Install the managed CLI with uv tool install attune-harness==" + HARNESS_VERSION + "; Python API use needs a separate Python 3.10+ environment." : "Use the published 1.5.0 guide for an installation today."} Confirm the environment and run the local example. Redis needs a running service; Voyage retrieval needs an API key and authorized paid calls.`,
  },
  {
    question: 'What does a receipt tell me?',
    answer:
      'A receipt records the task outcome, captured output and check evidence. Look for independent checks alongside the output, and keep unchecked behavior separate. A passing check establishes only what that check assessed; it does not guarantee a correct change or a reliable model.',
  },
  {
    question: 'Which agents and models can I use with Attune Harness?',
    answer:
      'Harness has documented setup paths for Claude Code and Codex. Models and authentication depend on the host and participants configured for the task. Installing the Python package does not install agent plugins or skills. Native planning and building remain experimental. Browser forms support draft intake, preview and intent approval; browser build dispatch is not available. Intent approval is separate from permission to execute paid work.',
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
