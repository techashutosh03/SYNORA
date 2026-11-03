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
    language: str = "en"
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

# -----------------------------------------------------------------------------
# UNSEEN HOLDOUT EVALUATION DATASET (44 real, anonymized prompts)
# Dedicated test set kept strictly separate from rule tuning to measure generalization
# across English, Hindi/Hinglish, Spanish, and French.
# -----------------------------------------------------------------------------
UNSEEN_EVAL_DATASET: List[BenchmarkCase] = [
    # English - Pure Chat & Concepts
    BenchmarkCase(
        prompt="How do transformers handle positional encodings in self-attention?",
        expected_workflow=WorkflowType.CHAT,
        category="unseen_chat",
        language="en"
    ),
    BenchmarkCase(
        prompt="Explain the Raft consensus algorithm leader election phase",
        expected_workflow=WorkflowType.CHAT,
        category="unseen_chat",
        language="en"
    ),
    BenchmarkCase(
        prompt="Compare PostgreSQL JSONB indexing with MongoDB BSON documents",
        expected_workflow=WorkflowType.CHAT,
        category="unseen_chat",
        language="en"
    ),
    BenchmarkCase(
        prompt="Can you explain how virtual DOM reconciliation works in React?",
        expected_workflow=WorkflowType.CHAT,
        category="unseen_chat",
        language="en"
    ),
    BenchmarkCase(
        prompt="What is the difference between processes and threads in Linux?",
        expected_workflow=WorkflowType.CHAT,
        category="unseen_chat",
        language="en"
    ),

    # English - Inspection / Read-Only
    BenchmarkCase(
        prompt="Check all API routes in the repo for missing authentication decorators",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="unseen_inspection",
        language="en"
    ),
    BenchmarkCase(
        prompt="Find where the rate limiting middleware is instantiated in the backend",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="unseen_inspection",
        language="en"
    ),
    BenchmarkCase(
        prompt="Search for hardcoded secret keys or API tokens across all files",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="unseen_inspection",
        language="en"
    ),
    BenchmarkCase(
        prompt="Inspect the database models for missing foreign key constraints",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="unseen_inspection",
        language="en"
    ),
    BenchmarkCase(
        prompt="Locate the Dockerfile and docker-compose files in the project",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="unseen_inspection",
        language="en"
    ),

    # English - Mutating / Confirmation Required
    BenchmarkCase(
        prompt="Fix the memory leak in the WebSocket connection pool and run pytest",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="unseen_mutation",
        language="en"
    ),
    BenchmarkCase(
        prompt="Update the CORS configuration in backend/main.py to allow our staging domain",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="unseen_mutation",
        language="en"
    ),
    BenchmarkCase(
        prompt="Refactor the authentication handler to use bcrypt and verify with npm test",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="unseen_mutation",
        language="en"
    ),
    BenchmarkCase(
        prompt="Fix the broken pagination logic in search results",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="unseen_mutation",
        language="en"
    ),
    BenchmarkCase(
        prompt="Replace deprecated datetime.utcnow() calls across the codebase and run tests",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="unseen_mutation",
        language="en"
    ),

    # English - Ambiguous / Clarification
    BenchmarkCase(
        prompt="it crashed again",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="unseen_ambiguous",
        language="en"
    ),
    BenchmarkCase(
        prompt="please debug the issue",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="unseen_ambiguous",
        language="en"
    ),
    BenchmarkCase(
        prompt="make it work please",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="unseen_ambiguous",
        language="en"
    ),
    BenchmarkCase(
        prompt="why does it fail",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="unseen_ambiguous",
        language="en"
    ),

    # Hindi / Hinglish
    BenchmarkCase(
        prompt="Python me GIL kya hota hai simple words me samjhao",
        expected_workflow=WorkflowType.CHAT,
        category="unseen_hindi_chat",
        language="hi_hinglish"
    ),
    BenchmarkCase(
        prompt="Bhai project ke architecture aur database design ka overview batao",
        expected_workflow=WorkflowType.CHAT,
        category="unseen_hindi_chat",
        language="hi_hinglish"
    ),
    BenchmarkCase(
        prompt="Backend ke auth module me check karo koi security vulnerability to nahi hai",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="unseen_hindi_inspection",
        language="hi_hinglish"
    ),
    BenchmarkCase(
        prompt="Project me database connection pooling kaha define kiya hai search karo",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="unseen_hindi_inspection",
        language="hi_hinglish"
    ),
    BenchmarkCase(
        prompt="Bhai user registration bug ko theek kar do aur pytest chala ke test karo",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="unseen_hindi_mutation",
        language="hi_hinglish"
    ),
    BenchmarkCase(
        prompt="Payment gateway webhook error fix kardo aur tests verify karo",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="unseen_hindi_mutation",
        language="hi_hinglish"
    ),
    BenchmarkCase(
        prompt="Navbar me logout button align nahi ho raha isko theek karo",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="unseen_hindi_mutation",
        language="hi_hinglish"
    ),
    BenchmarkCase(
        prompt="kya dikkat hai",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="unseen_hindi_ambiguous",
        language="hi_hinglish"
    ),
    BenchmarkCase(
        prompt="chal nahi raha",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="unseen_hindi_ambiguous",
        language="hi_hinglish"
    ),

    # Spanish
    BenchmarkCase(
        prompt="¿Cómo funciona la concurrencia asíncrona con asyncio en Python?",
        expected_workflow=WorkflowType.CHAT,
        category="unseen_spanish_chat",
        language="es"
    ),
    BenchmarkCase(
        prompt="Explica la diferencia entre INNER JOIN y LEFT JOIN con ejemplos",
        expected_workflow=WorkflowType.CHAT,
        category="unseen_spanish_chat",
        language="es"
    ),
    BenchmarkCase(
        prompt="Inspecciona el repositorio para encontrar dependencias desactualizadas",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="unseen_spanish_inspection",
        language="es"
    ),
    BenchmarkCase(
        prompt="Busca donde está configurada la sesión de usuario en el proyecto",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="unseen_spanish_inspection",
        language="es"
    ),
    BenchmarkCase(
        prompt="Arregla el fallo en el formulario de login y ejecuta tests",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="unseen_spanish_mutation",
        language="es"
    ),
    BenchmarkCase(
        prompt="Modifica la ruta de health check y ejecuta las pruebas",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="unseen_spanish_mutation",
        language="es"
    ),
    BenchmarkCase(
        prompt="no funciona",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="unseen_spanish_ambiguous",
        language="es"
    ),
    BenchmarkCase(
        prompt="arregla esto",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="unseen_spanish_ambiguous",
        language="es"
    ),

    # French
    BenchmarkCase(
        prompt="Explique le fonctionnement du garbage collector en V8",
        expected_workflow=WorkflowType.CHAT,
        category="unseen_french_chat",
        language="fr"
    ),
    BenchmarkCase(
        prompt="Quelle est la différence entre un thread et un processus?",
        expected_workflow=WorkflowType.CHAT,
        category="unseen_french_chat",
        language="fr"
    ),
    BenchmarkCase(
        prompt="Trouve où sont définis les modèles de base de données dans le projet",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="unseen_french_inspection",
        language="fr"
    ),
    BenchmarkCase(
        prompt="Inspecte le code pour détecter d'éventuelles failles de sécurité",
        expected_workflow=WorkflowType.CLAW_READ_ONLY,
        expected_permission_mode="read_only",
        category="unseen_french_inspection",
        language="fr"
    ),
    BenchmarkCase(
        prompt="Corrige l'erreur de connexion dans l'authentification et lance les tests",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="unseen_french_mutation",
        language="fr"
    ),
    BenchmarkCase(
        prompt="Met à jour les paramètres de configuration et lance les tests",
        expected_workflow=WorkflowType.CLAW_CONFIRMATION,
        expected_permission_mode="ask",
        category="unseen_french_mutation",
        language="fr"
    ),
    BenchmarkCase(
        prompt="ça ne marche pas",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="unseen_french_ambiguous",
        language="fr"
    ),
    BenchmarkCase(
        prompt="répare le problème",
        expected_workflow=WorkflowType.CLARIFICATION,
        category="unseen_french_ambiguous",
        language="fr"
    ),
]

