"""Unit tests for document loader."""

from pathlib import Path
from unittest.mock import patch

from drift.config.models import BundleStrategy, DocumentBundleConfig
from drift.core.types import DocumentBundle, DocumentFile
from drift.documents.loader import DocumentLoader


class TestDocumentLoader:
    """Tests for DocumentLoader class."""

    def test_initialization_with_project_path(self, temp_dir):
        """Test loader initialization with project path."""
        loader = DocumentLoader(project_path=temp_dir)

        assert loader.project_path == temp_dir

    def test_initialization_converts_string_path(self, temp_dir):
        """Test loader converts string path to Path object."""
        loader = DocumentLoader(project_path=str(temp_dir))

        assert isinstance(loader.project_path, Path)
        assert loader.project_path == temp_dir

    def test_discover_files_with_single_pattern(self, temp_dir):
        """Test file discovery with single glob pattern."""
        # Create test files
        (temp_dir / "test1.md").write_text("content1")
        (temp_dir / "test2.md").write_text("content2")
        (temp_dir / "test.txt").write_text("not matched")

        loader = DocumentLoader(project_path=temp_dir)
        files = loader._discover_files(["*.md"])

        assert len(files) == 2
        assert all(f.suffix == ".md" for f in files)
        assert all(f.is_file() for f in files)

    def test_discover_files_with_multiple_patterns(self, temp_dir):
        """Test file discovery with multiple glob patterns."""
        # Create test files
        (temp_dir / "test1.md").write_text("content1")
        (temp_dir / "test2.txt").write_text("content2")
        (temp_dir / "test3.py").write_text("content3")

        loader = DocumentLoader(project_path=temp_dir)
        files = loader._discover_files(["*.md", "*.txt"])

        assert len(files) == 2
        suffixes = {f.suffix for f in files}
        assert suffixes == {".md", ".txt"}

    def test_discover_files_with_nested_pattern(self, temp_dir):
        """Test file discovery with nested directory pattern."""
        # Create nested structure
        nested_dir = temp_dir / "subdir" / "deep"
        nested_dir.mkdir(parents=True)
        (nested_dir / "test.md").write_text("content")
        (temp_dir / "root.md").write_text("root content")

        loader = DocumentLoader(project_path=temp_dir)
        files = loader._discover_files(["**/*.md"])

        assert len(files) == 2
        assert any("deep" in str(f) for f in files)

    def test_discover_files_ignores_directories(self, temp_dir):
        """Test that file discovery ignores directories."""
        # Create a directory that matches pattern
        (temp_dir / "test.md").mkdir()
        (temp_dir / "actual_file.md").write_text("content")

        loader = DocumentLoader(project_path=temp_dir)
        files = loader._discover_files(["*.md"])

        assert len(files) == 1
        assert files[0].name == "actual_file.md"

    def test_discover_files_returns_empty_for_no_matches(self, temp_dir):
        """Test file discovery returns empty list when no matches."""
        loader = DocumentLoader(project_path=temp_dir)
        files = loader._discover_files(["*.nonexistent"])

        assert files == []

    def test_discover_files_deduplicates(self, temp_dir):
        """Test that file discovery removes duplicates."""
        (temp_dir / "test.md").write_text("content")

        loader = DocumentLoader(project_path=temp_dir)
        # Use overlapping patterns
        files = loader._discover_files(["*.md", "test.md"])

        assert len(files) == 1

    def test_discover_files_sorts_results(self, temp_dir):
        """Test that file discovery returns sorted results."""
        (temp_dir / "zebra.md").write_text("z")
        (temp_dir / "apple.md").write_text("a")
        (temp_dir / "middle.md").write_text("m")

        loader = DocumentLoader(project_path=temp_dir)
        files = loader._discover_files(["*.md"])

        assert files[0].name == "apple.md"
        assert files[1].name == "middle.md"
        assert files[2].name == "zebra.md"

    def test_load_file_content_utf8(self, temp_dir):
        """Test loading file with UTF-8 encoding."""
        test_file = temp_dir / "test.txt"
        test_content = "Hello, 世界! 🌍"
        test_file.write_text(test_content, encoding="utf-8")

        loader = DocumentLoader(project_path=temp_dir)
        content = loader._load_file_content(test_file)

        assert content == test_content

    def test_load_file_content_latin1_fallback(self, temp_dir):
        """Test loading file falls back to latin-1 on UTF-8 error."""
        test_file = temp_dir / "test.txt"
        # Write with latin-1 encoding
        test_content = "Café résumé"
        test_file.write_text(test_content, encoding="latin-1")

        loader = DocumentLoader(project_path=temp_dir)
        content = loader._load_file_content(test_file)

        # Should successfully read the file
        assert isinstance(content, str)
        assert len(content) > 0

    def test_load_file_content_handles_permission_error(self, temp_dir):
        """Test loading file handles permission errors gracefully."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        loader = DocumentLoader(project_path=temp_dir)

        with patch("pathlib.Path.read_text", side_effect=PermissionError("Access denied")):
            content = loader._load_file_content(test_file)

        assert "[Error reading file:" in content
        assert "Access denied" in content

    def test_load_file_content_handles_missing_file(self, temp_dir):
        """Test loading file handles missing file error."""
        test_file = temp_dir / "nonexistent.txt"

        loader = DocumentLoader(project_path=temp_dir)
        content = loader._load_file_content(test_file)

        assert "[Error reading file:" in content

    def test_create_document_file(self, temp_dir):
        """Test creating DocumentFile object."""
        test_file = temp_dir / "subdir" / "test.md"
        test_file.parent.mkdir(parents=True)
        test_content = "# Test content"
        test_file.write_text(test_content)

        loader = DocumentLoader(project_path=temp_dir)
        doc_file = loader._create_document_file(test_file)

        assert isinstance(doc_file, DocumentFile)
        assert doc_file.file_path == test_file
        assert doc_file.content == test_content
        assert doc_file.relative_path == "subdir/test.md"

    def test_create_individual_bundles(self, temp_dir):
        """Test creating individual bundles strategy."""
        # Create test files
        file1 = temp_dir / "skill1" / "SKILL.md"
        file2 = temp_dir / "skill2" / "SKILL.md"
        file1.parent.mkdir(parents=True)
        file2.parent.mkdir(parents=True)
        file1.write_text("Skill 1")
        file2.write_text("Skill 2")

        bundle_config = DocumentBundleConfig(
            bundle_type="skill",
            file_patterns=["*/SKILL.md"],
            bundle_strategy=BundleStrategy.INDIVIDUAL,
            resource_patterns=[],
        )

        loader = DocumentLoader(project_path=temp_dir)
        bundles = loader._create_individual_bundles([file1, file2], bundle_config)

        assert len(bundles) == 2
        assert all(isinstance(b, DocumentBundle) for b in bundles)
        assert all(b.bundle_type == "skill" for b in bundles)
        assert all(b.bundle_strategy == "individual" for b in bundles)
        assert all(len(b.files) == 1 for b in bundles)

    def test_create_individual_bundles_with_resources(self, temp_dir):
        """Test creating individual bundles with resource files."""
        # Create main file and resources
        main_file = temp_dir / "skill1" / "SKILL.md"
        resource1 = temp_dir / "skill1" / "example.py"
        resource2 = temp_dir / "skill1" / "template.md"
        other_resource = temp_dir / "skill2" / "other.py"  # Should not be included

        main_file.parent.mkdir(parents=True)
        main_file.write_text("Skill 1")
        resource1.write_text("# Example")
        resource2.write_text("# Template")
        other_resource.parent.mkdir(parents=True)
        other_resource.write_text("# Other")

        bundle_config = DocumentBundleConfig(
            bundle_type="skill",
            file_patterns=["skill1/SKILL.md"],
            bundle_strategy=BundleStrategy.INDIVIDUAL,
            resource_patterns=["**/*.py", "**/*.md"],
        )

        loader = DocumentLoader(project_path=temp_dir)
        bundles = loader._create_individual_bundles([main_file], bundle_config)

        assert len(bundles) == 1
        bundle = bundles[0]
        # Should have main file + 2 resources (not other.py from skill2)
        assert len(bundle.files) == 3
        file_names = {f.file_path.name for f in bundle.files}
        assert file_names == {"SKILL.md", "example.py", "template.md"}

    def test_create_individual_bundles_unique_ids(self, temp_dir):
        """Test that individual bundles get unique IDs."""
        file1 = temp_dir / "test1.md"
        file2 = temp_dir / "test2.md"
        file1.write_text("content1")
        file2.write_text("content2")

        bundle_config = DocumentBundleConfig(
            bundle_type="test",
            file_patterns=["*.md"],
            bundle_strategy=BundleStrategy.INDIVIDUAL,
            resource_patterns=[],
        )

        loader = DocumentLoader(project_path=temp_dir)
        bundles = loader._create_individual_bundles([file1, file2], bundle_config)

        assert len(bundles) == 2
        # Each bundle should have unique ID (hash of file path)
        assert bundles[0].bundle_id != bundles[1].bundle_id
        # IDs should be 12 char MD5 hashes
        assert all(len(b.bundle_id) == 12 for b in bundles)

    def test_create_collection_bundle(self, temp_dir):
        """Test creating collection bundle strategy."""
        # Create multiple files
        file1 = temp_dir / "cmd1.md"
        file2 = temp_dir / "cmd2.md"
        file3 = temp_dir / "CLAUDE.md"
        file1.write_text("Command 1")
        file2.write_text("Command 2")
        file3.write_text("Claude config")

        bundle_config = DocumentBundleConfig(
            bundle_type="mixed",
            file_patterns=["*.md"],
            bundle_strategy=BundleStrategy.COLLECTION,
            resource_patterns=[],
        )

        loader = DocumentLoader(project_path=temp_dir)
        bundles = loader._create_collection_bundle([file1, file2, file3], bundle_config)

        assert len(bundles) == 1
        bundle = bundles[0]
        assert bundle.bundle_type == "mixed"
        assert bundle.bundle_strategy == "collection"
        assert len(bundle.files) == 3
        # Bundle ID should be 12 char MD5 hash
        assert len(bundle.bundle_id) == 12

    def test_create_collection_bundle_empty_files(self, temp_dir):
        """Test creating collection bundle with empty file list."""
        bundle_config = DocumentBundleConfig(
            bundle_type="test",
            file_patterns=["*.md"],
            bundle_strategy=BundleStrategy.COLLECTION,
            resource_patterns=[],
        )

        loader = DocumentLoader(project_path=temp_dir)
        bundles = loader._create_collection_bundle([], bundle_config)

        # Even empty list creates a bundle (with no files)
        assert len(bundles) == 1
        assert len(bundles[0].files) == 0

    def test_load_bundles_individual_strategy(self, temp_dir):
        """Test load_bundles with individual strategy."""
        # Create test files
        file1 = temp_dir / "test1.md"
        file2 = temp_dir / "test2.md"
        file1.write_text("content1")
        file2.write_text("content2")

        bundle_config = DocumentBundleConfig(
            bundle_type="test",
            file_patterns=["*.md"],
            bundle_strategy=BundleStrategy.INDIVIDUAL,
            resource_patterns=[],
        )

        loader = DocumentLoader(project_path=temp_dir)
        bundles = loader.load_bundles(bundle_config)

        assert len(bundles) == 2
        assert all(b.bundle_strategy == "individual" for b in bundles)

    def test_load_bundles_collection_strategy(self, temp_dir):
        """Test load_bundles with collection strategy."""
        file1 = temp_dir / "test1.md"
        file2 = temp_dir / "test2.md"
        file1.write_text("content1")
        file2.write_text("content2")

        bundle_config = DocumentBundleConfig(
            bundle_type="test",
            file_patterns=["*.md"],
            bundle_strategy=BundleStrategy.COLLECTION,
            resource_patterns=[],
        )

        loader = DocumentLoader(project_path=temp_dir)
        bundles = loader.load_bundles(bundle_config)

        assert len(bundles) == 1
        assert bundles[0].bundle_strategy == "collection"
        assert len(bundles[0].files) == 2

    def test_load_bundles_no_matching_files(self, temp_dir):
        """Test load_bundles returns empty when no files match."""
        bundle_config = DocumentBundleConfig(
            bundle_type="test",
            file_patterns=["*.nonexistent"],
            bundle_strategy=BundleStrategy.INDIVIDUAL,
            resource_patterns=[],
        )

        loader = DocumentLoader(project_path=temp_dir)
        bundles = loader.load_bundles(bundle_config)

        assert bundles == []

    def test_format_bundle_for_llm(self, temp_dir):
        """Test formatting bundle for LLM consumption."""
        file1 = temp_dir / "test1.md"
        file2 = temp_dir / "subdir" / "test2.md"
        file1.write_text("Content 1")
        file2.parent.mkdir(parents=True)
        file2.write_text("Content 2")

        bundle = DocumentBundle(
            bundle_id="test_bundle_123",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[
                DocumentFile(
                    relative_path="test1.md",
                    content="Content 1",
                    file_path=file1,
                ),
                DocumentFile(
                    relative_path="subdir/test2.md",
                    content="Content 2",
                    file_path=file2,
                ),
            ],
        )

        loader = DocumentLoader(project_path=temp_dir)
        formatted = loader.format_bundle_for_llm(bundle)

        assert "test1.md" in formatted
        assert "subdir/test2.md" in formatted
        assert "Content 1" in formatted
        assert "Content 2" in formatted
        assert "---" in formatted  # Separator

    def test_format_bundle_for_llm_empty_bundle(self, temp_dir):
        """Test formatting empty bundle for LLM."""
        bundle = DocumentBundle(
            bundle_id="empty_bundle",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[],
        )

        loader = DocumentLoader(project_path=temp_dir)
        formatted = loader.format_bundle_for_llm(bundle)

        assert formatted == ""

    def test_discover_resources(self, temp_dir):
        """Test discovering resource files relative to main file."""
        # Create structure
        skill_dir = temp_dir / "skill1"
        skill_dir.mkdir()
        main_file = skill_dir / "SKILL.md"
        main_file.write_text("main")
        (skill_dir / "example.py").write_text("example")
        (skill_dir / "template.js").write_text("template")
        (skill_dir / "readme.txt").write_text("readme")

        loader = DocumentLoader(project_path=temp_dir)
        resources = loader._discover_resources(main_file, ["**/*.py", "**/*.js"])

        assert len(resources) == 2
        names = {r.name for r in resources}
        assert names == {"example.py", "template.js"}

    def test_discover_resources_excludes_main(self, temp_dir):
        """Test that discover_resources excludes main file."""
        skill_dir = temp_dir / "skill1"
        skill_dir.mkdir()
        main_file = skill_dir / "SKILL.md"
        main_file.write_text("main")
        (skill_dir / "other.md").write_text("other")

        loader = DocumentLoader(project_path=temp_dir)
        resources = loader._discover_resources(main_file, ["**/*.md"])

        # Should only get other.md, not main SKILL.md
        assert len(resources) == 1
        assert resources[0].name == "other.md"

    def test_generate_bundle_id(self, temp_dir):
        """Test bundle ID generation."""
        file1 = temp_dir / "test1.md"
        file2 = temp_dir / "test2.md"
        file1.write_text("content1")
        file2.write_text("content2")

        loader = DocumentLoader(project_path=temp_dir)

        # Same file should generate same ID
        id1 = loader._generate_bundle_id(file1)
        id2 = loader._generate_bundle_id(file1)
        assert id1 == id2

        # Different files should generate different IDs
        id3 = loader._generate_bundle_id(file2)
        assert id1 != id3

        # Multiple files should generate unique ID
        id4 = loader._generate_bundle_id(file1, file2)
        assert id4 != id1
        assert id4 != id3

        # IDs should be MD5 hashes (12 chars)
        assert len(id1) == 12
        assert len(id4) == 12
