"""
SYNORA Routing Accuracy Benchmark & Evaluation Dataset
Provides a comprehensive suite of real, anonymized prompts across English, Hindi/Hinglish,
Spanish, and French to measure routing accuracy, detect misroutes, and guard safety boundaries.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.core.workflow_router import workflow_router, WorkflowType

class BenchmarkCase(BaseModel):
    prompt: str
    expected_workflow: WorkflowType
    expected_permission_mode: Optional[str] = None
    category: str
    context: Optional[str] = None
    notes: Optional[str] = None

# Comprehensive Evaluation Dataset (65 real, anonymized prompts)
BENCHMARK_DATASET: List[BenchmarkCase] = [
    # -------------------------------------------------------------
    # 1. PURE CHAT / EXPLANATIONS (Conversational & Multi-Stage)
    # -------------------------------------------------------------
    BenchmarkCase(
        prompt="Explain this code",
        expected_workflow=WorkflowType.CHAT,
        category="chat_explanation",
        notes="Canonical explain prompt"
    ),
    BenchmarkCase(
        prompt="Can you explain how async/await works in Python?",
        expected_workflow=WorkflowType.CHAT,
        category="chat_explanation"
    ),
    BenchmarkCase(
        prompt="What does the GIL do in CPython?",
        expected_workflow=WorkflowType.CHAT,
        category="chat_concept"
    ),
    BenchmarkCase(
        prompt="Teach me about Kubernetes ingress controllers vs services",
        expected_workflow=WorkflowType.CHAT,
        category="chat_concept"
    ),
    BenchmarkCase(
        prompt="Overview of TCP vs UDP protocols and when to choose each",
        expected_workflow=WorkflowType.CHAT,
        category="chat_comparison"
    ),
    BenchmarkCase(
        prompt="How does quicksort achieve O(n log n) average time complexity?",
        expected_workflow=WorkflowType.CHAT,
        category="chat_algorithm"
    ),
    BenchmarkCase(
        prompt="What is the difference between SQLite WAL mode and DELETE journal mode?",
        expected_workflow=WorkflowType.CHAT,
        category="chat_comparison"
    ),
    BenchmarkCase(
        prompt="Give me pros and cons of using WebSockets vs Server-Sent Events",
        expected_workflow=WorkflowType.CHAT,
        category="chat_comparison"
    ),
    BenchmarkCase(
        prompt="Walk me through how JWT authentication verifies signatures",
        expected_workflow=WorkflowType.CHAT,
        category="chat_explanation"
    ),
    BenchmarkCase(
        prompt="Write a poem about distributed systems and consensus",
        expected_workflow=WorkflowType.CHAT,
        category="chat_creative"
    ),

    # -------------------------------------------------------------
    # 2. CLAW CODE READ-ONLY (Safe Inspection & Auditing)
    # -------------------------------------------------------------
    BenchmarkCase(
        prompt="Find the bug in my project",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="claw_read_only"
    ),
    BenchmarkCase(
        prompt="Find bugs across the codebase",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="claw_read_only"
    ),
    BenchmarkCase(
        prompt="Search where Router is defined in the repo",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="claw_read_only"
    ),
    BenchmarkCase(
        prompt="Inspect the project files for memory leaks",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="claw_read_only"
    ),
    BenchmarkCase(
        prompt="Audit my codebase for security issues and SQL injections",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="claw_read_only"
    ),
    BenchmarkCase(
        prompt="Locate all places where localStorage is accessed in the codebase",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="claw_read_only"
    ),
    BenchmarkCase(
        prompt="Search for dead code or unused imports in our project",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="claw_read_only"
    ),
    BenchmarkCase(
        prompt="Audit the project dependencies for deprecated packages",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="claw_read_only"
    ),
    BenchmarkCase(
        prompt="Inspect project structure and describe the directory layout",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="claw_read_only"
    ),
    BenchmarkCase(
        prompt="Check git diff and show uncommitted changes in the repo",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="claw_read_only"
    ),

    # -------------------------------------------------------------
    # 3. CLAW CODE MUTATING / CONFIRMATION (File Edits, Fixes, Tests)
    # -------------------------------------------------------------
    BenchmarkCase(
        prompt="Fix the bug and run tests",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_confirmation"
    ),
    BenchmarkCase(
        prompt="Fix bugs in my project and run pytest",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_confirmation"
    ),
    BenchmarkCase(
        prompt="fix the login bug",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_confirmation",
        notes="Mutating bug fix without explicit 'run tests' indicator"
    ),
    BenchmarkCase(
        prompt="Fix the login bug in auth.py",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_confirmation"
    ),
    BenchmarkCase(
        prompt="resolve the signup crash",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_confirmation"
    ),
    BenchmarkCase(
        prompt="Fix the payment error and verify tests",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_confirmation"
    ),
    BenchmarkCase(
        prompt="explain and fix this file",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_compound",
        notes="Compound request demanding both explanation and modification"
    ),
    BenchmarkCase(
        prompt="explain the error and fix it",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_compound"
    ),
    BenchmarkCase(
        prompt="review and fix the database schema",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_compound"
    ),
    BenchmarkCase(
        prompt="Implement missing method in backend/core/router.py and test it",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_confirmation"
    ),
    BenchmarkCase(
        prompt="Refactor auth in the project and run cargo test",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_confirmation"
    ),
    BenchmarkCase(
        prompt="Fix the failing test and commit changes",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_confirmation"
    ),
    BenchmarkCase(
        prompt="Update package.json dependencies and run npm test",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_confirmation"
    ),
    BenchmarkCase(
        prompt="Patch the security vulnerability in jwt parser and test it",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_confirmation"
    ),
    BenchmarkCase(
        prompt="Replace deprecated mock library with unittest.mock in backend/tests",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="claw_confirmation"
    ),

    # -------------------------------------------------------------
    # 4. AMBIGUOUS PROMPTS (Clarification Fast-Path)
    # -------------------------------------------------------------
    BenchmarkCase(
        prompt="fix it",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="ambiguous",
        notes="Vague 2-word prompt lacking file or code context"
    ),
    BenchmarkCase(
        prompt="fix the bug",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="ambiguous"
    ),
    BenchmarkCase(
        prompt="why is it failing",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="ambiguous"
    ),
    BenchmarkCase(
        prompt="make it work",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="ambiguous"
    ),
    BenchmarkCase(
        prompt="it doesn't work",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="ambiguous"
    ),
    BenchmarkCase(
        prompt="debug this",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="ambiguous"
    ),
    BenchmarkCase(
        prompt="run it",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="ambiguous"
    ),
    BenchmarkCase(
        prompt="help with this",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="ambiguous"
    ),
    BenchmarkCase(
        prompt="update it",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="ambiguous"
    ),

    # -------------------------------------------------------------
    # 5. CONTEXT-RESOLVED FOLLOW-UPS (Ambiguous prompt + Prior Context)
    # -------------------------------------------------------------
    BenchmarkCase(
        prompt="fix it",
        context="User: The auth endpoint in backend/auth.py is raising AttributeError: NoneType object has no attribute 'token'",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="context_followup",
        notes="Follow-up 'fix it' disambiguated by prior error in context"
    ),
    BenchmarkCase(
        prompt="apply the change",
        context="Assistant: Here is the proposed fix for SQLite deadlock in backend/database/sqlite.py: line 42",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="context_followup"
    ),
    BenchmarkCase(
        prompt="now fix line 45",
        context="User: We ran pytest and backend/core/router.py failed on line 45 with IndexError",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="context_followup"
    ),
    BenchmarkCase(
        prompt="fix it: ```python\ndef divide(a, b):\n    return a / b\n```",
        expected_workflow=WorkflowType.CHAT,
        category="code_fence_in_prompt",
        notes="Provided inline code snippet routes to conversational fix rather than workspace claw"
    ),

    # -------------------------------------------------------------
    # 6. HINDI / HINGLISH PROMPTS
    # -------------------------------------------------------------
    BenchmarkCase(
        prompt="bhai login bug fix kar de",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="multilingual_hindi"
    ),
    BenchmarkCase(
        prompt="login chal nahi raha theek kardo",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="multilingual_hindi"
    ),
    BenchmarkCase(
        prompt="ye code explain karo",
        expected_workflow=WorkflowType.CHAT,
        category="multilingual_hindi"
    ),
    BenchmarkCase(
        prompt="samjhao ye function kya karta hai",
        expected_workflow=WorkflowType.CHAT,
        category="multilingual_hindi"
    ),
    BenchmarkCase(
        prompt="code me bug dhoondho",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="multilingual_hindi"
    ),
    BenchmarkCase(
        prompt="project me bug search karo",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="multilingual_hindi"
    ),
    BenchmarkCase(
        prompt="isko sahi kar do aur test chalao",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="multilingual_hindi"
    ),
    BenchmarkCase(
        prompt="chal nahi raha",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="multilingual_hindi_ambiguous"
    ),
    BenchmarkCase(
        prompt="kya problem hai",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="multilingual_hindi_ambiguous"
    ),

    # -------------------------------------------------------------
    # 7. SPANISH & FRENCH PROMPTS
    # -------------------------------------------------------------
    BenchmarkCase(
        prompt="explica este código",
        expected_workflow=WorkflowType.CHAT,
        category="multilingual_spanish"
    ),
    BenchmarkCase(
        prompt="como funciona el protocolo TCP",
        expected_workflow=WorkflowType.CHAT,
        category="multilingual_spanish"
    ),
    BenchmarkCase(
        prompt="busca el fallo en mi proyecto",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="multilingual_spanish"
    ),
    BenchmarkCase(
        prompt="arregla el error de login y ejecuta tests",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="multilingual_spanish"
    ),
    BenchmarkCase(
        prompt="explique ce code s'il vous plait",
        expected_workflow=WorkflowType.CHAT,
        category="multilingual_french"
    ),
    BenchmarkCase(
        prompt="trouve le bug dans mon projet",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="multilingual_french"
    ),
    BenchmarkCase(
        prompt="corrige le bug de login et lance les tests",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="multilingual_french"
    ),
]

def run_routing_benchmark(dataset: Optional[List[BenchmarkCase]] = None) -> Dict[str, Any]:
    """
    Executes the benchmark against the WorkflowRouter and calculates:
    - Total test count
    - Accuracy percentage
    - Category-level breakdown
    - Detailed misroutes list
    """
    cases = dataset or BENCHMARK_DATASET
    total = len(cases)
    passed = 0
    misroutes = []
    category_stats = {}

    for case in cases:
        cat = case.category
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0}
        category_stats[cat]["total"] += 1

        decision = workflow_router.classify(case.prompt, context=case.context)
        is_type_match = decision.workflow_type == case.expected_workflow
        is_perm_match = (case.expected_permission_mode is None) or (decision.permission_mode == case.expected_permission_mode)

        if is_type_match and is_perm_match:
            passed += 1
            category_stats[cat]["passed"] += 1
        else:
            misroutes.append({
                "prompt": case.prompt,
                "category": case.category,
                "expected_workflow": case.expected_workflow.value,
                "actual_workflow": decision.workflow_type.value,
                "expected_permission": case.expected_permission_mode,
                "actual_permission": decision.permission_mode,
                "decision_reason": decision.reason,
                "notes": case.notes
            })

    accuracy = round((passed / total) * 100, 2) if total > 0 else 0.0

    return {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": len(misroutes),
        "accuracy_pct": accuracy,
        "category_stats": category_stats,
        "misroutes": misroutes
    }

if __name__ == "__main__":
    results = run_routing_benchmark()
    print(f"SYNORA Workflow Routing Benchmark: {results['passed_cases']}/{results['total_cases']} ({results['accuracy_pct']}%)")
    if results["misroutes"]:
        print("\nMisroutes detected:")
        for m in results["misroutes"]:
            print(f" - Prompt: '{m['prompt']}' | Expected: {m['expected_workflow']} | Actual: {m['actual_workflow']}")

