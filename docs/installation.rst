Installation
============

Drift is a test-driven development framework for AI workflows. Define validation rules, run checks, fix issues, and iterate to compliance.

Prerequisites
-------------

Drift requires Python 3.10 or later.

Installation
------------

Install the latest stable version from PyPI:

.. code-block:: bash

    uv pip install ai-drift

Development Installation
------------------------

To install Drift for development with all dependencies:

.. code-block:: bash

    git clone https://github.com/jarosser06/drift.git
    cd drift
    uv pip install -e ".[dev]"

This installs Drift in editable mode with development dependencies including:

- pytest (testing)
- black (code formatting)
- flake8 (linting)
- isort (import sorting)
- mypy (type checking)

Provider Setup (Optional)
-------------------------

LLM providers are ONLY required if your rules use ``type: prompt`` for semantic analysis. Programmatic validation (``--no-llm``) works without any provider setup.

Anthropic API
~~~~~~~~~~~~~

Set your API key as an environment variable:

.. code-block:: bash

    export ANTHROPIC_API_KEY=your_api_key_here

Or add it to your shell configuration file (``~/.bashrc``, ``~/.zshrc``, etc.).

AWS Bedrock
~~~~~~~~~~~

Configure your AWS credentials:

.. code-block:: bash

    aws configure

Bedrock requires appropriate IAM permissions for model access.

Claude Code
~~~~~~~~~~~

Claude Code provider uses your existing Claude Code CLI installation. No API key needed.

Ensure the ``claude`` CLI is installed and in your PATH:

.. code-block:: bash

    claude --version

If not installed, visit the Claude Code documentation for installation instructions.

Verifying Installation
----------------------

Verify Drift is installed correctly:

.. code-block:: bash

    drift --version

Run a basic analysis:

.. code-block:: bash

    drift

This performs programmatic validation without requiring an LLM provider.
