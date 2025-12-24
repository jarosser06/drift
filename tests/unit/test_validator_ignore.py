"""Unit tests for validator ignore pattern handling via rule params."""

import tempfile
from pathlib import Path

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators.base import BaseValidator


class MockValidator(BaseValidator):
    """Mock validator for testing."""

    @property
    def validation_type(self):
        """Return validation type."""
        return "test:mock"

    @property
    def computation_type(self):
        """Return computation type."""
        return "programmatic"

    def validate(self, rule, bundle, all_bundles=None):
        """Mock validate that tracks which files were checked."""
        self.checked_files = []
        for rel_path, content, file_path in self._iter_bundle_files(bundle, rule):
            self.checked_files.append(rel_path)
        return None


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        (project_path / "src").mkdir()
        (project_path / "tests").mkdir()
        (project_path / ".git").mkdir()

        (project_path / "README.md").write_text("# Project")
        (project_path / "src" / "main.py").write_text("print('hello')")
        (project_path / "src" / "utils.py").write_text("def util(): pass")
        (project_path / "tests" / "test_main.py").write_text("def test(): pass")
        (project_path / ".git" / "config").write_text("[core]")
        (project_path / "temp.tmp").write_text("temporary")

        yield project_path


@pytest.fixture
def sample_bundle(temp_project_dir):
    """Create a sample document bundle."""
    files = [
        DocumentFile(
            file_path=temp_project_dir / "README.md", relative_path="README.md", content="# Project"
        ),
        DocumentFile(
            file_path=temp_project_dir / "src" / "main.py",
            relative_path="src/main.py",
            content="print('hello')",
        ),
        DocumentFile(
            file_path=temp_project_dir / "src" / "utils.py",
            relative_path="src/utils.py",
            content="def util(): pass",
        ),
        DocumentFile(
            file_path=temp_project_dir / "tests" / "test_main.py",
            relative_path="tests/test_main.py",
            content="def test(): pass",
        ),
        DocumentFile(
            file_path=temp_project_dir / ".git" / "config",
            relative_path=".git/config",
            content="[core]",
        ),
        DocumentFile(
            file_path=temp_project_dir / "temp.tmp", relative_path="temp.tmp", content="temporary"
        ),
    ]

    return DocumentBundle(
        bundle_id="test",
        bundle_type="project",
        bundle_strategy="collection",
        files=files,
        project_path=temp_project_dir,
    )


class TestShouldIgnoreFile:
    """Tests for _should_ignore_file helper method."""

    def test_no_patterns(self):
        """Test with no ignore patterns."""
        validator = MockValidator()
        assert validator._should_ignore_file("test.py", None) is False

    def test_glob_pattern_match(self):
        """Test glob pattern matching."""
        validator = MockValidator()
        assert validator._should_ignore_file("test.tmp", ["*.tmp"]) is True

    def test_glob_pattern_no_match(self):
        """Test glob pattern non-matching."""
        validator = MockValidator()
        assert validator._should_ignore_file("test.py", ["*.tmp"]) is False

    def test_directory_pattern(self):
        """Test directory pattern matching."""
        validator = MockValidator()
        assert validator._should_ignore_file(".git/config", [".git/**"]) is True
        assert validator._should_ignore_file("foo/.git/config", ["**/.git/**"]) is True


class TestIterBundleFiles:
    """Tests for _iter_bundle_files helper method."""

    def test_no_ignore_patterns(self, sample_bundle):
        """Test iteration with no ignore patterns."""
        validator = MockValidator()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            params={},  # No ignore_patterns
        )

        files = list(validator._iter_bundle_files(sample_bundle, rule))
        assert len(files) == 6
        file_paths = [f[0] for f in files]
        assert "README.md" in file_paths
        assert "src/main.py" in file_paths
        assert "temp.tmp" in file_paths

    def test_with_ignore_patterns(self, sample_bundle):
        """Test iteration with ignore patterns from rule params."""
        validator = MockValidator()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            params={"ignore_patterns": ["*.tmp", ".git/**"]},
        )

        files = list(validator._iter_bundle_files(sample_bundle, rule))
        file_paths = [f[0] for f in files]

        # Should exclude temp.tmp and .git/config
        assert "temp.tmp" not in file_paths
        assert ".git/config" not in file_paths
        # Should include others
        assert "README.md" in file_paths
        assert "src/main.py" in file_paths

    def test_tuple_structure(self, sample_bundle):
        """Test that _iter_bundle_files yields correct tuple structure."""
        validator = MockValidator()
        rule = ValidationRule(rule_type="test:mock", description="Test", params={})

        files = list(validator._iter_bundle_files(sample_bundle, rule))
        for file_tuple in files:
            assert len(file_tuple) == 3
            rel_path, content, file_path = file_tuple
            assert isinstance(rel_path, str)
            assert isinstance(content, str)
            assert isinstance(file_path, str)

    def test_empty_ignore_list(self, sample_bundle):
        """Test with empty ignore patterns list."""
        validator = MockValidator()
        rule = ValidationRule(
            rule_type="test:mock", description="Test", params={"ignore_patterns": []}
        )

        files_with_empty = list(validator._iter_bundle_files(sample_bundle, rule))
        assert len(files_with_empty) == 6

    def test_all_files_ignored(self, sample_bundle):
        """Test when all files are ignored."""
        validator = MockValidator()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            params={"ignore_patterns": ["*", "**/*"]},
        )

        files = list(validator._iter_bundle_files(sample_bundle, rule))
        assert len(files) == 0

    def test_specific_file_types_ignored(self, sample_bundle):
        """Test ignoring specific file types."""
        validator = MockValidator()
        rule = ValidationRule(
            rule_type="test:mock", description="Test", params={"ignore_patterns": ["*.py"]}
        )

        files = list(validator._iter_bundle_files(sample_bundle, rule))
        file_paths = [f[0] for f in files]

        # Should exclude all .py files
        assert "src/main.py" not in file_paths
        assert "src/utils.py" not in file_paths
        assert "tests/test_main.py" not in file_paths
        # Should include non-.py files
        assert "README.md" in file_paths

    def test_directory_patterns(self, sample_bundle):
        """Test directory-level ignore patterns."""
        validator = MockValidator()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            params={"ignore_patterns": ["tests/**", ".git/**"]},
        )

        files = list(validator._iter_bundle_files(sample_bundle, rule))
        file_paths = [f[0] for f in files]

        # Should exclude tests/ and .git/
        assert "tests/test_main.py" not in file_paths
        assert ".git/config" not in file_paths
        # Should include others
        assert "src/main.py" in file_paths


