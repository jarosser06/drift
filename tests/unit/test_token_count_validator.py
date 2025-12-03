"""Tests for TokenCountValidator."""

import sys
from unittest.mock import Mock

import pytest

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators.core.file_validators import TokenCountValidator


class TestTokenCountValidator:
    """Tests for TokenCountValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return TokenCountValidator()

    @pytest.fixture
    def tmp_path(self, tmp_path):
        """Provide tmp_path fixture."""
        return tmp_path

    @pytest.fixture
    def bundle_with_file(self, tmp_path):
        """Create bundle with a test file."""
        test_file = tmp_path / "test.md"
        content = "This is a test file with some content for token counting."
        test_file.write_text(content)

        return DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

    # ==================== Anthropic Provider Tests ====================

    def test_anthropic_token_count_under_max(self, validator, tmp_path, monkeypatch):
        """Test that validation passes when Anthropic token count is under max."""
        test_file = tmp_path / "CLAUDE.md"
        content = "Short content"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="CLAUDE.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Check CLAUDE.md token count",
            file_path="CLAUDE.md",
            max_count=1500,
            params={"provider": "anthropic"},
            failure_message="CLAUDE.md exceeds 1500 tokens",
            expected_behavior="CLAUDE.md should be under 1500 tokens",
        )

        # Mock the anthropic module
        mock_client = Mock()
        mock_client.count_tokens.return_value = 50
        mock_anthropic = Mock()
        mock_anthropic.Anthropic.return_value = mock_client

        monkeypatch.setitem(sys.modules, "anthropic", mock_anthropic)

        result = validator.validate(rule, bundle)
        assert result is None

    def test_anthropic_token_count_exceeds_max(self, validator, tmp_path, monkeypatch):
        """Test that validation fails when Anthropic token count exceeds max."""
        test_file = tmp_path / "CLAUDE.md"
        content = "Very long content " * 1000
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="CLAUDE.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Check CLAUDE.md token count",
            file_path="CLAUDE.md",
            max_count=1500,
            params={"provider": "anthropic"},
            failure_message="CLAUDE.md exceeds 1500 tokens",
            expected_behavior="CLAUDE.md should be under 1500 tokens",
        )

        # Mock the anthropic module
        mock_client = Mock()
        mock_client.count_tokens.return_value = 2000
        mock_anthropic = Mock()
        mock_anthropic.Anthropic.return_value = mock_client

        monkeypatch.setitem(sys.modules, "anthropic", mock_anthropic)

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "2000 tokens" in result.observed_issue
        assert "exceeds max 1500" in result.observed_issue
        assert "anthropic tokenizer" in result.observed_issue

    def test_anthropic_missing_package(self, validator, tmp_path, monkeypatch):
        """Test that validation fails gracefully when anthropic package is missing."""
        test_file = tmp_path / "test.md"
        content = "Test content"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Check token count",
            file_path="test.md",
            max_count=1000,
            params={"provider": "anthropic"},
            failure_message="Too many tokens",
            expected_behavior="Should be under limit",
        )

        # Make the import fail by removing from sys.modules and making __import__ raise
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("No module named 'anthropic'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        monkeypatch.delitem(sys.modules, "anthropic", raising=False)

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Token counting failed" in result.observed_issue
        assert "pip install anthropic" in result.observed_issue

    # ==================== OpenAI Provider Tests ====================

    def test_openai_token_count_under_max(self, validator, tmp_path, monkeypatch):
        """Test that validation passes when OpenAI token count is under max."""
        test_file = tmp_path / "test.md"
        content = "Short content for OpenAI"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Check token count",
            file_path="test.md",
            max_count=100,
            params={"provider": "openai"},
            failure_message="Too many tokens",
            expected_behavior="Should be under 100 tokens",
        )

        # Mock tiktoken
        mock_encoding = Mock()
        mock_encoding.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
        mock_tiktoken = Mock()
        mock_tiktoken.encoding_for_model.return_value = mock_encoding

        monkeypatch.setitem(sys.modules, "tiktoken", mock_tiktoken)

        result = validator.validate(rule, bundle)
        assert result is None

    def test_openai_token_count_exceeds_max(self, validator, tmp_path, monkeypatch):
        """Test that validation fails when OpenAI token count exceeds max."""
        test_file = tmp_path / "test.md"
        content = "Long content " * 100
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Check token count",
            file_path="test.md",
            max_count=100,
            params={"provider": "openai"},
            failure_message="Too many tokens",
            expected_behavior="Should be under 100 tokens",
        )

        # Mock tiktoken
        mock_encoding = Mock()
        mock_encoding.encode.return_value = [1] * 150  # 150 tokens
        mock_tiktoken = Mock()
        mock_tiktoken.encoding_for_model.return_value = mock_encoding

        monkeypatch.setitem(sys.modules, "tiktoken", mock_tiktoken)

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "150 tokens" in result.observed_issue
        assert "exceeds max 100" in result.observed_issue
        assert "openai tokenizer" in result.observed_issue

    def test_openai_missing_package(self, validator, tmp_path, monkeypatch):
        """Test that validation fails gracefully when tiktoken package is missing."""
        test_file = tmp_path / "test.md"
        content = "Test content"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Check token count",
            file_path="test.md",
            max_count=1000,
            params={"provider": "openai"},
            failure_message="Too many tokens",
            expected_behavior="Should be under limit",
        )

        # Make the import fail by removing from sys.modules and making __import__ raise
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "tiktoken":
                raise ImportError("No module named 'tiktoken'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        monkeypatch.delitem(sys.modules, "tiktoken", raising=False)

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Token counting failed" in result.observed_issue
        assert "pip install tiktoken" in result.observed_issue

    # ==================== Llama Provider Tests ====================

    def test_llama_token_count_under_max(self, validator, tmp_path, monkeypatch):
        """Test that validation passes when Llama token count is under max."""
        test_file = tmp_path / "test.md"
        content = "Short content for Llama"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Check token count",
            file_path="test.md",
            max_count=100,
            params={"provider": "llama"},
            failure_message="Too many tokens",
            expected_behavior="Should be under 100 tokens",
        )

        # Mock transformers
        mock_tokenizer = Mock()
        mock_tokenizer.encode.return_value = [1, 2, 3, 4, 5, 6]  # 6 tokens
        mock_transformers = Mock()
        mock_transformers.AutoTokenizer.from_pretrained.return_value = mock_tokenizer

        monkeypatch.setitem(sys.modules, "transformers", mock_transformers)

        result = validator.validate(rule, bundle)
        assert result is None

    def test_llama_missing_package(self, validator, tmp_path, monkeypatch):
        """Test that validation fails gracefully when transformers package is missing."""
        test_file = tmp_path / "test.md"
        content = "Test content"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Check token count",
            file_path="test.md",
            max_count=1000,
            params={"provider": "llama"},
            failure_message="Too many tokens",
            expected_behavior="Should be under limit",
        )

        # Ensure transformers module is not available
        monkeypatch.delitem(sys.modules, "transformers", raising=False)

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Token counting failed" in result.observed_issue
        assert "pip install transformers" in result.observed_issue

    # ==================== General Error Cases ====================

    def test_unsupported_provider(self, validator, bundle_with_file):
        """Test that validation fails with unsupported provider."""
        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Check token count",
            file_path="test.md",
            max_count=1000,
            params={"provider": "unsupported"},
            failure_message="Too many tokens",
            expected_behavior="Should be under limit",
        )

        with pytest.raises(ValueError, match="Unsupported token counter provider"):
            validator.validate(rule, bundle_with_file)

    def test_default_provider_is_anthropic(self, validator, tmp_path, monkeypatch):
        """Test that default provider is anthropic when not specified."""
        test_file = tmp_path / "test.md"
        content = "Test content"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        # Rule without params (should default to anthropic)
        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Check token count",
            file_path="test.md",
            max_count=1000,
            failure_message="Too many tokens",
            expected_behavior="Should be under limit",
        )

        # Ensure anthropic module is not available
        monkeypatch.delitem(sys.modules, "anthropic", raising=False)

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "anthropic" in result.observed_issue.lower()

    def test_file_not_found(self, validator, bundle_with_file):
        """Test validation when file doesn't exist."""
        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Check nonexistent file",
            file_path="nonexistent.md",
            max_count=1000,
            params={"provider": "anthropic"},
            failure_message="File not found",
            expected_behavior="File should exist",
        )

        result = validator.validate(rule, bundle_with_file)
        assert result is not None
        assert "does not exist" in result.observed_issue
        assert "nonexistent.md" in result.file_paths

    def test_missing_file_path(self, validator, bundle_with_file):
        """Test that validator raises error when file_path is missing."""
        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="No file path",
            max_count=1000,
            params={"provider": "anthropic"},
            failure_message="Error",
            expected_behavior="Should error",
        )

        with pytest.raises(ValueError, match="requires rule.file_path"):
            validator.validate(rule, bundle_with_file)

    def test_file_read_error(self, validator, tmp_path):
        """Test validation when file cannot be read."""
        test_file = tmp_path / "test.md"
        test_file.write_text("content")
        test_file.chmod(0o000)  # Make unreadable

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content="",
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Read protected file",
            file_path="test.md",
            max_count=1000,
            params={"provider": "anthropic"},
            failure_message="Cannot read",
            expected_behavior="Should be readable",
        )

        try:
            result = validator.validate(rule, bundle)
            assert result is not None
            assert "Failed to read file" in result.observed_issue
        finally:
            # Restore permissions for cleanup
            test_file.chmod(0o644)

    def test_min_count_validation(self, validator, tmp_path, monkeypatch):
        """Test that min_count validation works."""
        test_file = tmp_path / "test.md"
        content = "Very short"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Check minimum tokens",
            file_path="test.md",
            min_count=100,
            params={"provider": "anthropic"},
            failure_message="Too few tokens",
            expected_behavior="Should have at least 100 tokens",
        )

        # Mock the anthropic module
        mock_client = Mock()
        mock_client.count_tokens.return_value = 5
        mock_anthropic = Mock()
        mock_anthropic.Anthropic.return_value = mock_client

        monkeypatch.setitem(sys.modules, "anthropic", mock_anthropic)

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "5 tokens" in result.observed_issue
        assert "below min 100" in result.observed_issue

    def test_computation_type(self, validator):
        """Test that computation_type is programmatic."""
        assert validator.computation_type == "programmatic"

    def test_no_constraints_passes(self, validator, bundle_with_file, monkeypatch):
        """Test that validation passes when no constraints are specified."""
        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="No constraints",
            file_path="test.md",
            params={"provider": "anthropic"},
            failure_message="Error",
            expected_behavior="Should pass",
        )

        # Mock the anthropic module
        mock_client = Mock()
        mock_client.count_tokens.return_value = 500
        mock_anthropic = Mock()
        mock_anthropic.Anthropic.return_value = mock_client

        monkeypatch.setitem(sys.modules, "anthropic", mock_anthropic)

        result = validator.validate(rule, bundle_with_file)
        assert result is None

    def test_tokenizer_exception_handling(self, validator, tmp_path, monkeypatch):
        """Test that exceptions from tokenizer are handled gracefully."""
        test_file = tmp_path / "test.md"
        content = "Test content"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type=ValidationType.TOKEN_COUNT,
            description="Check tokens",
            file_path="test.md",
            max_count=1000,
            params={"provider": "anthropic"},
            failure_message="Error",
            expected_behavior="Should work",
        )

        # Mock the anthropic module to raise an exception
        mock_client = Mock()
        mock_client.count_tokens.side_effect = Exception("Tokenizer error")
        mock_anthropic = Mock()
        mock_anthropic.Anthropic.return_value = mock_client

        monkeypatch.setitem(sys.modules, "anthropic", mock_anthropic)

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Token counting failed" in result.observed_issue
        assert "Tokenizer error" in result.observed_issue
