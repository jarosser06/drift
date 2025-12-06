"""Tests for parallel execution functionality."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from drift.config.models import DriftConfig, ParallelExecutionConfig, ValidationRule
from drift.core.analyzer import DriftAnalyzer
from drift.core.types import DocumentBundle, DocumentFile, DocumentRule


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory."""
    project = tmp_path / "test_project"
    project.mkdir()
    return project


@pytest.fixture
def mock_config():
    """Create a mock DriftConfig with parallel execution enabled."""
    config = Mock(spec=DriftConfig)
    config.parallel_execution = ParallelExecutionConfig(enabled=True)
    config.cache_enabled = False
    config.cache_dir = ".drift/cache"
    config.cache_ttl = 86400
    config.temp_dir = "/tmp/drift"
    config.providers = {}
    config.models = {}
    config.rule_definitions = {}
    config.get_enabled_agent_tools.return_value = {}
    return config


@pytest.fixture
def mock_bundle():
    """Create a mock DocumentBundle for testing."""
    bundle = Mock(spec=DocumentBundle)
    bundle.bundle_id = "test_bundle"
    bundle.bundle_type = "test"
    bundle.files = [Mock(spec=DocumentFile, relative_path="test.txt", content="test content")]
    bundle.project_path = Path("/test/project")
    return bundle


@pytest.fixture
def sample_validation_rules():
    """Create sample validation rules for testing."""
    return [
        ValidationRule(
            rule_type="core:file_exists",
            description="Test rule 1",
            file_path="test1.txt",
            failure_message="File test1.txt should exist",
            expected_behavior="File should exist",
        ),
        ValidationRule(
            rule_type="core:file_exists",
            description="Test rule 2",
            file_path="test2.txt",
            failure_message="File test2.txt should exist",
            expected_behavior="File should exist",
        ),
        ValidationRule(
            rule_type="core:file_exists",
            description="Test rule 3",
            file_path="test3.txt",
            failure_message="File test3.txt should exist",
            expected_behavior="File should exist",
        ),
    ]


class TestParallelExecutionConfig:
    """Test ParallelExecutionConfig model."""

    def test_default_enabled_true(self):
        """Test that parallel execution is enabled by default."""
        config = ParallelExecutionConfig()
        assert config.enabled is True

    def test_can_disable_parallel_execution(self):
        """Test that parallel execution can be disabled."""
        config = ParallelExecutionConfig(enabled=False)
        assert config.enabled is False


class TestDriftConfigIntegration:
    """Test integration of ParallelExecutionConfig with DriftConfig."""

    def test_drift_config_has_parallel_execution_field(self):
        """Test that DriftConfig includes parallel_execution field."""
        config = DriftConfig(
            providers={},
            models={},
            rule_definitions={},
        )
        assert hasattr(config, "parallel_execution")
        assert isinstance(config.parallel_execution, ParallelExecutionConfig)

    def test_parallel_execution_default_enabled(self):
        """Test that parallel execution is enabled by default in DriftConfig."""
        config = DriftConfig(
            providers={},
            models={},
            rule_definitions={},
        )
        assert config.parallel_execution.enabled is True

    def test_can_override_parallel_execution_in_config(self):
        """Test that parallel execution can be disabled in DriftConfig."""
        config = DriftConfig(
            providers={},
            models={},
            rule_definitions={},
            parallel_execution=ParallelExecutionConfig(enabled=False),
        )
        assert config.parallel_execution.enabled is False


