"""
SYNORA Workflow Router
Workflow-routing layer executed BEFORE model selection:

1. “Explain this code” -> Chat (Conversational & Multi-Stage Model Orchestration).
2. “Find the bug in my project” -> Claw Code with read-only access (workspace inspection).
3. “Fix the bug and run tests” -> Claw Code with confirmation before changes or commands (ask mode).
4. Ambiguous request -> Ask a clarifying question.

Handles edge cases:
- Mutating tasks without explicit "run tests" (e.g. "fix the login bug") -> Claw with confirmation
- Compound tasks (e.g. "explain and fix this file") -> Claw with confirmation
- Follow-up prompts leveraging session context
- Multilingual and Hindi/Hinglish requests
"""

import re
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class WorkflowType(str, Enum):
    CHAT = "chat"
    CLAW_READ_ONLY = "claw_read_only"
    CLAW_CONFIRMATION = "claw_confirmation"
    CLARIFICATION = "clarification"

class WorkflowDecision(BaseModel):
    workflow_type: WorkflowType
    reason: str
    confidence: float
    permission_mode: Optional[str] = None  # "read_only", "ask", or None for chat
    suggested_runtime: str                 # "orchestrator", "claw_agent", or "clarification"
    clarification_question: Optional[str] = None
    clarification_options: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Ambiguous phrases that lack target context (file, code snippet, or specific error)
AMBIGUOUS_PATTERNS = [
    # English
    r"^(?:please\s+)?(?:fix|debug|solve|repair)\s+(?:it|this|that|the\s+bug|the\s+issue|the\s+error)$",
    r"^(?:why\s+is\s+it\s+(?:failing|broken|crashing)|why\s+it\s+fails|why\s+does\s+it\s+fail)$",
    r"^(?:please\s+)?(?:make\s+it\s+work|it\s+doesn'?t\s+work|it\s+is\s+broken|it\s+failed)(?:\s+please)?$",
    r"^it\s+(?:crashed|broke|failed)(?:\s+again)?$",
    r"^(?:help\s+me|help\s+with\s+this|fix\s+code|debug\s+code)$",
    r"^(?:run\s+it|test\s+it|execute\s+it)$",
    r"^(?:update\s+it|change\s+it|modify\s+it)$",
    # Hindi / Hinglish
    r"^(?:isko\s+|ye\s+)?(?:theek|sahi|fix)\s+(?:karo|kar\s+do|kar\s+de)$",
    r"^(?:chal\s+nahi\s+raha|chal\s+nahi\s+raha\s+hai|kaam\s+nahi\s+kar\s+raha)$",
    r"^(?:kya\s+dikkat\s+hai|kya\s+problem\s+hai|kya\s+error\s+hai)$",
    # Spanish
    r"^(?:por\s+favor\s+)?(?:arregla|repara|corrige)\s+(?:esto|eso|el\s+error|el\s+bug|el\s+fallo)$",
    r"^(?:no\s+funciona|est[aá]\s+roto|fall[oó]|ayuda(?:\s+con\s+esto)?)$",
    # French
    r"^(?:s'il\s+vous\s+pla[iî]t\s+)?(?:r[eé]pare|corrige)\s+(?:[cç]a|ceci|le\s+bug|le\s+probl[eè]me)$",
    r"^(?:[cç]a\s+ne\s+marche\s+pas|[cç]a\s+ne\s+fonctionne\s+pas|c'est\s+cass[eé]|aidez-moi)$",
]

# Explanatory & conceptual markers (route to Chat)
EXPLANATION_INDICATORS = [
    # English
    "explain", "what is", "what does", "how does", "teach me", "walk me through",
    "overview", "difference between", "why does", "pros and cons", "how to write",
    "concept of", "understand", "meaning of", "clarify", "review", "compare",
    # Hindi / Hinglish
    "explain karo", "samjhao", "samjha do", "kya karta hai", "kaise kaam karta hai",
    "batao", "bataiye", "iska matlab kya hai", "kya hota hai",
    # Spanish / French
    "explica", "como funciona", "¿cómo funciona", "que es", "ensename", "diferencia entre",
    "explique", "comment fonctionne", "qu'est-ce que", "quelle est", "différence entre", "comparaison"
]

# Workspace scope indicators (referring to local repo/project)
WORKSPACE_SCOPE_INDICATORS = [
    "my project", "the project", "this project", "my codebase", "the codebase",
    "this codebase", "my repo", "the repo", "this repo", "my workspace",
    "the workspace", "in the project", "in this project", "in my project",
    "in the repo", "in this repo", "in our repo", "across the codebase",
    "in the files", "in this directory", "in our project", "in the code", "in my code",
    # Hindi / Hinglish
    "project me", "repo me", "codebase me", "files me", "code me", "is code me",
    # Spanish / French
    "en mi proyecto", "en el repositorio", "en el codigo", "dans mon projet", "dans le code"
]