class TestValidatorIgnoreIntegration:
    """Integration tests for validator ignore pattern handling."""

    def test_validator_receives_ignore_patterns(self, sample_bundle):
        """Test that validator can access ignore patterns from rule params."""
        validator = MockValidator()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            params={"ignore_patterns": ["*.tmp"]},
        )

        validator.validate(rule, sample_bundle)

        # MockValidator's validate() uses _iter_bundle_files
        # Should not have checked temp.tmp
        assert "temp.tmp" not in validator.checked_files
        assert "README.md" in validator.checked_files

    def test_validator_without_ignore_patterns(self, sample_bundle):
        """Test validator with no ignore patterns in params."""
        validator = MockValidator()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            params={},  # No ignore_patterns
        )

        validator.validate(rule, sample_bundle)

        # Should check all files
        assert len(validator.checked_files) == 6

    def test_validator_with_empty_patterns(self, sample_bundle):
        """Test validator with empty ignore patterns."""
        validator = MockValidator()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            params={"ignore_patterns": []},
        )

        validator.validate(rule, sample_bundle)

        # Should check all files
        assert len(validator.checked_files) == 6

    def test_multiple_validators_different_patterns(self, sample_bundle):
        """Test that different validators can have different ignore patterns."""
        validator1 = MockValidator()
        validator2 = MockValidator()

        rule1 = ValidationRule(
            rule_type="test:mock",
            description="Test 1",
            params={"ignore_patterns": ["*.tmp"]},
        )

        rule2 = ValidationRule(
            rule_type="test:mock",
            description="Test 2",
            params={"ignore_patterns": ["*.py"]},
        )

        validator1.validate(rule1, sample_bundle)
        validator2.validate(rule2, sample_bundle)

        # validator1 should not check .tmp files
        assert "temp.tmp" not in validator1.checked_files
        assert "src/main.py" in validator1.checked_files

        # validator2 should not check .py files
        assert "src/main.py" not in validator2.checked_files
        assert "temp.tmp" in validator2.checked_files


class TestRealWorldScenarios:
    """Test realistic ignore pattern scenarios."""

    def test_python_project_ignores(self, sample_bundle):
        """Test common Python project ignore patterns."""
        validator = MockValidator()
        python_ignores = [
            "**/__pycache__/**",
            "*.pyc",
            "*.pyo",
            "**/.pytest_cache/**",
            "**/venv/**",
            "**/.venv/**",
        ]

        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            params={"ignore_patterns": python_ignores},
        )

        files = list(validator._iter_bundle_files(sample_bundle, rule))
        file_paths = [f[0] for f in files]

        # All source files should still be included
        assert "src/main.py" in file_paths

    def test_git_ignores(self, sample_bundle):
        """Test git-related ignore patterns."""
        validator = MockValidator()
        git_ignores = [".git/**", "**/.gitignore"]

        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            params={"ignore_patterns": git_ignores},
        )

        files = list(validator._iter_bundle_files(sample_bundle, rule))
        file_paths = [f[0] for f in files]

        # .git files should be excluded
        assert ".git/config" not in file_paths
        # Other files included
        assert "README.md" in file_paths

    def test_node_project_ignores(self, temp_project_dir):
        """Test Node.js project ignore patterns."""
        # Create some node files
        node_modules = temp_project_dir / "node_modules"
        node_modules.mkdir()
        (node_modules / "package").mkdir()
        (node_modules / "package" / "index.js").write_text("module.exports = {}")
        (temp_project_dir / "package.json").write_text("{}")

        files = [
            DocumentFile(
                file_path=temp_project_dir / "package.json",
                relative_path="package.json",
                content="{}",
            ),
            DocumentFile(
                file_path=temp_project_dir / "node_modules" / "package" / "index.js",
                relative_path="node_modules/package/index.js",
                content="module.exports = {}",
            ),
        ]

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="project",
            bundle_strategy="collection",
            files=files,
            project_path=temp_project_dir,
        )

        validator = MockValidator()
        node_ignores = ["node_modules/**/*", "**/.npm/**"]

        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            params={"ignore_patterns": node_ignores},
        )

        filtered_files = list(validator._iter_bundle_files(bundle, rule))
        file_paths = [f[0] for f in filtered_files]

        # node_modules should be excluded
        assert "node_modules/package/index.js" not in file_paths
        # package.json included
        assert "package.json" in file_paths

    def test_temporary_and_backup_files(self, sample_bundle):
        """Test ignoring temporary and backup files."""
        validator = MockValidator()
        temp_patterns = ["*.tmp", "*.bak", "*.swp", "*~", "*.log"]

        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            params={"ignore_patterns": temp_patterns},
        )

        files = list(validator._iter_bundle_files(sample_bundle, rule))
        file_paths = [f[0] for f in files]

        # temp.tmp should be excluded
        assert "temp.tmp" not in file_paths
        # Regular files included
        assert "README.md" in file_paths
