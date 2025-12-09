"""Validators for block-based content analysis."""

import re
from typing import List, Literal, Optional

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.validators.base import BaseValidator


class BlockLineCountValidator(BaseValidator):
    """Validator for counting lines within paired delimiters.

    Validates content within paired delimiters (code blocks, YAML sections, etc.)
    against line count thresholds using comparison operators.

    Configuration Parameters (via rule.params):
        pattern_start: Regex pattern for opening delimiter (e.g., "^```")
        pattern_end: Regex pattern for closing delimiter (e.g., "^```")
        min_lines: Minimum lines required (inclusive, >=)
        max_lines: Maximum lines allowed (inclusive, <=)
        exact_lines: Exact line count required (==)
        files: List of file patterns to validate (glob patterns)

    Example usage in .drift.yaml:
        - name: "Ensure code examples are substantial"
          type: core:block_line_count
          params:
            pattern_start: "^```"
            pattern_end: "^```"
            min_lines: 3
            files: ["README.md", "docs/**/*.md"]

    Edge Cases Handled:
        - Unpaired delimiters: Clear error messages
        - Empty blocks: Counted as 0 lines
        - Multiple paired blocks: All validated
        - Line count excludes delimiter lines themselves
    """

    @property
    def validation_type(self) -> str:
        """Return validation type for this validator."""
        return "core:block_line_count"

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    @property
    def default_failure_message(self) -> str:
        """Return default failure message template."""
        return "Block line count validation failed"

    @property
    def default_expected_behavior(self) -> str:
        """Return default expected behavior description."""
        return "Blocks should meet line count constraints"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Validate block line counts in files.

        -- rule: ValidationRule with params containing patterns and thresholds
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if validation fails, None if passes.
        """
        # Extract parameters from params dict
        pattern_start = rule.params.get("pattern_start")
        pattern_end = rule.params.get("pattern_end")
        min_lines = rule.params.get("min_lines")
        max_lines = rule.params.get("max_lines")
        exact_lines = rule.params.get("exact_lines")
        file_patterns = rule.params.get("files", [])

        # Validate required parameters
        if not pattern_start:
            raise ValueError("BlockLineCountValidator requires params.pattern_start")
        if not pattern_end:
            raise ValueError("BlockLineCountValidator requires params.pattern_end")

        # At least one threshold must be specified
        if min_lines is None and max_lines is None and exact_lines is None:
            raise ValueError(
                "BlockLineCountValidator requires at least one of: "
                "params.min_lines, params.max_lines, or params.exact_lines"
            )

        # Compile patterns
        try:
            start_re = re.compile(pattern_start, re.MULTILINE)
            end_re = re.compile(pattern_end, re.MULTILINE)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        # Get files to validate
        if not file_patterns:
            # No file patterns specified, use all files in bundle
            files_to_check = bundle.files
        else:
            # Match files against patterns
            files_to_check = []
            for pattern in file_patterns:
                import fnmatch

                for doc_file in bundle.files:
                    if fnmatch.fnmatch(doc_file.relative_path, pattern):
                        if doc_file not in files_to_check:
                            files_to_check.append(doc_file)

        if not files_to_check:
            # No files to check
            return None

        # Track violations
        violations = []
        total_blocks = 0

        for doc_file in files_to_check:
            file_path = bundle.project_path / doc_file.relative_path

            # Read file content
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except FileNotFoundError:
                # File listed in bundle but doesn't exist - skip it
                continue
            except IsADirectoryError:
                # File path points to a directory - skip it
                continue
            except (PermissionError, UnicodeDecodeError) as e:
                # Can't read file due to permissions or encoding - return error
                error_type = type(e).__name__
                return DocumentRule(
                    bundle_id=bundle.bundle_id,
                    bundle_type=bundle.bundle_type,
                    file_paths=[doc_file.relative_path],
                    observed_issue=(f"Failed to read file {doc_file.relative_path}: {error_type}"),
                    expected_quality=self._get_expected_behavior(rule),
                    rule_type="",
                    context=f"Validation rule: {rule.description}",
                )

            # Check if start and end patterns are the same
            same_delimiter = pattern_start == pattern_end

            if same_delimiter:
                # When start/end are the same, treat alternating matches as open/close
                matches = []
                for i, line in enumerate(lines, start=1):
                    if start_re.search(line):
                        matches.append(i)

                # Pair up alternating matches
                if len(matches) % 2 != 0:
                    return DocumentRule(
                        bundle_id=bundle.bundle_id,
                        bundle_type=bundle.bundle_type,
                        file_paths=[doc_file.relative_path],
                        observed_issue=(
                            f"Unpaired delimiters in {doc_file.relative_path}: "
                            f"odd number of delimiter matches ({len(matches)})"
                        ),
                        expected_quality=self._get_expected_behavior(rule),
                        rule_type="",
                        context=f"Validation rule: {rule.description}",
                    )

                # Pair them up: [0,1], [2,3], [4,5], ...
                block_pairs = [(matches[i], matches[i + 1]) for i in range(0, len(matches), 2)]
            else:
                # Different start/end patterns - need to pair each start with next unpaired end
                block_starts = []
                block_ends = []

                for i, line in enumerate(lines, start=1):
                    if start_re.search(line):
                        block_starts.append(i)
                    # For end pattern, only match if it's NOT also a start
                    # This handles cases like "^```yaml" (start) and "^```" (end)
                    # where the end pattern is less specific
                    elif end_re.search(line):
                        block_ends.append(i)

                # Pair each start with the next available end that comes after it
                block_pairs = []
                used_ends = set()

                for start in block_starts:
                    # Find next end after this start that hasn't been used
                    paired = False
                    for end in block_ends:
                        if end > start and end not in used_ends:
                            block_pairs.append((start, end))
                            used_ends.add(end)
                            paired = True
                            break

                    if not paired:
                        # No available end for this start
                        return DocumentRule(
                            bundle_id=bundle.bundle_id,
                            bundle_type=bundle.bundle_type,
                            file_paths=[doc_file.relative_path],
                            observed_issue=(
                                f"Unpaired delimiters in {doc_file.relative_path}: "
                                f"start at line {start} has no matching end"
                            ),
                            expected_quality=self._get_expected_behavior(rule),
                            rule_type="",
                            context=f"Validation rule: {rule.description}",
                        )

                # Check if there are unused ends
                if len(used_ends) < len(block_ends):
                    unused_ends = [e for e in block_ends if e not in used_ends]
                    unused_str = ", ".join(map(str, unused_ends))
                    return DocumentRule(
                        bundle_id=bundle.bundle_id,
                        bundle_type=bundle.bundle_type,
                        file_paths=[doc_file.relative_path],
                        observed_issue=(
                            f"Unpaired delimiters in {doc_file.relative_path}: "
                            f"unmatched end delimiter(s) at line(s): {unused_str}"
                        ),
                        expected_quality=self._get_expected_behavior(rule),
                        rule_type="",
                        context=f"Validation rule: {rule.description}",
                    )

            # Process each block
            for start_line, end_line in block_pairs:
                if end_line <= start_line:
                    return DocumentRule(
                        bundle_id=bundle.bundle_id,
                        bundle_type=bundle.bundle_type,
                        file_paths=[doc_file.relative_path],
                        observed_issue=(
                            f"Invalid block in {doc_file.relative_path}: "
                            f"end line {end_line} before/at start line {start_line}"
                        ),
                        expected_quality=self._get_expected_behavior(rule),
                        rule_type="",
                        context=f"Validation rule: {rule.description}",
                    )

                # Count lines between delimiters (excluding delimiter lines)
                line_count = end_line - start_line - 1
                total_blocks += 1

                # Check against thresholds
                threshold_violated = False
                threshold_desc = ""

                if exact_lines is not None:
                    if line_count != exact_lines:
                        threshold_violated = True
                        threshold_desc = f"expected exactly {exact_lines}"
                elif min_lines is not None and line_count < min_lines:
                    threshold_violated = True
                    threshold_desc = f"expected at least {min_lines}"
                elif max_lines is not None and line_count > max_lines:
                    threshold_violated = True
                    threshold_desc = f"expected at most {max_lines}"

                if threshold_violated:
                    violations.append(
                        {
                            "file_path": doc_file.relative_path,
                            "line_start": start_line,
                            "line_end": end_line,
                            "actual_count": line_count,
                            "threshold": threshold_desc,
                        }
                    )

        if not violations:
            # All blocks passed
            return None

        # Build failure message
        threshold_label = ""
        if exact_lines is not None:
            threshold_label = f"exact {exact_lines}"
        elif min_lines is not None:
            threshold_label = f"min {min_lines}"
        elif max_lines is not None:
            threshold_label = f"max {max_lines}"

        # Create detailed failure message
        failure_lines = [
            f"Found {total_blocks} total blocks, {len(violations)} in violation",
            f"Threshold: {threshold_label}",
            "",
        ]

        for v in violations:
            failure_lines.append(
                f"{v['file_path']}:{v['line_start']}-{v['line_end']}: "
                f"{v['actual_count']} lines ({v['threshold']})"
            )

        failure_details = {
            "total_blocks": total_blocks,
            "violations_count": len(violations),
            "threshold": threshold_label,
            "violations": violations,
        }

        # Extract unique file paths
        file_paths = sorted({str(v["file_path"]) for v in violations})

        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=file_paths,
            observed_issue="\n   ".join(failure_lines),
            expected_quality=self._get_expected_behavior(rule),
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}",
            failure_details=failure_details,
        )
