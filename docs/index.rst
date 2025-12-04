Drift Documentation
===================

Quality assurance for AI-augmented codebases.

`GitHub <https://github.com/jarosser06/drift>`_ | `Issues <https://github.com/jarosser06/drift/issues>`_ | `PyPI <https://pypi.org/project/ai-drift/>`_

What Drift Does
---------------

Drift validates your AI-augmented development environment using custom rules you define in ``.drift.yaml``.

**IMPORTANT:** Drift has NO built-in rules. All validation rules must be defined by you in ``.drift.yaml`` under ``rule_definitions``. Without rules, Drift does nothing.

**Primary Use: Project Structure Validation**

Run ``drift --no-llm`` to execute your custom programmatic validation rules without API calls. Define rules in ``.drift.yaml`` to check:

- **Dependency health**: Detect redundant transitive dependencies in commands, skills, and agents
- **Link integrity**: Validate all file references and resource links in documentation
- **Completeness checks**: Ensure skills, commands, and agents have required structure
- **Configuration validation**: Verify agent tools format, frontmatter schema, and MCP permissions
- **Consistency validation**: Detect contradictions between commands and project guidelines
- **Required files**: Verify essential configuration files exist

See :doc:`configuration` for rule examples and :doc:`quickstart` for starter rules.

**Conversation Quality Analysis**

Conversation analysis helps teams identify where AI collaboration can be improved.

Run ``drift`` (requires LLM access and rules with ``type: prompt``) to analyze AI agent conversation logs. Define custom conversation-level validation rules in ``.drift.yaml`` to detect patterns like:

- User manually executing steps that slash commands automate
- AI agent not using available skills for specialized tasks
- Available automation or capabilities not being utilized
- Conversations diverging from documented best practices

Getting Started
---------------

.. toctree::
   :maxdepth: 2

   installation
   quickstart
   configuration

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