class TestExecutionRouting:
    """Test execution routing between parallel and sequential."""

    @patch("drift.core.analyzer.ValidatorRegistry")
    def test_single_rule_uses_sequential(
        self, mock_registry_class, mock_config, mock_bundle, temp_project
    ):
        """Test that single rule falls back to sequential execution."""
        # Setup
        mock_registry = Mock()
        mock_registry.execute_rule.return_value = None
        mock_registry_class.return_value = mock_registry

        analyzer = DriftAnalyzer(config=mock_config, project_path=temp_project)

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Single test rule",
            file_path="test.txt",
            failure_message="File should exist",
            expected_behavior="File should exist",
        )

        type_config = Mock()
        type_config.validation_rules = Mock()
        type_config.validation_rules.rules = [rule]

        # Execute
        with patch.object(
            analyzer, "_execute_rules_sequential", wraps=analyzer._execute_rules_sequential
        ) as mock_sequential:
            with patch.object(analyzer, "_execute_rules_parallel") as mock_parallel:
                analyzer._execute_validation_rules(mock_bundle, "test_rule", type_config, None)

                # Verify sequential was called, parallel was not
                mock_sequential.assert_called_once()
                mock_parallel.assert_not_called()

    @patch("drift.core.analyzer.ValidatorRegistry")
    def test_multiple_rules_use_parallel_when_enabled(
        self, mock_registry_class, mock_config, mock_bundle, temp_project
    ):
        """Test that multiple rules use parallel execution when enabled."""
        # Setup
        mock_registry = Mock()
        mock_registry.execute_rule.return_value = None
        mock_registry_class.return_value = mock_registry

        analyzer = DriftAnalyzer(config=mock_config, project_path=temp_project)

        rules = [
            ValidationRule(
                rule_type="core:file_exists",
                description=f"Test rule {i}",
                file_path=f"test{i}.txt",
                failure_message=f"File test{i}.txt should exist",
                expected_behavior="File should exist",
            )
            for i in range(3)
        ]

        type_config = Mock()
        type_config.validation_rules = Mock()
        type_config.validation_rules.rules = rules

        # Execute - this should actually run parallel execution
        doc_rules, execution_details = analyzer._execute_validation_rules(
            mock_bundle, "test_rule", type_config, None
        )

        # Verify all rules were executed
        assert len(execution_details) == 3
        assert all(d["status"] == "passed" for d in execution_details)

    @patch("drift.core.analyzer.ValidatorRegistry")
    def test_parallel_disabled_uses_sequential(
        self, mock_registry_class, mock_bundle, temp_project
    ):
        """Test that disabling parallel execution uses sequential."""
        # Setup
        config = Mock(spec=DriftConfig)
        config.parallel_execution = ParallelExecutionConfig(enabled=False)
        config.cache_enabled = False
        config.cache_dir = ".drift/cache"
        config.cache_ttl = 86400
        config.temp_dir = "/tmp/drift"
        config.providers = {}
        config.models = {}
        config.rule_definitions = {}
        config.get_enabled_agent_tools.return_value = {}

        mock_registry = Mock()
        mock_registry.execute_rule.return_value = None
        mock_registry_class.return_value = mock_registry

        analyzer = DriftAnalyzer(config=config, project_path=temp_project)

        rules = [
            ValidationRule(
                rule_type="core:file_exists",
                description=f"Test rule {i}",
                file_path=f"test{i}.txt",
                failure_message=f"File test{i}.txt should exist",
                expected_behavior="File should exist",
            )
            for i in range(3)
        ]

        type_config = Mock()
        type_config.validation_rules = Mock()
        type_config.validation_rules.rules = rules

        # Execute - should use sequential since parallel is disabled
        doc_rules, execution_details = analyzer._execute_validation_rules(
            mock_bundle, "test_rule", type_config, None
        )

        # Verify all rules were executed
        assert len(execution_details) == 3
        assert all(d["status"] == "passed" for d in execution_details)


class TestSequentialExecution:
    """Test sequential execution logic."""

    @patch("drift.core.analyzer.ValidatorRegistry")
    def test_sequential_executes_all_rules(
        self, mock_registry_class, mock_config, mock_bundle, sample_validation_rules, temp_project
    ):
        """Test that sequential execution runs all rules."""
        # Setup
        mock_registry = Mock()
        mock_registry.execute_rule.return_value = None
        mock_registry_class.return_value = mock_registry

        analyzer = DriftAnalyzer(config=mock_config, project_path=temp_project)

        # Execute
        doc_rules, execution_details = analyzer._execute_rules_sequential(
            sample_validation_rules, mock_bundle, "test_rule", None
        )

        # Verify all rules were executed
        assert mock_registry.execute_rule.call_count == 3
        assert len(execution_details) == 3

    @patch("drift.core.analyzer.ValidatorRegistry")
    def test_sequential_continues_on_error(
        self, mock_registry_class, mock_config, mock_bundle, sample_validation_rules, temp_project
    ):
        """Test that sequential execution continues when a rule errors."""
        # Setup
        mock_registry = Mock()
        # First rule errors, others succeed
        mock_registry.execute_rule.side_effect = [
            Exception("Test error"),
            None,
            None,
        ]
        mock_registry_class.return_value = mock_registry

        analyzer = DriftAnalyzer(config=mock_config, project_path=temp_project)

        # Execute
        doc_rules, execution_details = analyzer._execute_rules_sequential(
            sample_validation_rules, mock_bundle, "test_rule", None
        )

        # Verify all rules were attempted
        assert mock_registry.execute_rule.call_count == 3
        assert len(execution_details) == 3

        # First rule should be marked as errored
        assert execution_details[0]["status"] == "errored"
        assert "error_message" in execution_details[0]

        # Other rules should be marked as passed
        assert execution_details[1]["status"] == "passed"
        assert execution_details[2]["status"] == "passed"

    @patch("drift.core.analyzer.ValidatorRegistry")
    def test_sequential_tracks_failed_validations(
        self, mock_registry_class, mock_config, mock_bundle, sample_validation_rules, temp_project
    ):
        """Test that sequential execution tracks failed validations."""
        # Setup
        mock_registry = Mock()
        mock_failure = Mock(spec=DocumentRule)
        # Second rule fails validation
        mock_registry.execute_rule.side_effect = [None, mock_failure, None]
        mock_registry_class.return_value = mock_registry

        analyzer = DriftAnalyzer(config=mock_config, project_path=temp_project)

        # Execute
        doc_rules, execution_details = analyzer._execute_rules_sequential(
            sample_validation_rules, mock_bundle, "test_rule", None
        )

        # Verify failure was tracked
        assert len(doc_rules) == 1
        assert doc_rules[0] == mock_failure

        # Verify execution details show failure
        assert execution_details[0]["status"] == "passed"
        assert execution_details[1]["status"] == "failed"
        assert execution_details[2]["status"] == "passed"


