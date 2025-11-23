"""Unit tests for temporary directory management."""

import json

import pytest

from drift.core.types import Learning
from drift.utils.temp import TempManager


class TestTempManager:
    """Tests for TempManager class."""

    def test_initialization(self, temp_dir):
        """Test temp manager initialization."""
        manager = TempManager(str(temp_dir / "drift"))

        assert manager.temp_dir == temp_dir / "drift"
        assert manager.analysis_dir is None

    def test_initialization_expands_tilde(self):
        """Test that tilde is expanded in temp_dir path."""
        manager = TempManager("~/drift-temp")

        assert "~" not in str(manager.temp_dir)
        assert str(manager.temp_dir).endswith("drift-temp")

    def test_create_analysis_dir(self, temp_dir):
        """Test creating analysis directory."""
        manager = TempManager(str(temp_dir))
        session_id = "test-session-123"

        result = manager.create_analysis_dir(session_id)

        assert result.exists()
        assert result.is_dir()
        assert result.name == f"analysis_{session_id}"
        assert manager.analysis_dir == result

    def test_create_analysis_dir_creates_parents(self, temp_dir):
        """Test that create_analysis_dir creates parent directories."""
        manager = TempManager(str(temp_dir / "nested" / "path"))
        session_id = "test"

        result = manager.create_analysis_dir(session_id)

        assert result.exists()
        assert result.parent.parent.exists()  # Parent directories created

    def test_save_pass_result(self, temp_dir, sample_learning):
        """Test saving analysis pass results."""
        manager = TempManager(str(temp_dir))
        manager.create_analysis_dir("session123")

        result_file = manager.save_pass_result(
            "conv-456",
            "incomplete_work",
            [sample_learning],
        )

        assert result_file.exists()
        assert result_file.name == "incomplete_work.json"

        # Verify content
        with open(result_file, "r") as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["learning_type"] == "incomplete_work"

    def test_save_pass_result_no_analysis_dir(self, temp_dir):
        """Test that save_pass_result fails without analysis dir."""
        manager = TempManager(str(temp_dir))

        with pytest.raises(ValueError) as exc_info:
            manager.save_pass_result("conv", "type", [])
        assert "Analysis directory not created" in str(exc_info.value)

    def test_save_pass_result_creates_conversation_dir(self, temp_dir, sample_learning):
        """Test that save_pass_result creates conversation subdirectory."""
        manager = TempManager(str(temp_dir))
        manager.create_analysis_dir("session")

        manager.save_pass_result("conv-123", "type1", [sample_learning])

        conv_dir = manager.analysis_dir / "conv-123"
        assert conv_dir.exists()
        assert conv_dir.is_dir()

    def test_save_pass_result_multiple_learnings(self, temp_dir, sample_learning):
        """Test saving multiple learnings."""
        manager = TempManager(str(temp_dir))
        manager.create_analysis_dir("session")

        learning2 = Learning(
            turn_number=2,
            agent_tool="test",
            conversation_file="/path",
            observed_behavior="Action 2",
            expected_behavior="Intent 2",
            learning_type="wrong_assumption",
        )

        manager.save_pass_result(
            "conv",
            "test_type",
            [sample_learning, learning2],
        )

        result_file = manager.analysis_dir / "conv" / "test_type.json"
        with open(result_file, "r") as f:
            data = json.load(f)

        assert len(data) == 2

    def test_load_pass_result(self, temp_dir, sample_learning):
        """Test loading saved pass results."""
        manager = TempManager(str(temp_dir))
        manager.create_analysis_dir("session")

        # Save some results first
        manager.save_pass_result("conv", "type1", [sample_learning])

        # Load them back
        learnings = manager.load_pass_result("conv", "type1")

        assert len(learnings) == 1
        assert isinstance(learnings[0], Learning)
        assert learnings[0].learning_type == sample_learning.learning_type

    def test_load_pass_result_not_found(self, temp_dir):
        """Test loading non-existent pass results returns empty list."""
        manager = TempManager(str(temp_dir))
        manager.create_analysis_dir("session")

        learnings = manager.load_pass_result("conv", "nonexistent")

        assert learnings == []

    def test_load_pass_result_no_analysis_dir(self, temp_dir):
        """Test loading pass results without analysis dir."""
        manager = TempManager(str(temp_dir))

        with pytest.raises(ValueError) as exc_info:
            manager.load_pass_result("conv", "type")
        assert "Analysis directory not created" in str(exc_info.value)

    def test_get_all_learnings(self, temp_dir, sample_learning):
        """Test getting all learnings for a conversation."""
        manager = TempManager(str(temp_dir))
        manager.create_analysis_dir("session")

        learning2 = Learning(
            turn_number=2,
            agent_tool="test",
            conversation_file="/path",
            observed_behavior="Action 2",
            expected_behavior="Intent 2",
            learning_type="type2",
        )

        # Save learnings of different types
        manager.save_pass_result("conv", "type1", [sample_learning])
        manager.save_pass_result("conv", "type2", [learning2])

        # Get all learnings
        all_learnings = manager.get_all_learnings("conv")

        assert len(all_learnings) == 2
        types = {learning.learning_type for learning in all_learnings}
        assert "incomplete_work" in types
        assert "type2" in types

    def test_get_all_learnings_no_analysis_dir(self, temp_dir):
        """Test get_all_learnings without analysis dir returns empty list."""
        manager = TempManager(str(temp_dir))

        learnings = manager.get_all_learnings("conv")

        assert learnings == []

    def test_get_all_learnings_conversation_not_found(self, temp_dir):
        """Test get_all_learnings for non-existent conversation."""
        manager = TempManager(str(temp_dir))
        manager.create_analysis_dir("session")

        learnings = manager.get_all_learnings("nonexistent")

        assert learnings == []

    def test_save_metadata(self, temp_dir):
        """Test saving analysis metadata."""
        manager = TempManager(str(temp_dir))
        manager.create_analysis_dir("session")

        metadata = {
            "session_id": "test",
            "timestamp": "2024-01-01T10:00:00",
            "conversations_analyzed": 5,
        }

        manager.save_metadata(metadata)

        metadata_file = manager.analysis_dir / "metadata.json"
        assert metadata_file.exists()

        with open(metadata_file, "r") as f:
            loaded = json.load(f)

        assert loaded == metadata

    def test_save_metadata_no_analysis_dir(self, temp_dir):
        """Test saving metadata without analysis dir fails."""
        manager = TempManager(str(temp_dir))

        with pytest.raises(ValueError) as exc_info:
            manager.save_metadata({})
        assert "Analysis directory not created" in str(exc_info.value)

    def test_cleanup(self, temp_dir):
        """Test cleaning up analysis directory."""
        manager = TempManager(str(temp_dir))
        analysis_dir = manager.create_analysis_dir("session")

        # Create some files
        test_file = analysis_dir / "test.txt"
        test_file.write_text("test content")

        assert analysis_dir.exists()

        manager.cleanup()

        assert not analysis_dir.exists()
        assert manager.analysis_dir is None

    def test_cleanup_no_analysis_dir(self, temp_dir):
        """Test cleanup when no analysis dir exists."""
        manager = TempManager(str(temp_dir))

        # Should not raise error
        manager.cleanup()

        assert manager.analysis_dir is None

    def test_cleanup_force(self, temp_dir):
        """Test force cleanup of entire temp directory."""
        manager = TempManager(str(temp_dir))

        # Create temp dir structure
        temp_file = temp_dir / "some_file.txt"
        temp_file.write_text("test")

        assert temp_dir.exists()

        manager.cleanup(force=True)

        assert not temp_dir.exists()

    def test_cleanup_force_no_temp_dir(self, temp_dir):
        """Test force cleanup when temp dir doesn't exist."""
        nonexistent = temp_dir / "nonexistent"
        manager = TempManager(str(nonexistent))

        # Should not raise error
        manager.cleanup(force=True)

    def test_preserve_for_debugging(self, temp_dir):
        """Test preserving analysis directory for debugging."""
        manager = TempManager(str(temp_dir))
        analysis_dir = manager.create_analysis_dir("session")

        preserved = manager.preserve_for_debugging()

        assert preserved == analysis_dir
        assert analysis_dir.exists()  # Should still exist

    def test_preserve_for_debugging_no_analysis_dir(self, temp_dir):
        """Test preserve_for_debugging returns None when no analysis dir."""
        manager = TempManager(str(temp_dir))

        result = manager.preserve_for_debugging()

        assert result is None

    def test_save_and_load_roundtrip(self, temp_dir, sample_learning):
        """Test full roundtrip of saving and loading learnings."""
        manager = TempManager(str(temp_dir))
        manager.create_analysis_dir("session")

        # Save
        manager.save_pass_result("conv-123", "incomplete_work", [sample_learning])

        # Load
        loaded = manager.load_pass_result("conv-123", "incomplete_work")

        assert len(loaded) == 1
        assert loaded[0].turn_number == sample_learning.turn_number
        assert loaded[0].observed_behavior == sample_learning.observed_behavior
        assert loaded[0].expected_behavior == sample_learning.expected_behavior

    def test_multiple_conversations_same_session(self, temp_dir, sample_learning):
        """Test managing multiple conversations in same analysis session."""
        manager = TempManager(str(temp_dir))
        manager.create_analysis_dir("session")

        # Save results for multiple conversations
        manager.save_pass_result("conv-1", "type1", [sample_learning])
        manager.save_pass_result("conv-2", "type1", [sample_learning])

        # Both should exist independently
        conv1_learnings = manager.get_all_learnings("conv-1")
        conv2_learnings = manager.get_all_learnings("conv-2")

        assert len(conv1_learnings) == 1
        assert len(conv2_learnings) == 1

    def test_empty_learnings_list(self, temp_dir):
        """Test saving empty learnings list."""
        manager = TempManager(str(temp_dir))
        manager.create_analysis_dir("session")

        manager.save_pass_result("conv", "type1", [])

        loaded = manager.load_pass_result("conv", "type1")
        assert loaded == []