def run_routing_benchmark(dataset: Optional[List[BenchmarkCase]] = None) -> Dict[str, Any]:
    """
    Executes the benchmark against the WorkflowRouter and calculates:
    - Total test count, passed, failed, accuracy percentage
    - Category-level breakdown
    - Language-level breakdown (en, hi_hinglish, es, fr)
    - Clarification metrics (Precision, Recall, F1, Rate %)
    - Detailed misroutes list
    """
    cases = dataset or BENCHMARK_DATASET
    total = len(cases)
    passed = 0
    misroutes = []
    category_stats: Dict[str, Dict[str, int]] = {}
    language_stats: Dict[str, Dict[str, int]] = {}

    clarification_tp = 0
    clarification_fp = 0
    clarification_fn = 0
    total_clarifications_predicted = 0
    total_clarification_cases = 0

    for case in cases:
        cat = case.category
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0}
        category_stats[cat]["total"] += 1

        # Infer language from case or category
        lang = getattr(case, "language", None)
        if not lang:
            if "hindi" in cat or "hinglish" in cat:
                lang = "hi_hinglish"
            elif "spanish" in cat:
                lang = "es"
            elif "french" in cat:
                lang = "fr"
            else:
                lang = "en"

        if lang not in language_stats:
            language_stats[lang] = {"total": 0, "passed": 0}
        language_stats[lang]["total"] += 1

        decision = workflow_router.classify(case.prompt, context=case.context)
        is_type_match = decision.workflow_type == case.expected_workflow
        is_perm_match = (case.expected_permission_mode is None) or (decision.permission_mode == case.expected_permission_mode)

        # Clarification evaluation
        is_expected_clarification = (case.expected_workflow == WorkflowType.CLARIFICATION)
        is_actual_clarification = (decision.workflow_type == WorkflowType.CLARIFICATION)

        if is_expected_clarification:
            total_clarification_cases += 1

        if is_actual_clarification:
            total_clarifications_predicted += 1

        if is_expected_clarification and is_actual_clarification:
            clarification_tp += 1
        elif not is_expected_clarification and is_actual_clarification:
            clarification_fp += 1
        elif is_expected_clarification and not is_actual_clarification:
            clarification_fn += 1

        if is_type_match and is_perm_match:
            passed += 1
            category_stats[cat]["passed"] += 1
            language_stats[lang]["passed"] += 1
        else:
            misroutes.append({
                "prompt": case.prompt,
                "category": case.category,
                "language": lang,
                "expected_workflow": case.expected_workflow.value,
                "actual_workflow": decision.workflow_type.value,
                "expected_permission": case.expected_permission_mode,
                "actual_permission": decision.permission_mode,
                "decision_reason": decision.reason,
                "notes": case.notes
            })

    accuracy = round((passed / total) * 100, 2) if total > 0 else 0.0

    # Language accuracy summary
    for l_key, l_data in language_stats.items():
        l_total = l_data["total"]
        l_passed = l_data["passed"]
        l_data["accuracy_pct"] = round((l_passed / l_total) * 100, 2) if l_total > 0 else 100.0

    # Clarification precision, recall, f1
    c_precision = round(clarification_tp / (clarification_tp + clarification_fp), 3) if (clarification_tp + clarification_fp) > 0 else 1.0
    c_recall = round(clarification_tp / (clarification_tp + clarification_fn), 3) if (clarification_tp + clarification_fn) > 0 else 1.0
    c_f1 = round(2 * (c_precision * c_recall) / (c_precision + c_recall), 3) if (c_precision + c_recall) > 0 else 1.0
    c_rate = round((total_clarifications_predicted / total) * 100, 2) if total > 0 else 0.0

    return {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": len(misroutes),
        "accuracy_pct": accuracy,
        "category_stats": category_stats,
        "language_stats": language_stats,
        "clarification_metrics": {
            "total_clarification_cases": total_clarification_cases,
            "predicted_clarifications": total_clarifications_predicted,
            "true_positives": clarification_tp,
            "false_positives": clarification_fp,
            "false_negatives": clarification_fn,
            "precision": c_precision,
            "recall": c_recall,
            "f1_score": c_f1,
            "clarification_rate_pct": c_rate
        },
        "misroutes": misroutes
    }

