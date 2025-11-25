"""Integration test for CLI on the REAL drift project."""

import subprocess


class TestRealProjectCLI:
    """Test CLI on the actual drift project directory."""

    def test_detailed_flag_shows_execution_details_for_real_project(self):
        """Test that --detailed shows execution details when run on the REAL drift project."""
        # Run drift with --detailed and --no-llm on the ACTUAL drift project
        result = subprocess.run(
            ["uv", "run", "drift", "--detailed", "--no-llm"],
            cwd="/Users/jim/Projects/drift",
            capture_output=True,
            text=True,
        )

        # Should succeed (exit code 2 means rule failed, which is expected
        # since .claude.md doesn't exist)
        assert result.returncode in [
            0,
            2,
        ], (
            f"CLI failed with unexpected exit code:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        stdout = result.stdout

        # Should show execution details section
        assert (
            "Test Execution Details" in stdout or "Execution Details" in stdout
        ), f"No execution details section found in output:\n{stdout}"

        # Should show the claude_md_missing rule
        assert (
            "claude_md_missing" in stdout
        ), f"claude_md_missing rule not found in output:\n{stdout}"

        # Should show execution context explaining WHAT WAS CHECKED
        # This should include:
        # - What bundle was checked (bundle type, bundle ID)
        # - What files were validated
        # - What validation was performed
        assert any(
            keyword in stdout
            for keyword in ["Bundle", "bundle", "Files checked", "Validated", "Validation"]
        ), f"No execution context found in output:\n{stdout}"

        # Should specifically mention the file being validated (CLAUDE.md or .claude.md)
        assert (
            "CLAUDE.md" in stdout or ".claude.md" in stdout
        ), "CLAUDE.md/.claude.md not mentioned in output:\n{stdout}"

        # Should show the validation type (file_exists)
        assert (
            "file_exists" in stdout or "File exists" in stdout or "file exists" in stdout
        ), f"Validation type not shown in output:\n{stdout}"
