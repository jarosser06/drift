"""Unit tests for Claude dependency graph analysis."""

import pytest

from drift.utils.claude_dependency_graph import ClaudeDependencyGraph


class TestDependencyGraph:
    """Test cases for DependencyGraph class."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure."""
        # Create .claude directory structure
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-a").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-b").mkdir(parents=True)
        (tmp_path / ".claude" / "agents").mkdir(parents=True)

        return tmp_path

    def test_load_resource_command(self, temp_project):
        """Test loading a command resource."""
        command_file = temp_project / ".claude" / "commands" / "test.md"
        command_file.write_text(
            """---
description: Test command
skills:
  - skill-a
  - skill-b
---
# Content
"""
        )

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(command_file, "command")

        assert "test" in graph.dependencies
        assert graph.dependencies["test"] == {"skill-a", "skill-b"}

    def test_load_resource_skill(self, temp_project):
        """Test loading a skill resource."""
        skill_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_file.write_text(
            """---
name: skill-a
skills:
  - skill-b
---
# Content
"""
        )

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_file, "skill")

        assert "skill-a" in graph.dependencies
        assert graph.dependencies["skill-a"] == {"skill-b"}

    def test_load_resource_no_dependencies(self, temp_project):
        """Test loading a resource with no dependencies."""
        skill_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_file.write_text(
            """---
name: skill-a
description: No deps
---
# Content
"""
        )

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_file, "skill")

        assert "skill-a" in graph.dependencies
        assert graph.dependencies["skill-a"] == set()

    def test_load_resource_file_not_found(self, temp_project):
        """Test loading nonexistent resource."""
        graph = ClaudeDependencyGraph(temp_project)
        nonexistent = temp_project / ".claude" / "commands" / "missing.md"

        with pytest.raises(FileNotFoundError):
            graph.load_resource(nonexistent, "command")

    def test_find_transitive_duplicates_simple(self, temp_project):
        """Test detecting simple transitive duplicates."""
        # Create command that depends on skill-a and skill-b
        command_file = temp_project / ".claude" / "commands" / "cmd.md"
        command_file.write_text(
            """---
skills:
  - skill-a
  - skill-b
---
"""
        )

        # Create skill-a that depends on skill-b
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text(
            """---
name: skill-a
skills:
  - skill-b
---
"""
        )

        # Create skill-b with no deps
        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text(
            """---
name: skill-b
---
"""
        )

        # Load all resources
        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(command_file, "command")
        graph.load_resource(skill_a_file, "skill")
        graph.load_resource(skill_b_file, "skill")

        # Check for duplicates in cmd
        duplicates = graph.find_transitive_duplicates("cmd")

        # skill-b is redundant in cmd because skill-a already depends on it
        assert len(duplicates) == 1
        assert duplicates[0] == ("skill-b", "skill-a")

    def test_find_transitive_duplicates_no_duplicates(self, temp_project):
        """Test when there are no transitive duplicates."""
        command_file = temp_project / ".claude" / "commands" / "cmd.md"
        command_file.write_text(
            """---
skills:
  - skill-a
---
"""
        )

        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text(
            """---
name: skill-a
skills:
  - skill-b
---
"""
        )

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(command_file, "command")
        graph.load_resource(skill_a_file, "skill")

        duplicates = graph.find_transitive_duplicates("cmd")

        assert len(duplicates) == 0

    def test_find_transitive_duplicates_deep_chain(self, temp_project):
        """Test detecting duplicates in deep dependency chain."""
        # cmd -> [skill-a, skill-c]
        # skill-a -> [skill-b]
        # skill-b -> [skill-c]
        # skill-c is redundant in cmd because skill-a -> skill-b -> skill-c

        command_file = temp_project / ".claude" / "commands" / "cmd.md"
        command_file.write_text(
            """---
skills:
  - skill-a
  - skill-c
---
"""
        )

        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text(
            """---
name: skill-a
skills:
  - skill-b
---
"""
        )

        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text(
            """---
name: skill-b
skills:
  - skill-c
---
"""
        )

        (temp_project / ".claude" / "skills" / "skill-c").mkdir(parents=True)
        skill_c_file = temp_project / ".claude" / "skills" / "skill-c" / "SKILL.md"
        skill_c_file.write_text(
            """---
name: skill-c
---
"""
        )

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(command_file, "command")
        graph.load_resource(skill_a_file, "skill")
        graph.load_resource(skill_b_file, "skill")
        graph.load_resource(skill_c_file, "skill")

        duplicates = graph.find_transitive_duplicates("cmd")

        # skill-c is redundant
        assert len(duplicates) == 1
        assert duplicates[0] == ("skill-c", "skill-a")

    def test_find_transitive_duplicates_circular(self, temp_project):
        """Test handling circular dependencies gracefully."""
        # skill-a -> skill-b
        # skill-b -> skill-a (circular)

        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text(
            """---
name: skill-a
skills:
  - skill-b
---
"""
        )

        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text(
            """---
name: skill-b
skills:
  - skill-a
---
"""
        )

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_a_file, "skill")
        graph.load_resource(skill_b_file, "skill")

        # Should not crash with circular dependency
        duplicates = graph.find_transitive_duplicates("skill-a")

        # Both are in each other's transitive deps, but neither is a direct duplicate
        assert isinstance(duplicates, list)

    def test_find_transitive_duplicates_missing_dep(self, temp_project):
        """Test when a declared dependency doesn't exist in graph."""
        command_file = temp_project / ".claude" / "commands" / "cmd.md"
        command_file.write_text(
            """---
skills:
  - skill-a
  - missing-skill
---
"""
        )

        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text(
            """---
name: skill-a
---
"""
        )

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(command_file, "command")
        graph.load_resource(skill_a_file, "skill")

        # Should handle missing dep gracefully
        duplicates = graph.find_transitive_duplicates("cmd")

        assert isinstance(duplicates, list)

    def test_find_transitive_duplicates_resource_not_found(self, temp_project):
        """Test error when resource not in graph."""
        graph = ClaudeDependencyGraph(temp_project)

        with pytest.raises(KeyError):
            graph.find_transitive_duplicates("nonexistent")

    def test_extract_resource_id_agent(self, temp_project):
        """Test resource ID extraction for agents."""
        agent_file = temp_project / ".claude" / "agents" / "my-agent.md"
        agent_file.write_text("---\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(agent_file, "agent")

        assert "my-agent" in graph.dependencies

    def test_multiple_duplicates_same_resource(self, temp_project):
        """Test detecting multiple duplicates from same resource."""
        # cmd -> [skill-a, skill-b, skill-c]
        # skill-a -> [skill-b, skill-c]
        # Both skill-b and skill-c are redundant

        command_file = temp_project / ".claude" / "commands" / "cmd.md"
        command_file.write_text(
            """---
skills:
  - skill-a
  - skill-b
  - skill-c
---
"""
        )

        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text(
            """---
name: skill-a
skills:
  - skill-b
  - skill-c
---
"""
        )

        (temp_project / ".claude" / "skills" / "skill-c").mkdir(parents=True)
        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\n---\n")
        skill_c_file = temp_project / ".claude" / "skills" / "skill-c" / "SKILL.md"
        skill_c_file.write_text("---\nname: skill-c\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(command_file, "command")
        graph.load_resource(skill_a_file, "skill")
        graph.load_resource(skill_b_file, "skill")
        graph.load_resource(skill_c_file, "skill")

        duplicates = graph.find_transitive_duplicates("cmd")

        # Both skill-b and skill-c are redundant
        assert len(duplicates) == 2
        dup_resources = [d[0] for d in duplicates]
        assert "skill-b" in dup_resources
        assert "skill-c" in dup_resources