class TestParallelExecution:
    """Test parallel execution logic."""

    @pytest.mark.asyncio
    @patch("drift.core.analyzer.ValidatorRegistry")
    async def test_parallel_executes_all_rules(
        self, mock_registry_class, mock_config, mock_bundle, sample_validation_rules, temp_project
    ):
        """Test that parallel execution runs all rules."""
        # Setup
        mock_registry = Mock()
        mock_registry.execute_rule.return_value = None
        mock_registry_class.return_value = mock_registry

        analyzer = DriftAnalyzer(config=mock_config, project_path=temp_project)

        # Execute
        doc_rules, execution_details = await analyzer._execute_rules_parallel(
            sample_validation_rules, mock_bundle, "test_rule", None
        )

        # Verify all rules were executed
        assert len(execution_details) == 3
        assert all(detail["status"] == "passed" for detail in execution_details)

    @pytest.mark.asyncio
    @patch("drift.core.analyzer.ValidatorRegistry")
    async def test_parallel_continues_on_error(
        self, mock_registry_class, mock_config, mock_bundle, sample_validation_rules, temp_project
    ):
        """Test that parallel execution continues when a rule errors."""
        # Setup
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            return None

        mock_registry = Mock()
        mock_registry.execute_rule.side_effect = side_effect
        mock_registry_class.return_value = mock_registry

        analyzer = DriftAnalyzer(config=mock_config, project_path=temp_project)

        # Execute
        doc_rules, execution_details = await analyzer._execute_rules_parallel(
            sample_validation_rules, mock_bundle, "test_rule", None
        )

        # Verify all rules were attempted
        assert len(execution_details) == 3

        # At least one rule should be errored
        errored = [d for d in execution_details if d["status"] == "errored"]
        assert len(errored) >= 1

    @pytest.mark.asyncio
    @patch("drift.core.analyzer.ValidatorRegistry")
    async def test_parallel_tracks_failed_validations(
        self, mock_registry_class, mock_config, mock_bundle, sample_validation_rules, temp_project
    ):
        """Test that parallel execution tracks failed validations."""
        # Setup
        call_count = 0
        mock_failure = Mock(spec=DocumentRule)

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Second call returns failure
            if call_count == 2:
                return mock_failure
            return None

        mock_registry = Mock()
        mock_registry.execute_rule.side_effect = side_effect
        mock_registry_class.return_value = mock_registry

        analyzer = DriftAnalyzer(config=mock_config, project_path=temp_project)

        # Execute
        doc_rules, execution_details = await analyzer._execute_rules_parallel(
            sample_validation_rules, mock_bundle, "test_rule", None
        )

        # Verify failure was tracked
        assert len(doc_rules) == 1
        assert doc_rules[0] == mock_failure

        # Verify execution details
        failed = [d for d in execution_details if d["status"] == "failed"]
        assert len(failed) == 1


