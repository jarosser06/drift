Drift Documentation
===================

Test-driven development for AI workflows.

`GitHub <https://github.com/jarosser06/drift>`_ | `Issues <https://github.com/jarosser06/drift/issues>`_ | `PyPI <https://pypi.org/project/ai-drift/>`_

What Drift Does
---------------

Drift is a **TDD framework for AI workflows**. Define your standards first, validate against them, fix issues, and iterate - just like TDD for code.

TDD Workflow for AI Agent Projects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Define standards** - Write validation rules in ``.drift.yaml`` for your expected project structure
2. **Run validation** - Execute ``drift`` to see what's missing or broken (red phase)
3. **Fix issues** - Create files, fix links, update configurations manually or with AI assistance (green phase)
4. **Iterate** - Re-run validation until all checks pass (refactor phase)

**No built-in opinions** - You define your team's standards in ``.drift.yaml``, then validate against them. Perfect for bootstrapping new projects or enforcing consistency across teams.

Project Structure Validation (Primary Use)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Define rules in ``.drift.yaml`` to check:

- **Dependency health**: Detect redundant transitive dependencies in commands, skills, and agents
- **Link integrity**: Validate all file references and resource links in documentation
- **Completeness checks**: Ensure skills, commands, and agents have required structure
- **Configuration validation**: Verify agent tools format, frontmatter schema, and MCP permissions
- **Consistency validation**: Detect contradictions between commands and project guidelines
- **Required files**: Verify essential configuration files exist

See :doc:`configuration` for rule examples and :doc:`quickstart` for starter rules.

Conversation Quality Analysis (Optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For teams wanting deeper insights, run ``drift`` with LLM-based rules to analyze AI agent conversations. Define custom conversation-level validation rules in ``.drift.yaml`` to detect patterns like:

- User manually executing steps that slash commands automate
- AI agent not using available skills for specialized tasks
- Available automation or capabilities not being utilized
- Conversations diverging from documented best practices

Requires LLM access and rules with ``type: prompt``.

Getting Started
---------------

.. toctree::
   :maxdepth: 2

   installation
   quickstart
   rules
   validators
   configuration

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