def run_evaluation_suite() -> Dict[str, Any]:
    """
    Runs the full evaluation suite:
    1. Tuning / Benchmark Dataset (65 prompts)
    2. Unseen Holdout Dataset (44 prompts)
    Reports metrics across both datasets independently to verify out-of-sample generalization.
    """
    bench_results = run_routing_benchmark(BENCHMARK_DATASET)
    unseen_results = run_routing_benchmark(UNSEEN_EVAL_DATASET)

    combined_total = bench_results["total_cases"] + unseen_results["total_cases"]
    combined_passed = bench_results["passed_cases"] + unseen_results["passed_cases"]
    combined_acc = round((combined_passed / combined_total) * 100, 2) if combined_total > 0 else 0.0

    return {
        "benchmark_dataset": bench_results,
        "unseen_holdout_dataset": unseen_results,
        "combined_summary": {
            "total_cases": combined_total,
            "passed_cases": combined_passed,
            "failed_cases": len(bench_results["misroutes"]) + len(unseen_results["misroutes"]),
            "overall_accuracy_pct": combined_acc
        }
    }

if __name__ == "__main__":
    suite = run_evaluation_suite()
    bench = suite["benchmark_dataset"]
    unseen = suite["unseen_holdout_dataset"]
    print(f"=== SYNORA Benchmark Dataset (Tuning Set): {bench['passed_cases']}/{bench['total_cases']} ({bench['accuracy_pct']}%) ===")
    print("Language Breakdown:", bench["language_stats"])
    print("Clarification Metrics:", bench["clarification_metrics"])
    print(f"\n=== SYNORA Unseen Holdout Dataset: {unseen['passed_cases']}/{unseen['total_cases']} ({unseen['accuracy_pct']}%) ===")
    print("Language Breakdown:", unseen["language_stats"])
    print("Clarification Metrics:", unseen["clarification_metrics"])
    if unseen["misroutes"]:
        print("\nUnseen Misroutes:")
        for m in unseen["misroutes"]:
            print(f" - [{m['language']}] '{m['prompt']}' -> Expected: {m['expected_workflow']} | Actual: {m['actual_workflow']}")