# Mutating verbs (action altering files, fixing code, or applying changes)
MUTATING_VERBS = [
    # English
    "fix", "modify", "edit", "refactor", "patch", "implement", "update",
    "change", "rewrite", "replace", "create", "write", "commit", "install", "repair", "resolve",
    # Hindi / Hinglish
    "theek karo", "theek kar do", "theek kar de", "theek kardo", "theek karde",
    "fix karo", "fix kar do", "fix kar de", "fix kardo", "fix karde",
    "sahi karo", "sahi kar do", "sahi kardo", "sahi karde", "badlo", "change karo", "update karo",
    # Spanish / French
    "arregla", "corrige", "modifica", "repara", "actualiza",
    "modifie", "repare", "met à jour", "mets à jour"
]

EXECUTION_INDICATORS = [
    "run test", "run tests", "run pytest", "npm test", "pytest", "cargo test",
    "unittest", "test it", "and test", "and run", "execute tests", "run the test",
    "run build", "build the project", "verify tests", "run commands", "failing test",
    "commit changes", "commit", "git commit", "run script", "bash command",
    # Hindi / Hinglish
    "test chalao", "test run karo", "run karke dekho", "tests verify karo", "verify karo",
    # Spanish / French
    "ejecuta las pruebas", "corre las pruebas", "ejecuta tests", "lance les tests"
]

BUG_FINDING_INDICATORS = [
    # English
    "find the bug", "find bugs", "locate bug", "search the bug", "diagnose bug",
    "identify bug", "detect bug", "audit codebase", "inspect project", "find issue",
    "where is the bug", "look for bugs", "audit my codebase", "search where",
    # Hindi / Hinglish
    "bug dhoondho", "bug dhoondh", "bug dekho", "galti dhoondho", "check karo",
    "inspect karo", "dikkat dhoondho", "search karo",
    # Spanish / French
    "busca el fallo", "encuentra el error", "busca bugs", "inspecciona el repositorio",
    "busca donde", "busca dónde", "trouve le bug", "cherche le bug", "trouve où",
    "inspecte le code", "inspecte"
]

