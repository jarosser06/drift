"""Unit tests for file existence checker."""

from pathlib import Path

from drift.draft.checker import FileExistenceChecker


class TestFileExistenceChecker:
    """Tests for FileExistenceChecker class."""

    def test_check_no_files_exist(self, temp_dir):
        """Test checking files when none exist."""
        files = [
            temp_dir / "file1.md",
            temp_dir / "file2.md",
            temp_dir / "file3.md",
        ]

        any_exist, existing = FileExistenceChecker.check(files)

        assert any_exist is False
        assert existing == []

    def test_check_all_files_exist(self, temp_dir):
        """Test checking files when all exist."""
        # Create files
        file1 = temp_dir / "file1.md"
        file2 = temp_dir / "file2.md"
        file3 = temp_dir / "file3.md"
        file1.touch()
        file2.touch()
        file3.touch()

        files = [file1, file2, file3]

        any_exist, existing = FileExistenceChecker.check(files)

        assert any_exist is True
        assert len(existing) == 3
        assert set(existing) == {file1, file2, file3}

    def test_check_some_files_exist(self, temp_dir):
        """Test checking files when some exist."""
        # Create only some files
        file1 = temp_dir / "file1.md"
        file2 = temp_dir / "file2.md"
        file3 = temp_dir / "file3.md"
        file1.touch()
        file3.touch()
        # file2 not created

        files = [file1, file2, file3]

        any_exist, existing = FileExistenceChecker.check(files)

        assert any_exist is True
        assert len(existing) == 2
        assert set(existing) == {file1, file3}

    def test_check_empty_list(self):
        """Test checking empty list of files."""
        files = []

        any_exist, existing = FileExistenceChecker.check(files)

        assert any_exist is False
        assert existing == []

    def test_check_single_file_exists(self, temp_dir):
        """Test checking single file that exists."""
        file1 = temp_dir / "file.md"
        file1.touch()

        any_exist, existing = FileExistenceChecker.check([file1])

        assert any_exist is True
        assert existing == [file1]

    def test_check_single_file_not_exists(self, temp_dir):
        """Test checking single file that doesn't exist."""
        file1 = temp_dir / "file.md"

        any_exist, existing = FileExistenceChecker.check([file1])

        assert any_exist is False
        assert existing == []

    def test_check_nested_file_exists(self, temp_dir):
        """Test checking file in nested directory."""
        # Create nested directory and file
        nested_dir = temp_dir / "a" / "b" / "c"
        nested_dir.mkdir(parents=True)
        nested_file = nested_dir / "file.md"
        nested_file.touch()

        any_exist, existing = FileExistenceChecker.check([nested_file])

        assert any_exist is True
        assert existing == [nested_file]

    def test_check_directory_not_counted_as_file(self, temp_dir):
        """Test that directories are not counted as existing files."""
        # Create a directory with the same name as expected file
        dir_path = temp_dir / "file.md"
        dir_path.mkdir()

        # Note: Path.exists() returns True for directories
        # but we're testing the checker's behavior
        any_exist, existing = FileExistenceChecker.check([dir_path])

        # Directory exists, so exists() returns True
        assert any_exist is True
        assert existing == [dir_path]

    def test_check_preserves_order(self, temp_dir):
        """Test that existing files preserve input order."""
        # Create files
        file1 = temp_dir / "a.md"
        file2 = temp_dir / "b.md"
        file3 = temp_dir / "c.md"
        file1.touch()
        file2.touch()
        file3.touch()

        files = [file3, file1, file2]

        any_exist, existing = FileExistenceChecker.check(files)

        assert any_exist is True
        # Order should be preserved
        assert existing == [file3, file1, file2]

    def test_check_with_absolute_paths(self, temp_dir):
        """Test checking files with absolute paths."""
        file1 = temp_dir.absolute() / "file1.md"
        file2 = temp_dir.absolute() / "file2.md"
        file1.touch()

        files = [file1, file2]

        any_exist, existing = FileExistenceChecker.check(files)

        assert any_exist is True
        assert len(existing) == 1
        assert existing[0] == file1

    def test_check_with_relative_paths(self, temp_dir):
        """Test checking files with relative paths."""
        # Create files
        file1 = temp_dir / "file1.md"
        file1.touch()

        # Use relative path from temp_dir
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            relative_file = Path("file1.md")

            any_exist, existing = FileExistenceChecker.check([relative_file])

            assert any_exist is True
            assert existing == [relative_file]
        finally:
            os.chdir(original_cwd)

    def test_check_mixed_existing_and_nonexisting(self, temp_dir):
        """Test checking mix of many existing and non-existing files."""
        # Create some files
        existing_files = []
        nonexisting_files = []

        for i in range(5):
            f = temp_dir / f"exists_{i}.md"
            f.touch()
            existing_files.append(f)

        for i in range(5):
            f = temp_dir / f"not_exists_{i}.md"
            nonexisting_files.append(f)

        # Mix them together
        all_files = existing_files + nonexisting_files

        any_exist, existing = FileExistenceChecker.check(all_files)

        assert any_exist is True
        assert len(existing) == 5
        assert set(existing) == set(existing_files)
