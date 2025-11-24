"""Unit tests for drift analyzer."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from drift.core.analyzer import DriftAnalyzer
from drift.core.types import AnalysisResult, CompleteAnalysisResult, Learning


class TestDriftAnalyzer:
    """Tests for DriftAnalyzer class."""

    def test_initialization_with_config(self, sample_drift_config):
        """Test analyzer initialization with provided config."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        assert analyzer.config == sample_drift_config
        assert analyzer.project_path is None
        assert len(analyzer.providers) > 0
        assert len(analyzer.agent_loaders) > 0

    @patch("drift.core.analyzer.ConfigLoader.load_config")
    def test_initialization_loads_config(self, mock_load_config, sample_drift_config):
        """Test analyzer loads config when not provided."""
        mock_load_config.return_value = sample_drift_config

        analyzer = DriftAnalyzer()

        mock_load_config.assert_called_once()
        assert analyzer.config == sample_drift_config

    def test_initialization_with_project_path(self, sample_drift_config, temp_dir):
        """Test analyzer initialization with project path."""
        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)

        assert analyzer.project_path == temp_dir

    def test_initialize_providers(self, sample_drift_config):
        """Test provider initialization."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        assert "haiku" in analyzer.providers
        assert analyzer.providers["haiku"].get_provider_type() == "bedrock"

    def test_initialize_agent_loaders(self, sample_drift_config):
        """Test agent loader initialization."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        assert "claude-code" in analyzer.agent_loaders
        assert analyzer.agent_loaders["claude-code"].agent_name == "claude-code"

    def test_format_conversation(self, sample_conversation):
        """Test conversation formatting for prompts."""
        formatted = DriftAnalyzer._format_conversation(sample_conversation)

        assert "[Turn 1]" in formatted
        assert "User:" in formatted
        assert "AI:" in formatted
        assert sample_conversation.turns[0].user_message in formatted
        assert sample_conversation.turns[0].ai_message in formatted

    def test_build_analysis_prompt(self, sample_conversation, sample_learning_type):
        """Test building analysis prompt."""
        analyzer = DriftAnalyzer(config=MagicMock())

        prompt = analyzer._build_analysis_prompt(
            sample_conversation,
            "incomplete_work",
            sample_learning_type,
        )

        assert "incomplete_work" in prompt
        assert sample_learning_type.description in prompt
        assert sample_learning_type.detection_prompt in prompt
        assert "JSON" in prompt
        # Signals are now part of detection_prompt, so just verify prompt has content
        assert len(prompt) > 100

    def test_parse_analysis_response_valid(self, sample_conversation):
        """Test parsing valid analysis response."""
        response = json.dumps(
            [
                {
                    "turn_number": 1,
                    "observed_behavior": "Did something",
                    "expected_behavior": "Wanted something else",
                    "resolved": True,
                    "still_needs_action": False,
                    "context": "Test context",
                }
            ]
        )

        learnings = DriftAnalyzer._parse_analysis_response(
            response,
            sample_conversation,
            "incomplete_work",
        )

        assert len(learnings) == 1
        assert isinstance(learnings[0], Learning)
        assert learnings[0].turn_number == 1
        assert learnings[0].learning_type == "incomplete_work"

    def test_parse_analysis_response_empty(self, sample_conversation):
        """Test parsing empty analysis response."""
        response = "[]"

        learnings = DriftAnalyzer._parse_analysis_response(
            response,
            sample_conversation,
            "incomplete_work",
        )

        assert learnings == []

    def test_parse_analysis_response_with_text(self, sample_conversation):
        """Test parsing response with extra text around JSON."""
        response = (
            "Here's my analysis:\n\n"
            '[{"turn_number": 1, "observed_behavior": "Test", "expected_behavior": "Test", '
            '"resolved": true, "still_needs_action": false, "context": "Test"}]\n\n'
            "That's all I found."
        )

        learnings = DriftAnalyzer._parse_analysis_response(
            response,
            sample_conversation,
            "test_type",
        )

        assert len(learnings) == 1

    def test_parse_analysis_response_invalid_json(self, sample_conversation):
        """Test parsing response with invalid JSON."""
        response = "This is not JSON at all"

        learnings = DriftAnalyzer._parse_analysis_response(
            response,
            sample_conversation,
            "test_type",
        )

        assert learnings == []

    def test_parse_analysis_response_no_json_array(self, sample_conversation):
        """Test parsing response without JSON array."""
        response = '{"not": "an array"}'

        learnings = DriftAnalyzer._parse_analysis_response(
            response,
            sample_conversation,
            "test_type",
        )

        assert learnings == []

    def test_generate_summary_no_results(self):
        """Test generating summary from empty results."""
        summary = DriftAnalyzer._generate_summary([])

        assert summary.total_conversations == 0
        assert summary.total_learnings == 0
        assert summary.conversations_with_drift == 0
        assert summary.conversations_without_drift == 0

    def test_generate_summary_with_results(self, sample_learning):
        """Test generating summary from results."""
        result1 = AnalysisResult(
            session_id="session1",
            agent_tool="claude-code",
            conversation_file="/path1",
            learnings=[sample_learning],
            analysis_timestamp=datetime.now(),
        )

        result2 = AnalysisResult(
            session_id="session2",
            agent_tool="claude-code",
            conversation_file="/path2",
            learnings=[],  # No drift
            analysis_timestamp=datetime.now(),
        )

        summary = DriftAnalyzer._generate_summary([result1, result2])

        assert summary.total_conversations == 2
        assert summary.total_learnings == 1
        assert summary.conversations_with_drift == 1
        assert summary.conversations_without_drift == 1
        assert "incomplete_work" in summary.by_type
        assert summary.by_type["incomplete_work"] == 1

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_creates_temp_dir(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
        temp_dir,
    ):
        """Test that analyze creates temporary analysis directory."""
        # Setup mocks
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = "[]"
        mock_provider_class.return_value = mock_provider

        # Override temp_dir in config
        sample_drift_config.temp_dir = str(temp_dir / "drift-analysis")

        analyzer = DriftAnalyzer(config=sample_drift_config)
        result = analyzer.analyze()

        # Check that temp directory was used
        assert isinstance(result, CompleteAnalysisResult)
        # Verify temp manager was used (session_id should be in metadata)
        assert "session_id" in result.metadata

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_end_to_end(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test full analyze workflow."""
        # Setup loader mock
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        # Setup provider mock
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = json.dumps(
            [
                {
                    "turn_number": 1,
                    "observed_behavior": "Test action",
                    "expected_behavior": "Test intent",
                    "resolved": True,
                    "still_needs_action": False,
                    "context": "Test",
                }
            ]
        )
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        result = analyzer.analyze()

        assert isinstance(result, CompleteAnalysisResult)
        assert result.summary.total_conversations == 1
        assert len(result.results) == 1
        assert len(result.results[0].learnings) == 1

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_with_agent_filter(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test analyze with specific agent tool filter."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = "[]"
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        analyzer.analyze(agent_tool="claude-code")

        # Should only analyze specified agent
        mock_loader.load_conversations.assert_called_once()

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_with_learning_type_filter(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test analyze with specific learning types."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = "[]"
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        analyzer.analyze(learning_types=["incomplete_work"])

        # Should only check specified learning types
        assert mock_provider.generate.call_count == 1  # One conversation * one learning type

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_with_model_override(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test analyze with model override."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = "[]"
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        analyzer.analyze(model_override="haiku")

        # Model override should be used
        assert mock_provider.generate.called

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_provider_not_available(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test analyze handles provider not available."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = False
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)

        with pytest.raises(RuntimeError) as exc_info:
            analyzer.analyze()
        assert "not available" in str(exc_info.value)

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    def test_analyze_loader_not_found_error(
        self,
        mock_loader_class,
        sample_drift_config,
    ):
        """Test analyze handles loader file not found error."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.side_effect = FileNotFoundError("Path not found")
        mock_loader_class.return_value = mock_loader

        analyzer = DriftAnalyzer(config=sample_drift_config)

        with pytest.raises(FileNotFoundError):
            analyzer.analyze()

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_continues_on_conversation_error(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test that analyze continues when individual conversations fail."""
        mock_loader = MagicMock()
        # Return two conversations
        conv2 = sample_conversation.model_copy()
        conv2.session_id = "session2"
        mock_loader.load_conversations.return_value = [sample_conversation, conv2]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        # First conversation succeeds, second fails
        mock_provider.generate.side_effect = ["[]", Exception("API Error")]
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        result = analyzer.analyze()

        # Should have analyzed both (second with error)
        assert len(result.results) == 1  # Only successful one

    def test_cleanup(self, sample_drift_config, temp_dir):
        """Test analyzer cleanup."""
        sample_drift_config.temp_dir = str(temp_dir / "drift-temp")
        analyzer = DriftAnalyzer(config=sample_drift_config)

        # Should not raise error
        analyzer.cleanup()

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_saves_metadata(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test that analyze saves metadata."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = "[]"
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        result = analyzer.analyze()

        # Check metadata
        assert "generated_at" in result.metadata
        assert "session_id" in result.metadata
        assert "config_used" in result.metadata

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_run_analysis_pass(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
        sample_learning_type,
    ):
        """Test running a single analysis pass."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = json.dumps(
            [
                {
                    "turn_number": 1,
                    "observed_behavior": "Action",
                    "expected_behavior": "Intent",
                    "resolved": False,
                    "still_needs_action": True,
                    "context": "Context",
                }
            ]
        )
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        analyzer.providers = {"haiku": mock_provider}

        learnings = analyzer._run_analysis_pass(
            sample_conversation,
            "incomplete_work",
            sample_learning_type,
            None,
        )

        assert len(learnings) == 1
        assert learnings[0].learning_type == "incomplete_work"

    def test_run_analysis_pass_unknown_model(
        self,
        sample_drift_config,
        sample_conversation,
        sample_learning_type,
    ):
        """Test that run_analysis_pass fails with unknown model."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        with pytest.raises(ValueError) as exc_info:
            analyzer._run_analysis_pass(
                sample_conversation,
                "incomplete_work",
                sample_learning_type,
                "nonexistent_model",
            )
        assert "not found in configured providers" in str(exc_info.value)

    @patch("drift.core.analyzer.DocumentLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_documents_no_project_path(
        self, mock_provider_class, mock_loader_class, sample_drift_config
    ):
        """Test analyze_documents requires project_path."""
        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=None)

        with pytest.raises(ValueError) as exc_info:
            analyzer.analyze_documents()
        assert "project path" in str(exc_info.value).lower()

    @patch("drift.core.analyzer.DocumentLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_documents_filters_learning_types(
        self, mock_provider_class, mock_loader_class, sample_drift_config, temp_dir
    ):
        """Test analyze_documents filters to only document learning types."""
        from drift.config.models import (
            BundleStrategy,
            DocumentBundleConfig,
            DriftLearningType,
        )

        # Add mixed learning types
        sample_drift_config.drift_learning_types = {
            "turn_type": DriftLearningType(
                description="Turn level",
                detection_prompt="Find issues",
                analysis_method="ai_analyzed",
                scope="turn_level",
                context="Test",
                requires_project_context=False,
            ),
            "doc_type": DriftLearningType(
                description="Document level",
                detection_prompt="Find doc issues",
                analysis_method="ai_analyzed",
                scope="document_level",
                context="Test",
                requires_project_context=True,
                supported_clients=["claude-code"],
                document_bundle=DocumentBundleConfig(
                    bundle_type="test",
                    file_patterns=["*.md"],
                    bundle_strategy=BundleStrategy.INDIVIDUAL,
                    resource_patterns=[],
                ),
            ),
        }

        mock_loader = MagicMock()
        mock_loader.load_bundles.return_value = []
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)
        analyzer.analyze_documents()

        # Should only load bundles once (for doc_type, not turn_type)
        assert mock_loader.load_bundles.call_count == 1

    @patch("drift.core.analyzer.DocumentLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_documents_document_level(
        self, mock_provider_class, mock_loader_class, sample_drift_config, temp_dir
    ):
        """Test analyze_documents with document_level scope."""
        from drift.config.models import (
            BundleStrategy,
            DocumentBundleConfig,
            DriftLearningType,
        )
        from drift.core.types import DocumentBundle, DocumentFile

        # Create document learning type
        doc_type = DriftLearningType(
            description="Test document type",
            detection_prompt="Find issues in {files_with_paths}",
            analysis_method="ai_analyzed",
            scope="document_level",
            context="Test",
            requires_project_context=True,
            supported_clients=["claude-code"],
            document_bundle=DocumentBundleConfig(
                bundle_type="test",
                file_patterns=["*.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
                resource_patterns=[],
            ),
        )
        sample_drift_config.drift_learning_types = {"doc_test": doc_type}

        # Create mock bundles
        bundle1 = DocumentBundle(
            bundle_id="bundle1",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[
                DocumentFile(
                    relative_path="test1.md",
                    content="content1",
                    file_path=temp_dir / "test1.md",
                )
            ],
        )
        bundle2 = DocumentBundle(
            bundle_id="bundle2",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[
                DocumentFile(
                    relative_path="test2.md",
                    content="content2",
                    file_path=temp_dir / "test2.md",
                )
            ],
        )

        mock_loader = MagicMock()
        mock_loader.load_bundles.return_value = [bundle1, bundle2]
        mock_loader.format_bundle_for_llm.return_value = "formatted content"
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = json.dumps(
            [
                {
                    "file_paths": ["test1.md"],
                    "observed_issue": "Issue found",
                    "expected_quality": "Should be better",
                    "context": "Test context",
                }
            ]
        )
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)
        result = analyzer.analyze_documents()

        # Should analyze each bundle separately
        assert mock_provider.generate.call_count == 2
        assert "document_learnings" in result.metadata
        assert len(result.metadata["document_learnings"]) == 2

    @patch("drift.core.analyzer.DocumentLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_documents_project_level(
        self, mock_provider_class, mock_loader_class, sample_drift_config, temp_dir
    ):
        """Test analyze_documents with project_level scope."""
        from drift.config.models import (
            BundleStrategy,
            DocumentBundleConfig,
            DriftLearningType,
        )
        from drift.core.types import DocumentBundle, DocumentFile

        # Create project-level learning type
        proj_type = DriftLearningType(
            description="Test project type",
            detection_prompt="Find cross-document issues",
            analysis_method="ai_analyzed",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            supported_clients=["claude-code"],
            document_bundle=DocumentBundleConfig(
                bundle_type="mixed",
                file_patterns=["*.md"],
                bundle_strategy=BundleStrategy.COLLECTION,
                resource_patterns=[],
            ),
        )
        sample_drift_config.drift_learning_types = {"proj_test": proj_type}

        # Create mock bundles
        bundle1 = DocumentBundle(
            bundle_id="bundle1",
            bundle_type="mixed",
            bundle_strategy="collection",
            project_path=temp_dir,
            files=[
                DocumentFile(
                    relative_path="test1.md",
                    content="content1",
                    file_path=temp_dir / "test1.md",
                ),
                DocumentFile(
                    relative_path="test2.md",
                    content="content2",
                    file_path=temp_dir / "test2.md",
                ),
            ],
        )

        mock_loader = MagicMock()
        mock_loader.load_bundles.return_value = [bundle1]
        mock_loader.format_bundle_for_llm.return_value = "formatted content"
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = json.dumps(
            [
                {
                    "file_paths": ["test1.md", "test2.md"],
                    "observed_issue": "Contradiction found",
                    "expected_quality": "Should be consistent",
                    "context": "Test context",
                }
            ]
        )
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)
        result = analyzer.analyze_documents()

        # Should analyze combined bundle once (max 1 for project level)
        assert mock_provider.generate.call_count == 1
        assert "document_learnings" in result.metadata
        # Project level should have max 1 learning
        assert len(result.metadata["document_learnings"]) == 1

    @patch("drift.core.analyzer.DocumentLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_documents_with_learning_type_filter(
        self, mock_provider_class, mock_loader_class, sample_drift_config, temp_dir
    ):
        """Test analyze_documents with specific learning type filter."""
        from drift.config.models import (
            BundleStrategy,
            DocumentBundleConfig,
            DriftLearningType,
        )

        # Create two document learning types
        sample_drift_config.drift_learning_types = {
            "type1": DriftLearningType(
                description="Type 1",
                detection_prompt="Find type1 issues",
                analysis_method="ai_analyzed",
                scope="document_level",
                context="Test",
                requires_project_context=True,
                supported_clients=["claude-code"],
                document_bundle=DocumentBundleConfig(
                    bundle_type="test",
                    file_patterns=["*.md"],
                    bundle_strategy=BundleStrategy.INDIVIDUAL,
                    resource_patterns=[],
                ),
            ),
            "type2": DriftLearningType(
                description="Type 2",
                detection_prompt="Find type2 issues",
                analysis_method="ai_analyzed",
                scope="document_level",
                context="Test",
                requires_project_context=True,
                supported_clients=["claude-code"],
                document_bundle=DocumentBundleConfig(
                    bundle_type="test",
                    file_patterns=["*.txt"],
                    bundle_strategy=BundleStrategy.INDIVIDUAL,
                    resource_patterns=[],
                ),
            ),
        }

        mock_loader = MagicMock()
        mock_loader.load_bundles.return_value = []
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)
        analyzer.analyze_documents(learning_types=["type1"])

        # Should only load bundles for type1
        assert mock_loader.load_bundles.call_count == 1

    @patch("drift.core.analyzer.DocumentLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_documents_handles_empty_bundles(
        self, mock_provider_class, mock_loader_class, sample_drift_config, temp_dir
    ):
        """Test analyze_documents handles no matching files gracefully."""
        from drift.config.models import (
            BundleStrategy,
            DocumentBundleConfig,
            DriftLearningType,
        )

        doc_type = DriftLearningType(
            description="Test",
            detection_prompt="Find issues",
            analysis_method="ai_analyzed",
            scope="document_level",
            context="Test",
            requires_project_context=True,
            supported_clients=["claude-code"],
            document_bundle=DocumentBundleConfig(
                bundle_type="test",
                file_patterns=["*.nonexistent"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
                resource_patterns=[],
            ),
        )
        sample_drift_config.drift_learning_types = {"test": doc_type}

        mock_loader = MagicMock()
        mock_loader.load_bundles.return_value = []  # No bundles found
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)
        result = analyzer.analyze_documents()

        # Should not call provider if no bundles
        assert mock_provider.generate.call_count == 0
        assert result.metadata["document_learnings"] == []

    def test_build_document_analysis_prompt(self, sample_drift_config, temp_dir):
        """Test building document analysis prompt."""
        from drift.config.models import (
            BundleStrategy,
            DocumentBundleConfig,
            DriftLearningType,
        )
        from drift.core.types import DocumentBundle, DocumentFile

        learning_type = DriftLearningType(
            description="Test type",
            detection_prompt="Find issues in {files_with_paths} at {project_root}",
            analysis_method="ai_analyzed",
            scope="document_level",
            context="Test context",
            requires_project_context=True,
            supported_clients=["claude-code"],
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=["*.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
                resource_patterns=[],
            ),
        )

        bundle = DocumentBundle(
            bundle_id="test_bundle",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content="test content",
                    file_path=temp_dir / "test.md",
                )
            ],
        )

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)
        prompt = analyzer._build_document_analysis_prompt(
            bundle, "test_type", learning_type
        )

        assert "test_type" in prompt
        assert learning_type.description in prompt
        assert "skill" in prompt  # bundle_type
        assert "JSON" in prompt
        assert len(prompt) > 100

    def test_parse_document_analysis_response_valid(self, sample_drift_config, temp_dir):
        """Test parsing valid document analysis response."""
        from drift.core.types import DocumentBundle

        bundle = DocumentBundle(
            bundle_id="test_bundle",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[],
        )

        # Response doesn't include bundle_id - that's added from the bundle param
        response = json.dumps(
            [
                {
                    "file_paths": ["test.md"],
                    "observed_issue": "Issue found",
                    "expected_quality": "Should be better",
                    "context": "Test context",
                }
            ]
        )

        analyzer = DriftAnalyzer(config=sample_drift_config)
        learnings = analyzer._parse_document_analysis_response(
            response, bundle, "test_type"
        )

        assert len(learnings) == 1
        assert learnings[0].bundle_id == "test_bundle"
        assert learnings[0].learning_type == "test_type"
        assert learnings[0].observed_issue == "Issue found"

    def test_parse_document_analysis_response_empty(self, sample_drift_config, temp_dir):
        """Test parsing empty document analysis response."""
        from drift.core.types import DocumentBundle

        bundle = DocumentBundle(
            bundle_id="test_bundle",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[],
        )

        response = "[]"

        analyzer = DriftAnalyzer(config=sample_drift_config)
        learnings = analyzer._parse_document_analysis_response(
            response, bundle, "test_type"
        )

        assert learnings == []

    def test_parse_document_analysis_response_invalid_json(self, sample_drift_config, temp_dir):
        """Test parsing invalid JSON in document analysis response."""
        from drift.core.types import DocumentBundle

        bundle = DocumentBundle(
            bundle_id="test_bundle",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[],
        )

        response = "This is not valid JSON"

        analyzer = DriftAnalyzer(config=sample_drift_config)
        learnings = analyzer._parse_document_analysis_response(
            response, bundle, "test_type"
        )

        assert learnings == []

    def test_combine_bundles(self, sample_drift_config, temp_dir):
        """Test combining multiple bundles into collection."""
        from drift.config.models import (
            BundleStrategy,
            DocumentBundleConfig,
            DriftLearningType,
        )
        from drift.core.types import DocumentBundle, DocumentFile

        bundle1 = DocumentBundle(
            bundle_id="bundle1",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[
                DocumentFile(
                    relative_path="test1.md",
                    content="content1",
                    file_path=temp_dir / "test1.md",
                )
            ],
        )
        bundle2 = DocumentBundle(
            bundle_id="bundle2",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[
                DocumentFile(
                    relative_path="test2.md",
                    content="content2",
                    file_path=temp_dir / "test2.md",
                )
            ],
        )

        learning_type = DriftLearningType(
            description="Test",
            detection_prompt="Find issues",
            analysis_method="ai_analyzed",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="test",
                file_patterns=["*.md"],
                bundle_strategy=BundleStrategy.COLLECTION,
                resource_patterns=[],
            ),
        )

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)
        combined = analyzer._combine_bundles([bundle1, bundle2], learning_type)

        assert combined.bundle_strategy == "collection"
        assert len(combined.files) == 2
        assert combined.bundle_type == "test"
        assert combined.bundle_id == "combined_project_level"