class TestAsyncHelpers:
    """Test async helper methods."""

    @pytest.mark.asyncio
    @patch("drift.core.analyzer.ValidatorRegistry")
    async def test_execute_single_rule_async_success(
        self, mock_registry_class, mock_config, mock_bundle, temp_project
    ):
        """Test async execution of a single successful rule."""
        # Setup
        mock_registry = Mock()
        mock_registry.execute_rule.return_value = None
        mock_registry_class.return_value = mock_registry

        analyzer = DriftAnalyzer(config=mock_config, project_path=temp_project)

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Test rule",
            file_path="test.txt",
            failure_message="File should exist",
            expected_behavior="File should exist",
        )

        # Execute
        result, exec_info = await analyzer._execute_single_rule_async(
            rule, mock_bundle, "test_rule", None
        )

        # Verify
        assert result is None
        assert exec_info["status"] == "passed"
        assert exec_info["rule_description"] == "Test rule"

    @pytest.mark.asyncio
    @patch("drift.core.analyzer.ValidatorRegistry")
    async def test_execute_single_rule_async_failure(
        self, mock_registry_class, mock_config, mock_bundle, temp_project
    ):
        """Test async execution of a single failed rule."""
        # Setup
        mock_failure = Mock(spec=DocumentRule)
        mock_registry = Mock()
        mock_registry.execute_rule.return_value = mock_failure
        mock_registry_class.return_value = mock_registry

        analyzer = DriftAnalyzer(config=mock_config, project_path=temp_project)

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Test rule",
            file_path="test.txt",
            failure_message="File should exist",
            expected_behavior="File should exist",
        )

        # Execute
        result, exec_info = await analyzer._execute_single_rule_async(
            rule, mock_bundle, "test_rule", None
        )

        # Verify
        assert result == mock_failure
        assert exec_info["status"] == "failed"

    @pytest.mark.asyncio
    @patch("drift.core.analyzer.ValidatorRegistry")
    async def test_execute_single_rule_async_error(
        self, mock_registry_class, mock_config, mock_bundle, temp_project
    ):
        """Test async execution handles errors gracefully."""
        # Setup
        mock_registry = Mock()
        mock_registry.execute_rule.side_effect = Exception("Test error")
        mock_registry_class.return_value = mock_registry

        analyzer = DriftAnalyzer(config=mock_config, project_path=temp_project)

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Test rule",
            file_path="test.txt",
            failure_message="File should exist",
            expected_behavior="File should exist",
        )

        # Execute
        result, exec_info = await analyzer._execute_single_rule_async(
            rule, mock_bundle, "test_rule", None
        )

        # Verify
        assert result is None
        assert exec_info["status"] == "errored"
        assert "error_message" in exec_info
        assert "Test error" in exec_info["error_message"]


class TestConcurrencySafety:
    """Test concurrency safety of parallel execution."""

    @pytest.mark.asyncio
    @patch("drift.core.analyzer.ValidatorRegistry")
    async def test_each_task_gets_own_registry(
        self, mock_registry_class, mock_config, mock_bundle, sample_validation_rules, temp_project
    ):
        """Test that each async task creates its own ValidatorRegistry."""
        # Setup
        registries_created = []

        def track_registry_creation(*args, **kwargs):
            registry = Mock()
            registry.execute_rule.return_value = None
            registries_created.append(registry)
            return registry

        mock_registry_class.side_effect = track_registry_creation

        analyzer = DriftAnalyzer(config=mock_config, project_path=temp_project)

        # Count registries created before parallel execution
        registries_before = len(registries_created)

        # Execute
        await analyzer._execute_rules_parallel(
            sample_validation_rules, mock_bundle, "test_rule", None
        )

        # Verify each task created its own registry (3 tasks = 3 new registries)
        registries_after = len(registries_created)
        assert registries_after - registries_before == 3

    @pytest.mark.asyncio
    @patch("drift.core.analyzer.ValidatorRegistry")
    async def test_parallel_and_sequential_produce_same_results(
        self, mock_registry_class, mock_config, mock_bundle, sample_validation_rules, temp_project
    ):
        """Test that parallel and sequential execution produce identical results."""
        # Setup - deterministic results
        results = [None, Mock(spec=DocumentRule), None]
        call_index = 0

        def side_effect(*args, **kwargs):
            nonlocal call_index
            result = results[call_index % len(results)]
            call_index += 1
            return result

        mock_registry = Mock()
        mock_registry.execute_rule.side_effect = side_effect
        mock_registry_class.return_value = mock_registry

        analyzer = DriftAnalyzer(config=mock_config, project_path=temp_project)

        # Execute sequentially
        call_index = 0
        seq_rules, seq_details = analyzer._execute_rules_sequential(
            sample_validation_rules, mock_bundle, "test_rule", None
        )

        # Execute in parallel
        call_index = 0
        par_rules, par_details = await analyzer._execute_rules_parallel(
            sample_validation_rules, mock_bundle, "test_rule", None
        )

        # Verify same number of results
        assert len(seq_rules) == len(par_rules)
        assert len(seq_details) == len(par_details)

        # Verify same statuses (order may differ in parallel)
        seq_statuses = sorted([d["status"] for d in seq_details])
        par_statuses = sorted([d["status"] for d in par_details])
        assert seq_statuses == par_statuses
