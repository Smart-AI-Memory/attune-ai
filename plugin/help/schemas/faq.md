---
type: faq
description: >
  FAQ template schema for question-answer pairs.
  Dynamically maintained from error patterns,
  support queries, and common follow-up questions.
required_fields:
  - name
  - question
  - answer
optional_fields:
  - related_topics
  - tags
  - source
---

# FAQ: {name}

## Question

{question}

Natural language question as a user would phrase it.

## Answer

{answer}

Concise, actionable answer. May include code examples
or link to a Task template for complex procedures.

## Related Topics

{related_topics}

Cross-links to other templates by type:

- Task: step-by-step procedure if the answer is complex
- Error: the error this FAQ addresses
- Reference: API or config details
- Tip: best practice related to the question
