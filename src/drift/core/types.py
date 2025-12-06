"""Core data types and models for drift analysis."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FrequencyType(str, Enum):
    """Frequency of a rule violation occurrence."""

    ONE_TIME = "one-time"
    REPEATED = "repeated"


class WorkflowElement(str, Enum):
    """Type of workflow element that needs improvement."""

    DOCUMENTATION = "documentation"
    SKILL = "skill"
    COMMAND = "command"
    CONTEXT = "context"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class ResourceRequest(BaseModel):
    """Request for a specific project resource."""

    resource_type: str = Field(
        ...,
        description="Type of resource (command, skill, agent, main_config)",
    )
    resource_id: str = Field(
        ...,
        description="Identifier for the resource (e.g., 'deploy', 'api-design')",
    )
    reason: str = Field(..., description="Why AI needs this resource")


class ResourceResponse(BaseModel):
    """Response with loaded resource."""

    request: ResourceRequest = Field(..., description="The original request")
    found: bool = Field(..., description="Whether the resource was found")
    content: Optional[str] = Field(None, description="Content of the resource if found")
    file_path: Optional[str] = Field(None, description="Path to the resource file if found")
    error: Optional[str] = Field(None, description="Error message if not found")


class PhaseAnalysisResult(BaseModel):
    """Result from a single analysis phase."""

    phase_number: int = Field(..., description="Phase number (1-indexed)")
    resource_requests: List[ResourceRequest] = Field(
        default_factory=list, description="Resources requested by AI for next phase"
    )
    findings: List[Dict[str, Any]] = Field(
        default_factory=list, description="Preliminary findings from this phase"
    )
    final_determination: bool = Field(False, description="True if this is the final phase")


class Turn(BaseModel):
    """A single turn in a conversation."""

    number: int = Field(..., description="Turn number in the conversation")
    uuid: Optional[str] = Field(None, description="Unique identifier for the turn")
    user_message: str = Field(..., description="User's message in this turn")
    ai_message: str = Field(..., description="AI's response in this turn")
    timestamp: Optional[datetime] = Field(None, description="When this turn occurred")


class Conversation(BaseModel):
    """A complete conversation from an agent tool."""

    session_id: str = Field(..., description="Unique identifier for the conversation session")
    agent_tool: str = Field(..., description="Which agent tool created this conversation")
    file_path: str = Field(..., description="Path to the conversation file")
    project_path: Optional[str] = Field(None, description="Path to the project being worked on")
    project_context: Optional[str] = Field(
        None, description="Structured summary of project customizations and available features"
    )
    turns: List[Turn] = Field(default_factory=list, description="All turns in the conversation")
    started_at: Optional[datetime] = Field(None, description="When the conversation started")
    ended_at: Optional[datetime] = Field(None, description="When the conversation ended")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about the conversation"
    )


class Rule(BaseModel):
    """A single rule violation identified in a conversation."""

    turn_number: int = Field(..., description="Turn where the drift occurred")
    turn_uuid: Optional[str] = Field(None, description="UUID of the turn")
    agent_tool: str = Field(..., description="Agent tool where drift was found")
    conversation_file: str = Field(..., description="Conversation file containing the drift")
    observed_behavior: str = Field(
        ..., description="What was observed (AI action or user behavior)"
    )
    expected_behavior: str = Field(..., description="What should have happened instead")
    rule_type: str = Field(..., description="Type of rule that was violated")
    workflow_element: WorkflowElement = Field(
        WorkflowElement.UNKNOWN, description="What workflow element needs improvement"
    )
    turns_to_resolve: int = Field(1, description="How many turns to resolve this drift")
    turns_involved: List[int] = Field(
        default_factory=list, description="All turns involved in this drift"
    )
    context: str = Field("", description="Additional context about the drift")
    resources_consulted: List[str] = Field(
        default_factory=list, description="Resources checked during multi-phase analysis"
    )
    phases_count: int = Field(1, description="Number of analysis phases")
    source_type: Optional[str] = Field(
        None, description="Source of the rule violation: 'conversation' or 'document'"
    )
    affected_files: Optional[List[str]] = Field(
        default=None,
        description="Files involved in this rule violation (for document analysis)",
    )
    bundle_id: Optional[str] = Field(
        default=None,
        description="Bundle identifier (e.g., 'testing_skill') for document rule violations",
    )


class AnalysisResult(BaseModel):
    """Results from analyzing a single conversation."""

    session_id: str = Field(..., description="Conversation session ID")
    agent_tool: str = Field(..., description="Agent tool that created the conversation")
    conversation_file: str = Field(..., description="Path to conversation file")
    project_path: Optional[str] = Field(None, description="Project path from conversation")
    rules: List[Rule] = Field(default_factory=list, description="All rule violations found")
    analysis_timestamp: datetime = Field(
        default_factory=datetime.now, description="When this analysis was performed"
    )
    error: Optional[str] = Field(None, description="Error message if analysis failed")
    rule_errors: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of rule names to error messages for this conversation",
    )


class AnalysisSummary(BaseModel):
    """Summary statistics for a complete analysis run."""

    total_conversations: int = Field(0, description="Total conversations analyzed")
    total_rule_violations: int = Field(0, description="Total rule violations found")
    by_type: Dict[str, int] = Field(
        default_factory=dict, description="Rule violation count by type"
    )
    by_agent: Dict[str, int] = Field(
        default_factory=dict, description="Rule violation count by agent tool"
    )
    conversations_with_drift: int = Field(0, description="Number of conversations containing drift")
    conversations_without_drift: int = Field(0, description="Number of conversations without drift")
    rules_checked: List[str] = Field(
        default_factory=list, description="List of rule names that were checked"
    )
    total_checks: int = Field(
        0, description="Total number of individual checks performed (rule x target combinations)"
    )
    checks_passed: int = Field(0, description="Number of checks that passed")
    checks_failed: int = Field(0, description="Number of checks that failed")
    checks_warned: int = Field(0, description="Number of checks that produced warnings")
    checks_errored: int = Field(0, description="Number of checks that encountered errors")
    rules_passed: List[str] = Field(
        default_factory=list, description="List of rule names that passed (no issues found)"
    )
    rules_warned: List[str] = Field(
        default_factory=list, description="List of rule names that produced warnings"
    )
    rules_failed: List[str] = Field(
        default_factory=list, description="List of rule names that failed (produced failures)"
    )
    rules_errored: List[str] = Field(
        default_factory=list,
        description="List of rule names that encountered errors during analysis",
    )
    rule_errors: Dict[str, str] = Field(
        default_factory=dict, description="Map of rule names to error messages"
    )


class CompleteAnalysisResult(BaseModel):
    """Complete analysis results including all conversations and summary."""

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Analysis run metadata")
    summary: AnalysisSummary = Field(
        default_factory=lambda: AnalysisSummary(
            total_conversations=0,
            total_rule_violations=0,
            conversations_with_drift=0,
            conversations_without_drift=0,
            total_checks=0,
            checks_passed=0,
            checks_failed=0,
            checks_warned=0,
            checks_errored=0,
        ),
        description="Summary statistics",
    )
    results: List[AnalysisResult] = Field(
        default_factory=list, description="Per-conversation results"
    )


# Document analysis types


class DocumentFile(BaseModel):
    """Represents a single document file."""

    relative_path: str = Field(..., description="Path relative to project root")
    content: str = Field(..., description="File content")
    file_path: Path = Field(..., description="Absolute path to file")


class DocumentBundle(BaseModel):
    """Represents a bundle of documents for analysis."""

    bundle_id: str = Field(..., description="Unique identifier for this bundle")
    bundle_type: str = Field(..., description="Type of bundle (skill, command, agent, mixed, etc.)")
    bundle_strategy: str = Field(..., description="Strategy used (individual or collection)")
    files: List[DocumentFile] = Field(default_factory=list, description="Files in this bundle")
    project_path: Path = Field(..., description="Project root path")


class DocumentRule(BaseModel):
    """A rule violation identified from document analysis."""

    bundle_id: str = Field(..., description="Bundle where issue was found")
    bundle_type: str = Field(..., description="Type of bundle")
    file_paths: List[str] = Field(
        default_factory=list, description="Files involved in this rule violation"
    )
    observed_issue: str = Field(..., description="What issue was observed")
    expected_quality: str = Field(..., description="What the expected quality/behavior should be")
    rule_type: str = Field(..., description="Type of rule that was violated")
    context: str = Field("", description="Additional context about the issue")
    failure_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional structured failure details for message templating. "
            "Validators can provide specific details (e.g., circular_path, actual_depth) "
            "that can be interpolated into violation messages for more actionable output."
        ),
    )