class WorkflowRouter:
    """
    Intelligent workflow classifier directing requests to the proper execution runtime:
    - Chat (pure explanation/synthesis)
    - Claw Code Read-Only (safe workspace inspection & diagnosis)
    - Claw Code Interactive (workspace changes & command execution with confirmation)
    - Clarification (interactive question when request is underspecified)
    """

    def is_ambiguous(
        self,
        prompt: str,
        context: Optional[str] = None,
        has_attachments: bool = False
    ) -> bool:
        """
        Detects if a request is too vague to safely execute without clarification.
        Takes prior conversation context into account (resolving follow-ups).
        """
        clean = prompt.strip().lower().rstrip(".!?~")
        words = clean.split()

        # If attachments exist, request has provided artifacts
        if has_attachments:
            return False

        # If rich conversation context exists (e.g. error trace, file path, or prior turn > 25 chars),
        # follow-ups like "fix it" or "now fix line 45" are NOT ambiguous!
        if context and len(context.strip()) > 25:
            code_or_file_in_context = any(
                sig in context.lower()
                for sig in ["def ", "class ", "error", "traceback", "file", "line ", "/", ".py", ".js", ".ts"]
            )
            if code_or_file_in_context:
                return False

        # If code fences exist in the prompt itself, user provided code
        if "```" in prompt:
            return False

        # If specific file paths or extensions are mentioned, target is known
        file_ext_pattern = r"\b[\w\-./]+\.(?:py|js|ts|tsx|jsx|json|html|css|rs|go|cpp|c|md|ya?ml|sql)\b"
        if re.search(file_ext_pattern, prompt, re.IGNORECASE):
            return False

        # Matches known ambiguous patterns
        for pattern in AMBIGUOUS_PATTERNS:
            if re.match(pattern, clean):
                return True

        # Single-word vague commands like "update", "fix", "change", "theek"
        if len(words) == 1 and words[0] in {"fix", "debug", "solve", "repair", "run", "check", "test", "update", "theek", "sahi", "badlo", "modify"}:
            return True

        # Extremely short prompts (<= 3 words) mentioning a fix/debug with no target
        if len(words) <= 3:
            vague_verbs = {"fix", "debug", "solve", "repair", "run", "check", "test", "update", "theek", "sahi"}
            vague_nouns = {"it", "this", "that", "code", "bug", "error", "issue", "isko", "ye"}
            if any(w in vague_verbs for w in words) and any(w in vague_nouns for w in words):
                return True

        return False

    def classify(
        self,
        prompt: str,
        context: Optional[str] = None,
        has_attachments: bool = False,
        workflow_override: Optional[str] = None
    ) -> WorkflowDecision:
        """
        Classifies incoming prompt into the exact workflow before model selection.
        Supports manual overrides: 'chat', 'inspect' / 'claw_read_only', 'mutate' / 'claw_confirmation'.
        """
        clean_prompt = prompt.strip()
        prompt_lower = clean_prompt.lower()
        words = set(re.findall(r"\b\w+\b", prompt_lower))

        # 0. Manual Override
        if workflow_override:
            override_clean = workflow_override.strip().lower()
            if override_clean in ("chat", "conversational", "orchestrator"):
                return WorkflowDecision(
                    workflow_type=WorkflowType.CHAT,
                    reason=f"Manual user override selected: Chat ({workflow_override})",
                    confidence=1.0,
                    permission_mode=None,
                    suggested_runtime="orchestrator",
                    metadata={"override": workflow_override}
                )
            elif override_clean in ("inspect", "inspect_project", "claw_read_only", "read_only"):
                return WorkflowDecision(
                    workflow_type=WorkflowType.CLAW_READ_ONLY,
                    reason=f"Manual user override selected: Inspect Project ({workflow_override})",
                    confidence=1.0,
                    permission_mode="read_only",
                    suggested_runtime="claw_agent",
                    metadata={"override": workflow_override}
                )
            elif override_clean in ("mutate", "make_changes", "changes", "claw_confirmation", "ask"):
                return WorkflowDecision(
                    workflow_type=WorkflowType.CLAW_CONFIRMATION,
                    reason=f"Manual user override selected: Make Changes ({workflow_override})",
                    confidence=1.0,
                    permission_mode="ask",
                    suggested_runtime="claw_agent",
                    metadata={"override": workflow_override}
                )
            elif override_clean in ("clarify", "clarification"):
                return WorkflowDecision(
                    workflow_type=WorkflowType.CLARIFICATION,
                    reason="Manual user override selected: Clarification",
                    confidence=1.0,
                    permission_mode=None,
                    suggested_runtime="clarification"
                )

        # 1. Ambiguity Gate -> Ask Clarifying Question
        if self.is_ambiguous(clean_prompt, context=context, has_attachments=has_attachments):
            return WorkflowDecision(
                workflow_type=WorkflowType.CLARIFICATION,
                reason="The request is underspecified without code context, file path, or target component.",
                confidence=0.95,
                permission_mode=None,
                suggested_runtime="clarification",
                clarification_question=(
                    "Your request is ambiguous. What would you like to do?\n\n"
                    "1. **Explain code or concept** (Chat)\n"
                    "2. **Find and diagnose the bug in your project** (Claw Code - Read-Only)\n"
                    "3. **Fix the bug and run tests** (Claw Code - Confirmation required before changes)\n\n"
                    "Please provide the relevant file path, code snippet, or specify which mode to use."
                ),
                clarification_options=[
                    "Explain this code (Chat)",
                    "Find the bug in my project (Claw Read-Only)",
                    "Fix the bug and run tests (Claw with Confirmation)"
                ]
            )

        # 1b. Git Inspection (Read-Only diff, status, or log)
        if any(g in prompt_lower for g in ["git diff", "uncommitted changes", "git status", "git log", "show diff"]):
            has_commit_action = bool(re.search(r"\b(?:git\s+)?commit\b", prompt_lower)) and ("uncommitted" not in prompt_lower or "commit changes" in prompt_lower)
            if not has_commit_action and not any(a in prompt_lower for a in ["apply", "revert", "discard", "reset --hard"]):
                return WorkflowDecision(
                    workflow_type=WorkflowType.CLAW_READ_ONLY,
                    reason="Request asks to inspect git diff or workspace status in read-only mode.",
                    confidence=0.98,
                    permission_mode="read_only",
                    suggested_runtime="claw_agent",
                    metadata={"action": "git_inspection"}
                )

        has_mutation = any(bool(re.search(rf"\b{re.escape(mv)}\b", prompt_lower)) for mv in MUTATING_VERBS)
        has_execution = any(ei in prompt_lower for ei in EXECUTION_INDICATORS)
        has_workspace_scope = any(ws in prompt_lower for ws in WORKSPACE_SCOPE_INDICATORS)
        has_bug_finding = any(bf in prompt_lower for bf in BUG_FINDING_INDICATORS)
        is_explanation = any(ei in prompt_lower for ei in EXPLANATION_INDICATORS)

        # 2. Compound requests ("explain and fix this file", "review and refactor")
        # When a prompt demands BOTH explanation AND code modification, it MUST run through Claw Code
        # with confirmation so the requested modifications are executed safely!
        if is_explanation and has_mutation:
            return WorkflowDecision(
                workflow_type=WorkflowType.CLAW_CONFIRMATION,
                reason="Compound request requires code modification alongside explanation; confirmation enforced.",
                confidence=0.95,
                permission_mode="ask",
                suggested_runtime="claw_agent",
                metadata={"action": "explain_and_fix"}
            )

        # 3. Check for "Fix the bug and run tests" OR any mutating request with execution
        if has_mutation and (has_execution or "and test" in prompt_lower or "and run" in prompt_lower):
            return WorkflowDecision(
                workflow_type=WorkflowType.CLAW_CONFIRMATION,
                reason="Request requires modifying code and executing tests/commands in workspace.",
                confidence=0.96,
                permission_mode="ask",
                suggested_runtime="claw_agent",
                metadata={"action": "mutate_and_test"}
            )

        # 4. Check for targeted bug fix WITHOUT "run tests" (e.g. "fix the login bug", "fix the navbar issue", "bhai login bug fix kar de")
        # If the user names a specific component/bug to fix, it is a code-modifying agent task!
        targets_specific_fix = any(
            t in prompt_lower
            for t in ["bug", "issue", "error", "crash", "typo", "leak", "vulnerability", "auth", "login", "problem", "chal nahi raha", "kaam nahi kar raha", "button", "navbar", "ui", "align"]
        ) and has_mutation

        if targets_specific_fix:
            return WorkflowDecision(
                workflow_type=WorkflowType.CLAW_CONFIRMATION,
                reason="Request targets fixing a specific component or bug; confirmation enforced before file edits.",
                confidence=0.94,
                permission_mode="ask",
                suggested_runtime="claw_agent",
                metadata={"action": "fix_targeted_bug"}
            )

        # 5. Follow-ups with mutation (e.g. context has file/code, user says "now fix line 45" or "apply the change")
        if context and has_mutation and any(tok in words for tok in ["now", "apply", "change", "this", "line", "it"]):
            return WorkflowDecision(
                workflow_type=WorkflowType.CLAW_CONFIRMATION,
                reason="Follow-up request modifying code based on previous conversation context.",
                confidence=0.93,
                permission_mode="ask",
                suggested_runtime="claw_agent",
                metadata={"action": "context_followup_fix"}
            )

        # 6. Check for "Find the bug in my project" / code inspection -> Claw Code (Read-Only)
        is_inspect_search = any(w in words for w in [
            "search", "grep", "locate", "find", "inspect", "audit", "trace", "check",
            "busca", "buscar", "inspecciona", "trouve", "trouver", "inspecte", "cherche", "chercher",
            "dhoondh", "dhoondho", "dhundo", "dhundh", "khojo", "where"
        ])
        has_code_scope = has_workspace_scope or any(w in words for w in [
            "project", "repo", "codebase", "files", "code", "service", "app", "module",
            "backend", "frontend", "api", "auth", "component", "function", "class",
            "database", "models", "model", "schema", "routes", "decorator", "decorators",
            "repositorio", "proyecto", "projet", "modèles", "modèle"
        ])
        is_location_query = bool(re.search(
            r"\b(?:where|donde|dónde|où)\b.*\b(?:defined|located|implemented|stored|written|found|configurada|configurado|définis|défini)\b",
            prompt_lower
        ))

        if (has_bug_finding or is_inspect_search or is_location_query) and (has_code_scope or "bug" in words or "issue" in words or is_location_query):
            if not has_mutation and not has_execution:
                return WorkflowDecision(
                    workflow_type=WorkflowType.CLAW_READ_ONLY,
                    reason="Request asks to find/inspect bugs or search codebase in read-only mode.",
                    confidence=0.95,
                    permission_mode="read_only",
                    suggested_runtime="claw_agent",
                    metadata={"action": "inspect_only"}
                )

        # 7. Check for "Explain this code" -> Chat
        if is_explanation or ("explain" in words and "code" in words) or ("samjhao" in words or "batao" in words):
            return WorkflowDecision(
                workflow_type=WorkflowType.CHAT,
                reason="Request asks for code or conceptual explanation.",
                confidence=0.98,
                permission_mode=None,
                suggested_runtime="orchestrator",
                metadata={"action": "explain"}
            )

        # 8. General workspace mutation fallback
        if has_mutation and (has_workspace_scope or "file" in words or "in " in prompt_lower):
            return WorkflowDecision(
                workflow_type=WorkflowType.CLAW_CONFIRMATION,
                reason="Request requires modifying workspace files; confirmation enforced.",
                confidence=0.90,
                permission_mode="ask",
                suggested_runtime="claw_agent",
                metadata={"action": "mutate_workspace"}
            )

        # Default to standard Chat Orchestration
        return WorkflowDecision(
            workflow_type=WorkflowType.CHAT,
            reason="Standard conversational or conceptual query.",
            confidence=0.85,
            permission_mode=None,
            suggested_runtime="orchestrator"
        )

workflow_router = WorkflowRouter()
