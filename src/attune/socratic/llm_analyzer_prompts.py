"""LLM prompt templates for goal analysis.

Defines the prompt templates used by LLMGoalAnalyzer for
goal analysis, question refinement, and agent recommendation.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

GOAL_ANALYSIS_PROMPT = """You are an expert at understanding user requirements for software development workflows.

Analyze the following goal statement and extract structured information:

<goal>
{goal}
</goal>

Provide your analysis in the following JSON format:
{{
    "intent": "A clear, concise statement of what the user wants to achieve",
    "domain": "One of: code_review, security, testing, documentation, performance, refactoring, general",
    "confidence": 0.0 to 1.0 indicating how well you understand the goal,
    "ambiguities": ["List of unclear aspects that need clarification"],
    "assumptions": ["List of assumptions you're making about their needs"],
    "constraints": ["Any constraints mentioned or implied"],
    "keywords": ["Important technical keywords extracted"],
    "suggested_agents": ["List of agent types that would help: security_reviewer, code_quality_reviewer, performance_analyzer, test_generator, documentation_writer, style_enforcer"],
    "suggested_questions": [
        {{
            "id": "unique_id",
            "question": "The clarifying question to ask",
            "type": "single_select or multi_select or text",
            "options": ["option1", "option2"] // for select types
        }}
    ]
}}

Focus on:
1. Identifying the core intent behind potentially vague statements
2. Detecting missing information that would affect implementation
3. Suggesting specific questions that would help refine the requirements
4. Recommending appropriate agent types for the task

Respond ONLY with valid JSON, no additional text."""


QUESTION_REFINEMENT_PROMPT = """Based on the user's goal and their previous answers, generate the next round of clarifying questions.

<goal>
{goal}
</goal>

<previous_answers>
{previous_answers}
</previous_answers>

<current_requirements>
{requirements}
</current_requirements>

<remaining_ambiguities>
{ambiguities}
</remaining_ambiguities>

Generate 2-4 focused questions that will help clarify the remaining ambiguities.
Prioritize questions that will have the biggest impact on the workflow design.

Respond in JSON format:
{{
    "questions": [
        {{
            "id": "unique_id",
            "question": "The clarifying question",
            "type": "single_select or multi_select or text or boolean",
            "options": ["option1", "option2"],
            "category": "technical or quality or scope or preferences",
            "priority": 1 to 5 (5 being most important)
        }}
    ],
    "confidence_after_answers": 0.0 to 1.0,
    "ready_to_generate": true/false,
    "reasoning": "Brief explanation of why these questions are important"
}}

Respond ONLY with valid JSON."""


AGENT_RECOMMENDATION_PROMPT = """Based on the user's requirements, recommend the optimal agent configuration.

<goal>
{goal}
</goal>

<requirements>
{requirements}
</requirements>

<available_agent_templates>
- security_reviewer: Security vulnerability detection, OWASP expertise
- code_quality_reviewer: Code quality, maintainability, best practices
- performance_analyzer: Performance bottlenecks, optimization opportunities
- test_generator: Unit test generation, coverage improvement
- documentation_writer: Documentation, docstrings, README generation
- style_enforcer: Code style, formatting, conventions
- result_synthesizer: Aggregates and reports findings from other agents
</available_agent_templates>

Recommend agents and their configuration:
{{
    "agents": [
        {{
            "template_id": "security_reviewer",
            "priority": 1,
            "customizations": {{
                "focus_areas": ["injection", "auth"],
                "model_tier": "capable"
            }},
            "reasoning": "Why this agent is needed"
        }}
    ],
    "workflow_stages": [
        {{
            "name": "Analysis",
            "agents": ["security_reviewer", "code_quality_reviewer"],
            "parallel": true
        }},
        {{
            "name": "Synthesis",
            "agents": ["result_synthesizer"],
            "parallel": false
        }}
    ],
    "estimated_cost_tier": "cheap or moderate or expensive",
    "estimated_duration": "fast (<1min) or moderate (1-5min) or slow (>5min)"
}}

Respond ONLY with valid JSON."""
