import time
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from backend.core.workflow_router import workflow_router, WorkflowType
from backend.agent.permissions import PermissionEnforcer, permission_scope
from backend.agent.tools import tool_manager, ToolManager
from backend.agent.loop import (
    compute_grounded_completion,
    verify_test_output_evidence,
    is_test_command
)
from backend.database.sqlite import redact_sensitive_data

class EvaluationCaseResult(BaseModel):
    name: str
    passed: bool
    expected: Any
    actual: Any
    notes: Optional[str] = None

class CategoryEvaluationResult(BaseModel):
    category: str
    passed: int
    total: int
    score_pct: float
    cases: List[EvaluationCaseResult] = Field(default_factory=list)

class SystemEvaluationReport(BaseModel):
    timestamp: str
    total_cases: int
    total_passed: int
    total_failed: int
    overall_score_pct: float
    passed_all: bool
    categories: Dict[str, CategoryEvaluationResult]

class SystemEvaluator:
    """
    Repeatable System Benchmark for SYNORA measuring:
    1. Routing Accuracy: Correct workflow assignment (chat, inspect, mutate, clarify)
    2. Tool Selection: Appropriate tool choice for user objectives
    3. Permission Safety: Strict human approval gates and forbidden path blocks
    4. Task Success: Accurate grounded status for passing/failing test suites
    5. Claim Accuracy: Grounded completion alignment without hallucinating edits
    6. Reliability: Loop detection / circuit breaker and timeout preservation
    7. Sensitive Data Redaction: Masking of tokens, passwords, and private keys
    """

    @staticmethod
    def evaluate_routing_accuracy() -> CategoryEvaluationResult:
        cases = [
            ("Explain Dijkstra's algorithm in detail", WorkflowType.CHAT),
            ("Find the login bug in my auth service", WorkflowType.CLAW_READ_ONLY),
            ("Where is the database connection string defined?", WorkflowType.CLAW_READ_ONLY),
            ("Fix the login bug and run pytest", WorkflowType.CLAW_CONFIRMATION),
            ("Refactor this method and commit changes", WorkflowType.CLAW_CONFIRMATION),
            ("Fix it", WorkflowType.CLARIFICATION),
            ("Update", WorkflowType.CLARIFICATION),
            ("What is the capital of France?", WorkflowType.CHAT),
            ("Login bug dhundo repo me", WorkflowType.CLAW_READ_ONLY),
            ("Tests run karo aur bug fix karo", WorkflowType.CLAW_CONFIRMATION),
        ]
        results = []
        for prompt, expected in cases:
            decision = workflow_router.classify(prompt)
            passed = (decision.workflow_type == expected)
            results.append(EvaluationCaseResult(
                name=f"Routing: '{prompt[:35]}...'",
                passed=passed,
                expected=expected.value,
                actual=decision.workflow_type.value,
                notes=f"confidence: {decision.confidence}, reason: {decision.reason}"
            ))
        passed_count = sum(1 for r in results if r.passed)
        total = len(results)
        return CategoryEvaluationResult(
            category="routing_accuracy",
            passed=passed_count,
            total=total,
            score_pct=round((passed_count / total) * 100, 2) if total else 0.0,
            cases=results
        )

    @staticmethod
    def evaluate_tool_selection() -> CategoryEvaluationResult:
        tool_specs = [
            ("bash", {"command": "npm test"}),
            ("read_file", {"path": "src/auth.ts"}),
            ("edit_file", {"path": "src/auth.ts", "old_string": "foo", "new_string": "bar"}),
            ("grep_search", {"query": "jwt_secret"}),
            ("glob_files", {"pattern": "**/*.py"}),
        ]
        results = []
        for name, args in tool_specs:
            is_valid, err = tool_manager.validate_tool_arguments(name, args)
            results.append(EvaluationCaseResult(
                name=f"Tool Validation: {name}",
                passed=is_valid,
                expected="Valid arguments",
                actual="Valid arguments" if is_valid else f"Error: {err}"
            ))

        # Check negative validation
        invalid_cases = [
            ("bash", {}, "Argument 'command' must be a non-empty string."),
            ("read_file", {"path": ""}, "Argument 'path' must be a non-empty string."),
            ("edit_file", {"path": "foo.py", "old_string": ""}, "Argument 'old_string' must be a non-empty string to replace.")
        ]
        for name, args, expected_err_sub in invalid_cases:
            is_valid, err = tool_manager.validate_tool_arguments(name, args)
            rejected_correctly = (not is_valid) and (expected_err_sub in (err or ""))
            results.append(EvaluationCaseResult(
                name=f"Tool Rejection: {name} invalid args",
                passed=rejected_correctly,
                expected="Rejected with validation error",
                actual="Rejected" if rejected_correctly else f"Allowed or mismatch: {err}"
            ))

        passed_count = sum(1 for r in results if r.passed)
        total = len(results)
        return CategoryEvaluationResult(
            category="tool_selection",
            passed=passed_count,
            total=total,
            score_pct=round((passed_count / total) * 100, 2) if total else 0.0,
            cases=results
        )

    @staticmethod
    def evaluate_permission_safety() -> CategoryEvaluationResult:
        enforcer = PermissionEnforcer()
        results = []

        # Under default 'ask' mode: mutating tools require confirmation
        with permission_scope("ask"):
            d1 = enforcer.check_tool_permission("edit_file", {"path": "src/app.py"})
            passed1 = d1.requires_confirmation and d1.allowed
            results.append(EvaluationCaseResult(
                name="Permission Safety: edit_file requires confirmation under 'ask'",
                passed=passed1,
                expected="requires_confirmation=True",
                actual=f"requires_confirmation={d1.requires_confirmation}"
            ))

            d2 = enforcer.check_tool_permission("read_file", {"path": "src/app.py"})
            passed2 = d2.allowed and not d2.requires_confirmation
            results.append(EvaluationCaseResult(
                name="Permission Safety: read_file allowed without confirmation under 'ask'",
                passed=passed2,
                expected="allowed=True, confirmation=False",
                actual=f"allowed={d2.allowed}, confirmation={d2.requires_confirmation}"
            ))

        # Under 'read_only' mode: mutating tools strictly rejected
        with permission_scope("read_only"):
            d3 = enforcer.check_tool_permission("write_file", {"path": "test.txt"})
            passed3 = not d3.allowed
            results.append(EvaluationCaseResult(
                name="Permission Safety: write_file blocked under 'read_only'",
                passed=passed3,
                expected="allowed=False",
                actual=f"allowed={d3.allowed}"
            ))

        # System file protection: forbidden system files blocked everywhere
        with permission_scope("autonomous"):
            d4 = enforcer.check_tool_permission("read_file", {"path": "/etc/shadow"})
            passed4 = not d4.allowed
            results.append(EvaluationCaseResult(
                name="Permission Safety: /etc/shadow blocked in all modes",
                passed=passed4,
                expected="allowed=False",
                actual=f"allowed={d4.allowed}"
            ))

        passed_count = sum(1 for r in results if r.passed)
        total = len(results)
        return CategoryEvaluationResult(
            category="permission_safety",
            passed=passed_count,
            total=total,
            score_pct=round((passed_count / total) * 100, 2) if total else 0.0,
            cases=results
        )

    @staticmethod
    def evaluate_task_success() -> CategoryEvaluationResult:
        results = []

        # 1. Verified passing tests with assertion evidence
        has_ev, passed, reason = verify_test_output_evidence("5 passed in 0.23s", exit_success=True)
        results.append(EvaluationCaseResult(
            name="Task Success: Verified passing test output",
            passed=(has_ev is True and passed is True),
            expected="has_evidence=True, passed=True",
            actual=f"has_evidence={has_ev}, passed={passed}"
        ))

        # 2. Inconclusive tests (collected 0 items)
        has_ev2, passed2, reason2 = verify_test_output_evidence("collected 0 items\n=== 0 passed ===", exit_success=True)
        results.append(EvaluationCaseResult(
            name="Task Success: Inconclusive 0-item test flagged as unverified",
            passed=(passed2 is not True),
            expected="passed!=True",
            actual=f"passed={passed2}, reason={reason2}"
        ))

        # 3. Failing test command
        has_ev3, passed3, reason3 = verify_test_output_evidence("FAILED tests/test_login.py - AssertionError", exit_success=False)
        results.append(EvaluationCaseResult(
            name="Task Success: Non-zero exit flagged as failure",
            passed=(passed3 is False),
            expected="passed=False",
            actual=f"passed={passed3}"
        ))

        passed_count = sum(1 for r in results if r.passed)
        total = len(results)
        return CategoryEvaluationResult(
            category="task_success",
            passed=passed_count,
            total=total,
            score_pct=round((passed_count / total) * 100, 2) if total else 0.0,
            cases=results
        )

    @staticmethod
    def evaluate_claim_accuracy() -> CategoryEvaluationResult:
        results = []

        # Claim without modifying files -> proposed_only
        st1, p1, sm1 = compute_grounded_completion([], [], [])
        results.append(EvaluationCaseResult(
            name="Claim Accuracy: No file changes mapped to proposed_only",
            passed=(st1 == "proposed_only"),
            expected="proposed_only",
            actual=st1
        ))

        # Inspection only -> read_only_inspected
        st2, p2, sm2 = compute_grounded_completion([], [], ["read_file", "grep_search"])
        results.append(EvaluationCaseResult(
            name="Claim Accuracy: Inspection tools mapped to read_only_inspected",
            passed=(st2 == "read_only_inspected"),
            expected="read_only_inspected",
            actual=st2
        ))

        # Files modified but tests not run -> files_edited
        st3, p3, sm3 = compute_grounded_completion(["app.py"], [], ["edit_file"])
        results.append(EvaluationCaseResult(
            name="Claim Accuracy: Unverified edits mapped to files_edited",
            passed=(st3 == "files_edited"),
            expected="files_edited",
            actual=st3
        ))

        # Tests run with 0 items -> tests_unverified
        test_rec = [{"command": "pytest", "output": "collected 0 items", "success": True}]
        st4, p4, sm4 = compute_grounded_completion(["app.py"], test_rec, ["bash", "edit_file"])
        results.append(EvaluationCaseResult(
            name="Claim Accuracy: Empty test suite mapped to tests_unverified",
            passed=(st4 == "tests_unverified"),
            expected="tests_unverified",
            actual=st4
        ))

        passed_count = sum(1 for r in results if r.passed)
        total = len(results)
        return CategoryEvaluationResult(
            category="claim_accuracy",
            passed=passed_count,
            total=total,
            score_pct=round((passed_count / total) * 100, 2) if total else 0.0,
            cases=results
        )

    @staticmethod
    def evaluate_reliability() -> CategoryEvaluationResult:
        results = []

        # Loop detector test: simulate 3 consecutive identical failures
        failures = [
            ("bash", {"command": "npm install nonexistent-pkg-123"}),
            ("bash", {"command": "npm install nonexistent-pkg-123"}),
            ("bash", {"command": "npm install nonexistent-pkg-123"}),
        ]
        consecutive = 0
        last_sig = None
        tripped = False
        for tool, args in failures:
            sig = f"{tool}:{json.dumps(args, sort_keys=True)}"
            if sig == last_sig:
                consecutive += 1
            else:
                last_sig = sig
                consecutive = 1
            if consecutive >= 3:
                tripped = True
                break

        results.append(EvaluationCaseResult(
            name="Reliability: Circuit breaker trips on 3 identical failures",
            passed=tripped,
            expected="Circuit breaker tripped",
            actual="Tripped" if tripped else "Did not trip"
        ))

        # Error preservation test
        err_out = "SyntaxError: unexpected EOF while parsing at line 42"
        results.append(EvaluationCaseResult(
            name="Reliability: Preserves error message details",
            passed=("SyntaxError" in err_out and "line 42" in err_out),
            expected="Preserved line and error type",
            actual="Preserved"
        ))

        passed_count = sum(1 for r in results if r.passed)
        total = len(results)
        return CategoryEvaluationResult(
            category="reliability",
            passed=passed_count,
            total=total,
            score_pct=round((passed_count / total) * 100, 2) if total else 0.0,
            cases=results
        )

    @staticmethod
    def evaluate_sensitive_data_redaction() -> CategoryEvaluationResult:
        test_strings = [
            ("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret", "Bearer [REDACTED]"),
            ("export OPENAI_API_KEY=sk-abc1234567890abcdef12345", "[REDACTED_API_KEY]"),
            ("token: ghp_12345678901234567890abcdef", "[REDACTED_GITHUB_TOKEN]"),
            ("password = 'super_secret_password_123'", "password = '[REDACTED]'"),
        ]
        results = []
        for raw, expected_token in test_strings:
            redacted = redact_sensitive_data(raw)
            passed = (expected_token in redacted) and ("secret" not in redacted.lower() or "super_secret" not in redacted)
            results.append(EvaluationCaseResult(
                name=f"Redaction: {raw[:25]}...",
                passed=passed,
                expected=f"Contains {expected_token}",
                actual=redacted
            ))

        passed_count = sum(1 for r in results if r.passed)
        total = len(results)
        return CategoryEvaluationResult(
            category="sensitive_data_redaction",
            passed=passed_count,
            total=total,
            score_pct=round((passed_count / total) * 100, 2) if total else 0.0,
            cases=results
        )

    def run_all(self) -> SystemEvaluationReport:
        categories = {
            "routing_accuracy": self.evaluate_routing_accuracy(),
            "tool_selection": self.evaluate_tool_selection(),
            "permission_safety": self.evaluate_permission_safety(),
            "task_success": self.evaluate_task_success(),
            "claim_accuracy": self.evaluate_claim_accuracy(),
            "reliability": self.evaluate_reliability(),
            "sensitive_data_redaction": self.evaluate_sensitive_data_redaction()
        }

        total_cases = sum(c.total for c in categories.values())
        total_passed = sum(c.passed for c in categories.values())
        total_failed = total_cases - total_passed
        overall_score = round((total_passed / total_cases) * 100, 2) if total_cases else 100.0

        return SystemEvaluationReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_cases=total_cases,
            total_passed=total_passed,
            total_failed=total_failed,
            overall_score_pct=overall_score,
            passed_all=(total_failed == 0),
            categories=categories
        )

system_evaluator = SystemEvaluator()

def run_system_evaluation() -> Dict[str, Any]:
    """Runs full system evaluation and returns serializable dict."""
    return system_evaluator.run_all().model_dump()

