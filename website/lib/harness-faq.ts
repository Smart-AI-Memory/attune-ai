import { HARNESS_PUBLISHED_VERSION, HARNESS_INSTALL_COMMAND } from '@/lib/harness-release';

// Shared current FAQ; historical setup remains in the versioned guides.
export const HARNESS_FAQ_ITEMS = [
  {
    question: 'What is Attune Harness?',
    answer:
      'Attune Harness is an open-source toolkit for AI-assisted engineering. It helps you define scoped work, record permitted actions, and inspect the results and the checks behind them.',
  },
  {
    question: 'Can I use it for specification development?',
    answer:
      'Work with your agent to develop requirements, constraints and acceptance criteria, then agree with the scope before authorizing execution. Harness supports planning, building, repair and test journeys. Use the documented participant paths and review each workflow’s requirements and qualification limits.',
  },
  {
    question: 'How do I get started with Harness?',
    answer:
      `Use the Get started guide for published Harness ${HARNESS_PUBLISHED_VERSION}. With Python 3.12 or later, install it in a managed environment using ${HARNESS_INSTALL_COMMAND}, then confirm the version and run a local example. Redis and Voyage are optional integrations; Voyage calls need an API key and spending permission.`,
  },
  {
    question: 'What does a receipt tell me?',
    answer:
      'A receipt records the task outcome, captured output and check evidence. Look for independent checks alongside the output, and keep unchecked behavior separate. A passing check establishes only what that check assessed; it does not guarantee a correct change or a reliable model.',
  },
  {
    question: 'Which agents and models can I use with Attune Harness?',
    answer:
      'Harness has documented setup paths for Claude Code and Codex. Models and authentication depend on the host and participants configured for the task. Installing the Python package does not install agent plugins or skills. Native planning and building retain their documented qualification limits. Browser forms support draft intake, preview and intent approval; browser build dispatch is not available. Intent approval is separate from permission to execute paid work.',
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
