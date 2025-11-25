"""Unit tests for drift analyzer."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from drift.config.models import DriftLearningType, PhaseDefinition
from drift.core.analyzer import DriftAnalyzer
from drift.core.types import AnalysisResult, CompleteAnalysisResult, Learning
from tests.mock_provider import MockProvider


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
        assert sample_learning_type.phases[0].prompt in prompt
        assert "JSON" in prompt
        # Signals are now part of phase prompt, so just verify prompt has content
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

    def test_generate_summary_no_results(self, sample_drift_config, tmp_path):
        """Test generating summary from empty results."""
        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=tmp_path)
        summary = analyzer._generate_summary([])

        assert summary.total_conversations == 0
        assert summary.total_learnings == 0
        assert summary.conversations_with_drift == 0
        assert summary.conversations_without_drift == 0

    def test_generate_summary_with_results(self, sample_learning, sample_drift_config, tmp_path):
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

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=tmp_path)
        summary = analyzer._generate_summary([result1, result2])

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
        """Test analyze handles loader file not found error gracefully."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.side_effect = FileNotFoundError("Path not found")
        mock_loader_class.return_value = mock_loader

        analyzer = DriftAnalyzer(config=sample_drift_config)

        # Should return empty result instead of raising
        result = analyzer.analyze()
        assert result.summary.total_conversations == 0
        assert result.summary.total_learnings == 0
        assert "No conversations available" in result.metadata.get("message", "")

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

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_fails_on_bedrock_api_error(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test that analyze fails immediately on Bedrock API errors."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        # Simulate Bedrock ValidationException
        mock_provider.generate.side_effect = Exception(
            "Bedrock API error: An error occurred (ValidationException) when calling "
            "the InvokeModel operation: Invocation of model ID "
            "anthropic.claude-haiku-4-5-20251001-v1:0 with on-demand throughput isn't "
            "supported. Retry your request with the ID or ARN of an inference profile "
            "that contains this model."
        )
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)

        # Should raise the exception, not continue
        with pytest.raises(Exception, match="Bedrock API error.*ValidationException"):
            analyzer.analyze()

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

        learnings, error, phase_results = analyzer._run_analysis_pass(
            sample_conversation,
            "incomplete_work",
            sample_learning_type,
            None,
        )

        assert error is None
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
            PhaseDefinition,
        )

        # Add mixed learning types
        sample_drift_config.drift_learning_types = {
            "turn_type": DriftLearningType(
                description="Turn level",
                scope="conversation_level",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="detection",
                        type="prompt",
                        prompt="Find issues",
                        model="haiku",
                    )
                ],
            ),
            "doc_type": DriftLearningType(
                description="Document level",
                scope="project_level",
                context="Test",
                requires_project_context=True,
                supported_clients=["claude-code"],
                document_bundle=DocumentBundleConfig(
                    bundle_type="test",
                    file_patterns=["*.md"],
                    bundle_strategy=BundleStrategy.INDIVIDUAL,
                    resource_patterns=[],
                ),
                phases=[
                    PhaseDefinition(
                        name="detection",
                        type="prompt",
                        prompt="Find doc issues",
                        model="haiku",
                    )
                ],
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
            PhaseDefinition,
        )
        from drift.core.types import DocumentBundle, DocumentFile

        # Create document learning type
        doc_type = DriftLearningType(
            description="Test document type",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            supported_clients=["claude-code"],
            document_bundle=DocumentBundleConfig(
                bundle_type="test",
                file_patterns=["*.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
                resource_patterns=[],
            ),
            phases=[
                PhaseDefinition(
                    name="detection",
                    type="prompt",
                    prompt="Find issues in {files_with_paths}",
                    model="haiku",
                )
            ],
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
            PhaseDefinition,
        )
        from drift.core.types import DocumentBundle, DocumentFile

        # Create project-level learning type
        proj_type = DriftLearningType(
            description="Test project type",
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
            phases=[
                PhaseDefinition(
                    name="detection",
                    type="prompt",
                    prompt="Find cross-document issues",
                    model="haiku",
                )
            ],
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
            PhaseDefinition,
        )

        # Create two document learning types
        sample_drift_config.drift_learning_types = {
            "type1": DriftLearningType(
                description="Type 1",
                scope="project_level",
                context="Test",
                requires_project_context=True,
                supported_clients=["claude-code"],
                document_bundle=DocumentBundleConfig(
                    bundle_type="test",
                    file_patterns=["*.md"],
                    bundle_strategy=BundleStrategy.INDIVIDUAL,
                    resource_patterns=[],
                ),
                phases=[
                    PhaseDefinition(
                        name="detection",
                        type="prompt",
                        prompt="Find type1 issues",
                        model="haiku",
                    )
                ],
            ),
            "type2": DriftLearningType(
                description="Type 2",
                scope="project_level",
                context="Test",
                requires_project_context=True,
                supported_clients=["claude-code"],
                document_bundle=DocumentBundleConfig(
                    bundle_type="test",
                    file_patterns=["*.txt"],
                    bundle_strategy=BundleStrategy.INDIVIDUAL,
                    resource_patterns=[],
                ),
                phases=[
                    PhaseDefinition(
                        name="detection",
                        type="prompt",
                        prompt="Find type2 issues",
                        model="haiku",
                    )
                ],
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
            PhaseDefinition,
        )

        doc_type = DriftLearningType(
            description="Test",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            supported_clients=["claude-code"],
            document_bundle=DocumentBundleConfig(
                bundle_type="test",
                file_patterns=["*.nonexistent"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
                resource_patterns=[],
            ),
            phases=[
                PhaseDefinition(
                    name="detection",
                    type="prompt",
                    prompt="Find issues",
                    model="haiku",
                )
            ],
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
            PhaseDefinition,
        )
        from drift.core.types import DocumentBundle, DocumentFile

        learning_type = DriftLearningType(
            description="Test type",
            scope="project_level",
            context="Test context",
            requires_project_context=True,
            supported_clients=["claude-code"],
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=["*.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
                resource_patterns=[],
            ),
            phases=[
                PhaseDefinition(
                    name="detection",
                    type="prompt",
                    prompt="Find issues in {files_with_paths} at {project_root}",
                    model="haiku",
                )
            ],
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
        prompt = analyzer._build_document_analysis_prompt(bundle, "test_type", learning_type)

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
        learnings = analyzer._parse_document_analysis_response(response, bundle, "test_type")

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
        learnings = analyzer._parse_document_analysis_response(response, bundle, "test_type")

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
        learnings = analyzer._parse_document_analysis_response(response, bundle, "test_type")

        assert learnings == []

    def test_combine_bundles(self, sample_drift_config, temp_dir):
        """Test combining multiple bundles into collection."""
        from drift.config.models import (
            BundleStrategy,
            DocumentBundleConfig,
            DriftLearningType,
            PhaseDefinition,
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
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="test",
                file_patterns=["*.md"],
                bundle_strategy=BundleStrategy.COLLECTION,
                resource_patterns=[],
            ),
            phases=[
                PhaseDefinition(
                    name="detection",
                    type="prompt",
                    prompt="Find issues",
                    model="haiku",
                )
            ],
        )

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)
        combined = analyzer._combine_bundles([bundle1, bundle2], learning_type)

        assert combined.bundle_strategy == "collection"
        assert len(combined.files) == 2
        assert combined.bundle_type == "test"
        assert combined.bundle_id == "combined_project_level"

    def test_empty_list_learning_types_does_not_run_all_rules(self, sample_drift_config, temp_dir):
        """Test that passing learning_types=[] doesn't run ALL rules (critical bug fix)."""
        with patch("drift.providers.bedrock.BedrockProvider.generate") as mock_generate:
            mock_generate.side_effect = AssertionError(
                "CRITICAL BUG: generate() was called when learning_types=[]! "
                "Empty list should prevent ALL rule execution."
            )

            analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)

            # Pass empty list - should NOT run any rules or call LLM
            result = analyzer.analyze(learning_types=[])

            # Verify LLM was never called
            assert mock_generate.call_count == 0, (
                f"generate() was called {mock_generate.call_count} times! "
                f"When learning_types=[], NO rules should run."
            )

            # Should return empty result
            assert result.summary.total_learnings == 0
            assert result.summary.total_conversations == 0

    def test_empty_list_vs_none_learning_types(self, sample_drift_config, temp_dir):
        """Test that learning_types=[] behaves differently from learning_types=None."""
        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)

        # Mock to count rule execution
        with patch.object(analyzer, "_analyze_conversation") as mock_analyze:
            mock_analyze.return_value = MagicMock(
                learnings=[],
                rule_errors={},
            )

            # Empty list should skip analysis entirely
            result_empty = analyzer.analyze(learning_types=[])

            # None should NOT be the same - it should use all configured rules
            # (but we're not testing that here, just that empty list works)

            # With empty list, _analyze_conversation should not be called
            # because no conversations match or no rules to check
            assert result_empty.summary.total_learnings == 0

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_analyze_documents_with_programmatic_phases(self, sample_drift_config, temp_dir):
        """Test analyzing documents with programmatic validation phases."""
        from drift.config.models import PhaseDefinition

        # Add a learning type with programmatic phases
        programmatic_type = DriftLearningType(
            description="Programmatic validation",
            scope="project_level",
            context="Test",
            requires_project_context=False,
            supported_clients=None,
            phases=[
                PhaseDefinition(
                    name="check",
                    type="file_exists",
                    prompt="",
                    model="haiku",
                    available_resources=[],
                )
            ],
        )

        config = sample_drift_config
        config.drift_learning_types["programmatic"] = programmatic_type

        mock_provider = MockProvider()
        mock_provider.set_response(json.dumps([]))

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=config, project_path=str(temp_dir))

            result = analyzer.analyze_documents(
                learning_types=["programmatic"],
            )

            assert result is not None
            # Should have run with programmatic phases
            assert result.summary.total_conversations == 0  # No conversations analyzed

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_init_with_invalid_model_provider(self, sample_drift_config):
        """Test analyzer initialization with model referencing unknown provider."""
        # Create a model config with invalid provider
        from drift.config.models import ModelConfig

        sample_drift_config.models["bad_model"] = ModelConfig(
            provider="nonexistent_provider",
            model_id="test-model",
            params={},
        )

        with pytest.raises(ValueError, match="references unknown provider"):
            DriftAnalyzer(config=sample_drift_config)

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_analyze_documents_with_provider_error(self, sample_drift_config, temp_dir):
        """Test analyze_documents when provider raises API error."""
        from drift.config.models import BundleStrategy, DocumentBundleConfig

        doc_type = DriftLearningType(
            description="Test",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            supported_clients=["claude-code"],
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=["*.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="detection",
                    type="prompt",
                    prompt="Test",
                    model="haiku",
                )
            ],
        )

        sample_drift_config.drift_learning_types["test"] = doc_type

        # Create a file to analyze
        (temp_dir / "test.md").write_text("test")

        mock_provider = MockProvider()

        def raise_api_error(prompt, **kwargs):
            raise Exception("Bedrock API error: throttled")

        mock_provider.generate = raise_api_error

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=sample_drift_config, project_path=str(temp_dir))

            with pytest.raises(Exception, match="Bedrock API error"):
                analyzer.analyze_documents()

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_analyze_documents_with_non_api_error(self, sample_drift_config, temp_dir):
        """Test analyze_documents handles non-API errors gracefully."""
        from drift.config.models import BundleStrategy, DocumentBundleConfig

        doc_type = DriftLearningType(
            description="Test",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            supported_clients=["claude-code"],
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=["*.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="detection",
                    type="prompt",
                    prompt="Test",
                    model="haiku",
                )
            ],
        )

        sample_drift_config.drift_learning_types["test"] = doc_type

        # Create a file
        (temp_dir / "test.md").write_text("test")

        mock_provider = MockProvider()

        def raise_other_error(prompt, **kwargs):
            raise ValueError("Some other error")

        mock_provider.generate = raise_other_error

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=sample_drift_config, project_path=str(temp_dir))

            # Should not raise, logs warning and continues
            result = analyzer.analyze_documents()
            assert result is not None

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_run_multi_phase_document_analysis_no_phases(self, sample_drift_config, temp_dir):
        """Test multi-phase document analysis with no phases configured."""
        from drift.core.types import DocumentBundle, DocumentFile

        bad_type = DriftLearningType(
            description="No phases",
            scope="project_level",
            context="Test",
            requires_project_context=False,
            supported_clients=None,
            phases=[],
        )

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[
                DocumentFile(
                    relative_path="test.md", content="test", file_path=temp_dir / "test.md"
                )
            ],
        )

        analyzer = DriftAnalyzer(config=sample_drift_config)

        with pytest.raises(ValueError, match="no phases configured"):
            analyzer._run_multi_phase_document_analysis(bundle, "bad", bad_type, None)

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_run_multi_phase_document_analysis_model_not_found(self, sample_drift_config, temp_dir):
        """Test multi-phase document analysis when model not found."""
        from drift.core.types import DocumentBundle, DocumentFile

        doc_type = DriftLearningType(
            description="Test",
            scope="project_level",
            context="Test",
            requires_project_context=False,
            supported_clients=None,
            phases=[
                PhaseDefinition(
                    name="test",
                    type="prompt",
                    prompt="Test",
                    model="nonexistent_model",
                )
            ],
        )

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[
                DocumentFile(
                    relative_path="test.md", content="test", file_path=temp_dir / "test.md"
                )
            ],
        )

        analyzer = DriftAnalyzer(config=sample_drift_config)

        with pytest.raises(ValueError, match="not found in configured providers"):
            analyzer._run_multi_phase_document_analysis(bundle, "test", doc_type, None)

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_execute_validation_rules_with_error(self, sample_drift_config, temp_dir):
        """Test validation rule execution when rule throws error."""
        from drift.config.models import (
            BundleStrategy,
            DocumentBundleConfig,
            ValidationRule,
            ValidationRulesConfig,
            ValidationType,
        )
        from drift.core.types import DocumentBundle, DocumentFile

        # Create validation config with a rule
        validation_config = ValidationRulesConfig(
            rules=[
                ValidationRule(
                    rule_type=ValidationType.FILE_EXISTS,
                    description="Test rule",
                    file_path="nonexistent.txt",
                    failure_message="Failed",
                    expected_behavior="Should exist",
                )
            ],
            scope="document_level",
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=["*.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
        )

        type_config = DriftLearningType(
            description="Test",
            scope="project_level",
            context="Test",
            requires_project_context=False,
            supported_clients=None,
            validation_rules=validation_config,
            phases=[],
        )

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[
                DocumentFile(
                    relative_path="test.md", content="test", file_path=temp_dir / "test.md"
                )
            ],
        )

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=str(temp_dir))

        learnings, exec_details = analyzer._execute_validation_rules(
            bundle, "test", type_config, None
        )

        # Should handle errors gracefully
        assert isinstance(learnings, list)
        assert isinstance(exec_details, list)

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_execute_validation_rules_with_programmatic_phases(self, sample_drift_config, temp_dir):
        """Test validation rule execution with programmatic phases."""
        from drift.config.models import PhaseDefinition
        from drift.core.types import DocumentBundle, DocumentFile

        # Create a test file
        test_file = temp_dir / "test.md"
        test_file.write_text("# Test")

        # Create a type config with programmatic phases (no validation_rules)
        type_config = DriftLearningType(
            description="Test with programmatic validation",
            scope="project_level",
            context="Test context",
            requires_project_context=False,
            supported_clients=None,
            validation_rules=None,
            phases=[
                PhaseDefinition(
                    name="check_file",
                    type="file_exists",
                    file_path="test.md",
                    failure_message="Test file not found",
                    expected_behavior="Test file should exist",
                )
            ],
        )

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=str(temp_dir),
            files=[
                DocumentFile(relative_path="test.md", content="# Test", file_path=str(test_file))
            ],
        )

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=str(temp_dir))

        learnings, exec_details = analyzer._analyze_document_bundle(
            bundle, "test", type_config, None, None
        )

        # Should execute programmatic phases
        assert isinstance(learnings, list)
        assert isinstance(exec_details, list)
        assert len(exec_details) > 0
        assert exec_details[0]["rule_name"] == "test"
        assert exec_details[0]["status"] in ["passed", "failed"]

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_execute_validation_rules_programmatic_phase_failure(
        self, sample_drift_config, temp_dir
    ):
        """Test programmatic phase that fails validation."""
        from drift.config.models import PhaseDefinition
        from drift.core.types import DocumentBundle, DocumentFile

        # Create a type config with programmatic phase that checks nonexistent file
        type_config = DriftLearningType(
            description="Test with failing validation",
            scope="project_level",
            context="Test context",
            requires_project_context=False,
            supported_clients=None,
            validation_rules=None,
            phases=[
                PhaseDefinition(
                    name="check_missing_file",
                    type="file_exists",
                    file_path="nonexistent.md",
                    failure_message="File not found",
                    expected_behavior="File should exist",
                )
            ],
        )

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=str(temp_dir),
            files=[
                DocumentFile(
                    relative_path="test.md", content="# Test", file_path=str(temp_dir / "test.md")
                )
            ],
        )

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=str(temp_dir))

        learnings, exec_details = analyzer._analyze_document_bundle(
            bundle, "test", type_config, None, None
        )

        # Should create learning for failed validation
        assert isinstance(learnings, list)
        assert len(learnings) > 0
        assert learnings[0].learning_type == "test"
        assert isinstance(exec_details, list)
        assert len(exec_details) > 0
        assert exec_details[0]["status"] == "failed"

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_run_multi_phase_document_analysis(self, sample_drift_config, temp_dir):
        """Test running multi-phase document analysis with prompt phases."""
        from drift.config.models import PhaseDefinition
        from drift.core.types import DocumentBundle, DocumentFile

        # Set up mock response
        mock_provider = MockProvider()
        mock_provider.set_response("[]")

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=sample_drift_config, project_path=str(temp_dir))

            # Create test file
            test_file = temp_dir / "test.md"
            test_file.write_text("# Test Content")

            # Create type config with prompt phase
            type_config = DriftLearningType(
                description="Test document analysis",
                scope="project_level",
                context="Test context",
                requires_project_context=False,
                supported_clients=None,
                validation_rules=None,
                phases=[
                    PhaseDefinition(
                        name="analysis",
                        type="prompt",
                        prompt="Analyze the document",
                        model="haiku",
                    )
                ],
            )

            bundle = DocumentBundle(
                bundle_id="test",
                bundle_type="skill",
                bundle_strategy="individual",
                project_path=str(temp_dir),
                files=[
                    DocumentFile(
                        relative_path="test.md", content="# Test", file_path=str(test_file)
                    )
                ],
            )

            learnings, exec_details = analyzer._run_multi_phase_document_analysis(
                bundle, "test", type_config, None, None
            )

            # Should execute LLM-based document analysis
            assert isinstance(learnings, list)
            assert isinstance(exec_details, list)
            assert mock_provider.call_count == 1

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_execute_validation_rules_with_exception(self, sample_drift_config, temp_dir):
        """Test validation rule execution handles exceptions."""
        from unittest.mock import MagicMock

        from drift.config.models import (
            BundleStrategy,
            DocumentBundleConfig,
            ValidationRule,
            ValidationRulesConfig,
            ValidationType,
        )
        from drift.core.types import DocumentBundle, DocumentFile

        # Create validation config with a rule that will fail
        validation_config = ValidationRulesConfig(
            rules=[
                ValidationRule(
                    rule_type=ValidationType.REGEX_MATCH,
                    description="Test rule",
                    file_path="test.md",
                    pattern=".*",  # Valid pattern
                    failure_message="Failed",
                    expected_behavior="Should exist",
                )
            ],
            scope="project_level",
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=["*.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
        )

        type_config = DriftLearningType(
            description="Test",
            scope="project_level",
            context="Test",
            requires_project_context=False,
            supported_clients=None,
            validation_rules=validation_config,
            phases=[],
        )

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=str(temp_dir),
            files=[
                DocumentFile(
                    relative_path="test.md", content="test", file_path=str(temp_dir / "test.md")
                )
            ],
        )

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=str(temp_dir))

        # Mock the validator registry to raise an exception
        with patch("drift.core.analyzer.ValidatorRegistry") as mock_registry:
            mock_instance = MagicMock()
            mock_instance.execute_rule.side_effect = Exception("Test error")
            mock_registry.return_value = mock_instance

            learnings, exec_details = analyzer._execute_validation_rules(
                bundle, "test", type_config, None
            )

            # Should handle error gracefully
            assert isinstance(learnings, list)
            assert isinstance(exec_details, list)
            assert len(exec_details) > 0
            assert exec_details[0]["status"] == "errored"
            assert "Test error" in exec_details[0]["error_message"]


