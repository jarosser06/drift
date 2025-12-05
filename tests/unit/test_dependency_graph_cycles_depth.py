"""Unit tests for Claude dependency graph cycle detection and depth calculation."""

import pytest

from drift.utils.claude_dependency_graph import ClaudeDependencyGraph


class TestDependencyGraphCycles:
    """Test cases for cycle detection in DependencyGraph."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure."""
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-a").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-b").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-c").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-d").mkdir(parents=True)
        (tmp_path / ".claude" / "agents").mkdir(parents=True)
        return tmp_path

    def test_find_cycles_no_cycle(self, temp_project):
        """Test that find_cycles returns empty list when no cycles exist."""
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_a_file, "skill")
        graph.load_resource(skill_b_file, "skill")

        cycles = graph.find_cycles("skill-a")
        assert cycles == []

    def test_find_cycles_self_loop(self, temp_project):
        """Test detection of self-loop (A → A)."""
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-a\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_a_file, "skill")

        cycles = graph.find_cycles("skill-a")
        assert len(cycles) == 1
        assert cycles[0] == ["skill-a", "skill-a"]

    def test_find_cycles_two_node_cycle(self, temp_project):
        """Test detection of two-node cycle (A → B → A)."""
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\nskills:\n  - skill-a\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_a_file, "skill")
        graph.load_resource(skill_b_file, "skill")

        cycles = graph.find_cycles("skill-a")
        assert len(cycles) == 1
        assert cycles[0] == ["skill-a", "skill-b", "skill-a"]

    def test_find_cycles_multi_node_cycle(self, temp_project):
        """Test detection of multi-node cycle (A → B → C → D → A)."""
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\nskills:\n  - skill-c\n---\n")

        skill_c_file = temp_project / ".claude" / "skills" / "skill-c" / "SKILL.md"
        skill_c_file.write_text("---\nname: skill-c\nskills:\n  - skill-d\n---\n")

        skill_d_file = temp_project / ".claude" / "skills" / "skill-d" / "SKILL.md"
        skill_d_file.write_text("---\nname: skill-d\nskills:\n  - skill-a\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_a_file, "skill")
        graph.load_resource(skill_b_file, "skill")
        graph.load_resource(skill_c_file, "skill")
        graph.load_resource(skill_d_file, "skill")

        cycles = graph.find_cycles("skill-a")
        assert len(cycles) == 1
        assert cycles[0] == ["skill-a", "skill-b", "skill-c", "skill-d", "skill-a"]

    def test_find_cycles_multiple_cycles(self, temp_project):
        """Test detection of multiple cycles from same resource."""
        # skill-a → skill-b → skill-a (cycle 1)
        # skill-a → skill-c → skill-a (cycle 2)
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n  - skill-c\n---\n")

        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\nskills:\n  - skill-a\n---\n")

        skill_c_file = temp_project / ".claude" / "skills" / "skill-c" / "SKILL.md"
        skill_c_file.write_text("---\nname: skill-c\nskills:\n  - skill-a\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_a_file, "skill")
        graph.load_resource(skill_b_file, "skill")
        graph.load_resource(skill_c_file, "skill")

        cycles = graph.find_cycles("skill-a")
        assert len(cycles) == 2
        # Both should be detected
        cycle_strings = [" → ".join(c) for c in cycles]
        assert any("skill-a → skill-b → skill-a" in cs for cs in cycle_strings)
        assert any("skill-a → skill-c → skill-a" in cs for cs in cycle_strings)

    def test_find_cycles_resource_not_found(self, temp_project):
        """Test that find_cycles raises KeyError for non-existent resource."""
        graph = ClaudeDependencyGraph(temp_project)
        with pytest.raises(KeyError, match="not found in dependency graph"):
            graph.find_cycles("nonexistent")

    def test_find_cycles_missing_dependency(self, temp_project):
        """Test handling of missing dependencies in cycle detection."""
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - missing-skill\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_a_file, "skill")

        cycles = graph.find_cycles("skill-a")
        # Should return empty list, not crash
        assert cycles == []


class TestDependencyGraphDepth:
    """Test cases for depth calculation in DependencyGraph."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure."""
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-a").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-b").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-c").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-d").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-e").mkdir(parents=True)
        return tmp_path

    def test_get_dependency_depth_no_dependencies(self, temp_project):
        """Test depth calculation for resource with no dependencies."""
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_a_file, "skill")

        depth, path = graph.get_dependency_depth("skill-a")
        assert depth == 0
        assert path == ["skill-a"]

    def test_get_dependency_depth_single_level(self, temp_project):
        """Test depth calculation for single-level dependency chain."""
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_a_file, "skill")
        graph.load_resource(skill_b_file, "skill")

        depth, path = graph.get_dependency_depth("skill-a")
        assert depth == 1
        assert path == ["skill-a", "skill-b"]

    def test_get_dependency_depth_deep_chain(self, temp_project):
        """Test depth calculation for deep dependency chain."""
        # A → B → C → D → E (depth 4)
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\nskills:\n  - skill-c\n---\n")

        skill_c_file = temp_project / ".claude" / "skills" / "skill-c" / "SKILL.md"
        skill_c_file.write_text("---\nname: skill-c\nskills:\n  - skill-d\n---\n")

        skill_d_file = temp_project / ".claude" / "skills" / "skill-d" / "SKILL.md"
        skill_d_file.write_text("---\nname: skill-d\nskills:\n  - skill-e\n---\n")

        skill_e_file = temp_project / ".claude" / "skills" / "skill-e" / "SKILL.md"
        skill_e_file.write_text("---\nname: skill-e\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_a_file, "skill")
        graph.load_resource(skill_b_file, "skill")
        graph.load_resource(skill_c_file, "skill")
        graph.load_resource(skill_d_file, "skill")
        graph.load_resource(skill_e_file, "skill")

        depth, path = graph.get_dependency_depth("skill-a")
        assert depth == 4
        assert path == ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]

    def test_get_dependency_depth_multiple_branches(self, temp_project):
        """Test depth calculation with multiple dependency branches."""
        # A → B → C (depth 2)
        # A → D (depth 1)
        # Should return depth 2 (longest path)
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n  - skill-d\n---\n")

        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\nskills:\n  - skill-c\n---\n")

        skill_c_file = temp_project / ".claude" / "skills" / "skill-c" / "SKILL.md"
        skill_c_file.write_text("---\nname: skill-c\n---\n")

        skill_d_file = temp_project / ".claude" / "skills" / "skill-d" / "SKILL.md"
        skill_d_file.write_text("---\nname: skill-d\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_a_file, "skill")
        graph.load_resource(skill_b_file, "skill")
        graph.load_resource(skill_c_file, "skill")
        graph.load_resource(skill_d_file, "skill")

        depth, path = graph.get_dependency_depth("skill-a")
        assert depth == 2
        assert path == ["skill-a", "skill-b", "skill-c"]

    def test_get_dependency_depth_with_cycle(self, temp_project):
        """Test depth calculation handles cycles gracefully."""
        # A → B → A (cycle)
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\nskills:\n  - skill-a\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_a_file, "skill")
        graph.load_resource(skill_b_file, "skill")

        depth, path = graph.get_dependency_depth("skill-a")
        # Should handle cycle without infinite loop
        assert isinstance(depth, int)
        assert isinstance(path, list)
        # With BFS, the longest path before cycle detection is A → B → A (depth 2)
        assert depth >= 1  # At minimum goes through one dependency before cycle

    def test_get_dependency_depth_resource_not_found(self, temp_project):
        """Test that get_dependency_depth raises KeyError for non-existent resource."""
        graph = ClaudeDependencyGraph(temp_project)
        with pytest.raises(KeyError, match="not found in dependency graph"):
            graph.get_dependency_depth("nonexistent")

    def test_get_dependency_depth_missing_dependency(self, temp_project):
        """Test handling of missing dependencies in depth calculation."""
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - missing-skill\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(skill_a_file, "skill")

        depth, path = graph.get_dependency_depth("skill-a")
        # Should handle missing dependency gracefully
        assert depth == 1
        assert path == ["skill-a", "missing-skill"]

    def test_get_dependency_depth_command(self, temp_project):
        """Test depth calculation for command resources."""
        command_file = temp_project / ".claude" / "commands" / "test.md"
        command_file.write_text("---\ndescription: Test\nskills:\n  - skill-a\n---\n")

        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\n---\n")

        graph = ClaudeDependencyGraph(temp_project)
        graph.load_resource(command_file, "command")
        graph.load_resource(skill_a_file, "skill")
        graph.load_resource(skill_b_file, "skill")

        depth, path = graph.get_dependency_depth("test")
        assert depth == 2
        assert path == ["test", "skill-a", "skill-b"]