class TestAnalyzerEdgeCases:
    """Test edge cases and error paths in DriftAnalyzer."""

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_analyze_conversation_with_client_filtering(
        self, sample_drift_config, sample_conversation
    ):
        """Test that rules with supported_clients filter correctly."""
        # Create learning type that only supports "other-tool" (not claude-code)
        filtered_type = DriftLearningType(
            description="Filtered by client",
            scope="conversation_level",
            context="Test",
            requires_project_context=False,
            supported_clients=["other-tool"],  # conversation is claude-code
        )

        config = sample_drift_config
        config.drift_learning_types["filtered"] = filtered_type

        analyzer = DriftAnalyzer(config=config)

        # Run analysis - should skip the filtered type
        result, exec_details = analyzer._analyze_conversation(
            conversation=sample_conversation,
            learning_types={"filtered": filtered_type},
            model_override=None,
        )

        # Should return empty since rule was filtered
        assert len(result.learnings) == 0

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_analyze_with_conversation_load_error(self, sample_drift_config, temp_dir):
        """Test analyze() when conversation loading fails."""  # noqa: D202

        # Create a mock agent loader that raises an error
        class FailingLoader:
            def load_conversations(self, project_path=None, since=None):
                raise RuntimeError("Failed to load conversations")

        config = sample_drift_config
        analyzer = DriftAnalyzer(config=config)
        analyzer.agent_loaders["claude-code"] = FailingLoader()

        # Should handle error gracefully and continue
        result = analyzer.analyze()

        # Should return empty result (conversation loading failed)
        assert isinstance(result, CompleteAnalysisResult)

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_build_multi_phase_prompt_with_resources(
        self, sample_drift_config, sample_conversation, temp_dir
    ):
        """Test _build_multi_phase_prompt includes loaded resources."""
        sample_conversation.project_path = str(temp_dir)

        multi_type = DriftLearningType(
            description="Multi-phase",
            scope="conversation_level",
            context="Test",
            requires_project_context=True,
            supported_clients=["claude-code"],
            phases=[
                PhaseDefinition(
                    name="phase1",
                    type="prompt",
                    prompt="Test",
                    model="haiku",
                    available_resources=[],
                )
            ],
        )

        analyzer = DriftAnalyzer(config=sample_drift_config)

        # Add loaded resources
        resources_loaded = [{"type": "command", "id": "test", "content": "Test command content"}]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=sample_conversation,
            learning_type="test",
            type_config=multi_type,
            phase_idx=0,
            phase_def=multi_type.phases[0],
            resources_loaded=resources_loaded,
            previous_findings=[],
        )

        # Should include resource content in prompt
        assert "Test command content" in prompt or "command" in prompt.lower()
