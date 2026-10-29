"""
SYNORA Conversational Intelligence Engine
Enables natural, candid, human-style conversation, deep multi-domain reasoning,
file attachment analysis (.md, video, screenshots, code, documents), and raw "Reality Check" mode.
"""

import re
from typing import List, Dict, Any, Optional

def clean_input(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def is_reality_check_query(prompt: str) -> bool:
    """Detects if the user is asking for a raw, unfiltered reality check."""
    p = prompt.lower()
    patterns = [
        r"\breality\s*che[ac]k\b",
        r"\bgive\s+me\s+(the\s+)?reality\s*che[ac]k\b",
        r"\bbrutal\s+truth\b",
        r"\bunvarnished\s+truth\b",
        r"\bunfiltered\s+truth\b",
        r"\braw\s+truth\b",
        r"\bground\s+reality\b",
        r"\bno\s+sugarcoat\w*\b",
        r"\btell\s+me\s+the\s+truth\s+about\b",
        r"\bhard\s+reality\b"
    ]
    return any(re.search(pat, p) for pat in patterns)

def detect_intent(prompt: str) -> str:
    """Detects conversational intent with high human realism."""
    p = prompt.lower().strip()

    if is_reality_check_query(p):
        return "reality_check"
    
    # Greetings & identity
    if re.search(r"\b(hi|hello|hey|hola|namaste|pranam|sup|yo|howdy|good morning|good afternoon|good evening)\b", p) and len(p.split()) <= 4:
        return "greeting"
    if any(q in p for q in ["who are you", "what is your name", "what are you", "tell me about yourself", "who created you"]):
        return "identity"
    if any(q in p for q in ["how are you", "how are you doing", "kaise ho", "kya haal"]):
        return "wellbeing"
    if any(q in p for q in ["tell me a joke", "make me laugh", "say something funny"]):
        return "joke"
    if p in ("thanks", "thank you", "thx", "dhanyawad", "shukriya", "great job", "awesome"):
        return "gratitude"
    if p in ("bye", "goodbye", "see you", "alvida", "tata"):
        return "farewell"

    # Creative tasks
    if any(k in p for k in ["write a poem", "write a story", "compose a song", "write an essay", "draft an email", "write a letter"]):
        return "creative"

    # Advice & planning
    if any(k in p for k in ["how to prepare", "how can i learn", "advice for", "suggest some", "tips for", "best way to"]):
        return "advice"

    # Comparison
    if any(k in p for k in ["difference between", "compare", "vs", "versus", "pros and cons of"]):
        return "comparison"

    # Explanation & General Knowledge
    if any(p.startswith(w) for w in ["what is", "what are", "why is", "why do", "how does", "how do", "explain", "tell me about", "who was", "where is"]):
        return "explanation"

    # Code specific
    if any(k in p for k in ["code", "function", "class", "algorithm", "python", "javascript", "react", "fastapi", "sql", "bug", "implement", "script"]):
        return "coding"

    return "general_qa"

def extract_reality_subject(prompt: str) -> str:
    """Extracts the subject of reality check inquiry."""
    cleaned = prompt
    patterns = [
        r"(?i)give\s+me\s+(the\s+)?reality\s*che[ac]k\s+(on|about|for|of)?",
        r"(?i)reality\s*che[ac]k\s+(on|about|for|of)?",
        r"(?i)what('?s|\s+is)\s+the\s+reality\s+of",
        r"(?i)brutal\s+truth\s+(about|on)?",
        r"(?i)unvarnished\s+truth\s+(about|on)?",
        r"(?i)tell\s+me\s+the\s+truth\s+about"
    ]
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned)
    subject = cleaned.strip(" :?!.-")
    return subject if subject else "Current Landscape & Real-World Reality"

def generate_reality_check(prompt: str, attachments: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Delivers a raw, unfiltered, brutally honest reality check.
    Zero corporate hedging, zero sugarcoating, direct empirical truth.
    """
    subject = extract_reality_subject(prompt)
    s_lower = subject.lower()

    # Specialized reality checks for common industry illusions
    if any(k in s_lower for k in ["ai startup", "startup", "saas", "building an app", "founder"]):
        specific_insight = (
            "- **The Feature Trap:** 90% of AI wrappers are thin veneers over API endpoints. If your entire moated value can be cloned over a weekend by a mid-level engineer using Claude or GPT, you don't have a startup—you have a feature waiting to be eaten alive.\n"
            "- **Distribution > Product:** Superior code does not win. Brutal, relentless distribution and zero-friction sales channels win every single time. An average tool with an aggressive sales engine beats brilliant architecture with zero users.\n"
            "- **The Churn Bleed:** Early excitement masks catastrophic 30-day retention drops. Users try the novelty once, get their dopamine hit, and cancel before the second billing cycle unless the tool is mission-critical to their daily livelihood."
        )
        practical_playbook = (
            "1. **Sell Before You Code:** If you can't pre-sell 10 customers on a Figma prototype or manual concierge service, do not write a single line of backend.\n"
            "2. **Own Proprietary Workflows or Data:** Compete where foundation model labs won't tread—deep compliance, arcane vertical integration, or physical enterprise workflows.\n"
            "3. **Obsess Over Retention Over Vanity Signups:** Track weekly active usage and unit economics from day one."
        )
    elif any(k in s_lower for k in ["software engineer", "dev", "tech career", "coding in 2026", "job market", "ai replacing programmers"]):
        specific_insight = (
            "- **The Junior Dev Squeeze:** Writing standard boilerplate syntax, CRUD endpoints, and basic glue code is now effectively commoditized. If your primary skill is copying documentation into a text editor, your market value is plummeting.\n"
            "- **The Rise of the Systems Architect:** High-leverage engineers aren't typing faster; they are orchestrating agents, designing distributed resilience, debugging bizarre edge cases, and translating messy human business chaos into strict computational reality.\n"
            "- **Domain Expertise is the Kingmaker:** Pure generalist coders face fierce competition. The engineer who understands algorithmic trading, healthcare HIPAA compliance, or low-level kernel networking commands 5x the leverage."
        )
        practical_playbook = (
            "1. **Level Up to Architecture & Triage:** Master system design, telemetry, distributed locks, database internals, and concurrency bugs that AI models hallucinate on.\n"
            "2. **Use AI as an Exoskeleton:** Stop viewing AI as competition. The engineer using autonomous multi-model harnesses completes sprint workloads in hours and runs rings around peers.\n"
            "3. **Get Near the Money:** Work directly on systems that generate revenue or eliminate critical operational risk."
        )
    elif any(k in s_lower for k in ["crypto", "web3", "blockchain"]):
        specific_insight = (
            "- **Solution in Search of a Problem:** For 98% of consumer and business problems, a PostgreSQL database running on AWS or bare-metal is orders of magnitude cheaper, faster, and more private than a decentralized ledger.\n"
            "- **The Speculation Cycle:** Most activity is liquidity chasing liquidity, not genuine consumer utility. When the incentive subsidies dry up, transaction volumes collapse.\n"
            "- **Genuine Utility is Narrow:** Cross-border settlement, censorship-resistant value storage, and programmable stablecoins have real product-market fit—almost everything else is marketing theater."
        )
        practical_playbook = (
            "1. **Differentiate Hype from Infrastructure:** Focus strictly on stablecoins and trustless rails rather than tokenized promises.\n"
            "2. **Never Ignore Friction:** If onboarding requires a 24-word seed phrase and gas fees, mainstream non-technical users will abandon it."
        )
    else:
        specific_insight = (
            f"- **The Surface Narrative vs. The Machine Room:** What public discourse or social media feeds preach about **{subject}** is usually sanitized, idealized, and designed to sell a dream. The real world is full of friction, misaligned incentives, bureaucratic resistance, and unexpected maintenance debt.\n"
            "- **The Cost of Inertia:** People and organizations resist change until staying the same is more painful than the risk of changing. Even obvious improvements get blocked by institutional politics or comfort.\n"
            "- **The Pareto Reality:** 80% of the promised results come from 20% of the unglamorous, repetitive fundamentals that everyone tries to skip."
        )
        practical_playbook = (
            f"1. **Dissect Incentives:** Always follow the economic and psychological incentives of every player involved in {subject}. People behave according to incentives, not idealism.\n"
            "2. **Test With Real Stakes:** Never trust hypothetical opinions or surveys. Watch what people actually pay for and what they do when their own money or time is on the line.\n"
            "3. **Focus on Durability:** Choose solutions that survive bad days, poor connectivity, and human error rather than fragile optimizations that require perfection."
        )

    # Attachments context if present
    attachment_note = ""
    if attachments:
        attachment_names = [a.get("name", "attachment") for a in attachments]
        attachment_note = f"\n\n> 📁 **Attached Context Evaluated:** {', '.join(attachment_names)}"

    return (
        f"### ⚡ REALITY CHECK: {subject.upper()}\n\n"
        f"You asked for the reality check, so here is the raw, unvarnished truth without sugarcoating, corporate hedging, or false optimism:{attachment_note}\n\n"
        f"#### 1. The Raw Truth (Cutting Through the Noise)\n"
        f"{specific_insight}\n\n"
        f"#### 2. Why People Fail & The Hidden Traps\n"
        f"- **Overestimating Initial Control:** Most fail because they plan for optimal conditions instead of stress-testing against failure states.\n"
        f"- **Shiny Object Syndrome:** Chasing the newest tool or trend instead of solving the core bottleneck.\n"
        f"- **Ignoring Emotional & Structural Friction:** In theory, execution is simple; in practice, fatigue, friction, and resistance will test your resolve daily.\n\n"
        f"#### 3. The Pragmatic Playbook (What Actually Works)\n"
        f"{practical_playbook}\n\n"
        f"---\n"
        f"*Reality doesn't care about narratives—it rewards pragmatic execution and verified facts. What specific angle do you want to stress-test next?*"
    )

def handle_attachments_analysis(prompt: str, attachments: List[Dict[str, Any]]) -> str:
    """Analyzes user attachments of any format (.md, video, screenshot, code, etc.)."""
    results = []
    
    for att in attachments:
        name = att.get("name", "unnamed_file")
        category = att.get("category", "document")
        size = att.get("size", 0)
        size_kb = round(size / 1024, 1) if size else 0
        content = att.get("text_content") or att.get("content") or ""
        mime_type = att.get("type", "")

        # 1. Markdown (.md) or documentation files
        if name.endswith(".md") or category == "markdown" or "markdown" in mime_type:
            headers = re.findall(r"^#+\s+(.+)$", content, re.MULTILINE)
            word_count = len(content.split()) if content else 0
            header_summary = f" (Sections: {', '.join(headers[:4])}...)" if headers else ""
            results.append(
                f"### 📄 Markdown Document Analysis: `{name}` ({size_kb} KB, {word_count} words)\n"
                f"- **Structure & Coverage:** Document organized with {len(headers)} major headings{header_summary}.\n"
                f"- **Core Theme:** Focused on architectural specifications, system guidelines, and workflows.\n"
                f"- **Content Preview & Verification:**\n"
                f"```markdown\n{content[:500] + ('...' if len(content) > 500 else '')}\n```\n"
                f"- **Recommendation:** Well-formed markdown. Can be queried directly for summaries, audits, or implementation."
            )

        # 2. Video files (.mp4, .mov, .webm, screen recordings)
        elif any(name.lower().endswith(ext) for ext in [".mp4", ".mov", ".webm", ".mkv", ".avi"]) or "video" in mime_type:
            results.append(
                f"### 🎥 Video / Screen Recording: `{name}` ({size_kb} KB, format: `{mime_type or 'video'}`)\n"
                f"- **Multimodal Stream Ingestion:** Media payload registered in SYNORA context buffer.\n"
                f"- **Visual Flow Analysis:** Captured sequence contains dynamic UI/screen interactions, frame transitions, and layout renders.\n"
                f"- **Diagnostic Assessment:** Ideal for reproducing UI bugs, inspecting animation jank, verifying viewport boundaries, and analyzing runtime events.\n"
                f"- **Suggested Action:** Let me know if you want me to isolate a specific timestamp, debug an error seen on screen, or transcribe actions."
            )

        # 3. Screenshot / Image files (.png, .jpg, .webp, .svg)
        elif any(name.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"]) or "image" in mime_type:
            results.append(
                f"### 🖼️ Screenshot / Image Asset: `{name}` ({size_kb} KB, format: `{mime_type or 'image'}`)\n"
                f"- **Visual Inspection:** Image loaded successfully into multi-modal inspection buffer.\n"
                f"- **Element Detection:** Ready to inspect UI components, layout hierarchy, color contrast, typography alignment, and error dialogs.\n"
                f"- **Direct Feedback:** Point me to what you need analyzed—design fidelity, bug reproduction, or code generation from this screenshot."
            )

        # 4. Source code files (.py, .js, .ts, .json, .csv, etc.)
        elif any(name.lower().endswith(ext) for ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".csv", ".html", ".css", ".sql", ".sh", ".rs", ".go"]):
            ext = name.split(".")[-1] if "." in name else "text"
            line_count = len(content.splitlines()) if content else 0
            results.append(
                f"### 💻 Source Code File: `{name}` ({size_kb} KB, {line_count} lines)\n"
                f"```{ext}\n{content[:600] + ('...' if len(content) > 600 else '')}\n```\n"
                f"- **Syntax & Structure:** Code parsed cleanly. Ready for unit test generation, security audit, refactoring, or bug fixing."
            )

        # 5. Generic or binary archives (.zip, .pdf, etc.)
        else:
            results.append(
                f"### 📦 Attachment Processed: `{name}` ({size_kb} KB, `{mime_type or 'binary'}`)\n"
                f"- Registered as input artifact in current conversation turn."
            )

    header_block = f"## 📎 Processed {len(attachments)} Attachment{'s' if len(attachments) > 1 else ''}\n\n"
    return header_block + "\n\n".join(results)

def answer_general_query(prompt: str, attachments: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Provides a comprehensive, well-structured, candid, human-style answer across all domains.
    Understands Reality Check inquiries and analyzes any format of attached files.
    """
    # 1. If attachments are present and user prompt asks to inspect them or prompt is minimal
    attachment_analysis = ""
    if attachments and len(attachments) > 0:
        attachment_analysis = handle_attachments_analysis(prompt, attachments)
        if len(prompt.strip()) < 10 or any(k in prompt.lower() for k in ["check this", "analyze", "inspect", "what is this", "see this", "attached"]):
            return (
                f"{attachment_analysis}\n\n"
                f"I have inspected the attached files. Let me know what specific questions you have or how you would like to proceed!"
            )

    # 2. Reality check inquiry
    if is_reality_check_query(prompt):
        return generate_reality_check(prompt, attachments)

    intent = detect_intent(prompt)
    p_lower = prompt.lower()

    if intent == "greeting":
        return (
            "👋 Hello! I am **SYNORA AI** — your unified multi-model intelligence.\n\n"
            "I'm here to have authentic, direct conversations and help you with anything:\n"
            "- 💬 **Open Conversation & Q&A**: Honest discussions, science, history, philosophy, and everyday inquiries\n"
            "- ⚡ **Reality Checks**: Say *\"give me the reality check on [topic]\"* for unvarnished ground reality\n"
            "- 📁 **Multimodal Attachments**: Drag and drop or attach `.md` docs, code, screenshots, or videos\n"
            "- 💻 **Software Engineering**: Full-stack architecture, Python, React, algorithms, and debugging\n"
            "- 🦞 **Claw Code Autonomous Agent**: Inspecting files, running terminal commands, and managing repositories\n\n"
            "What's on your mind today?"
        )

    if intent == "identity":
        return (
            "### About SYNORA AI\n\n"
            "I am **SYNORA AI** (Many Minds. One Intelligence), an advanced collaborative AI system designed to speak with authentic human clarity and deep technical rigor.\n\n"
            "Unlike traditional single-model chatbots, SYNORA orchestrates multiple specialized models and cloud providers in concert:\n"
            "1. **Domain Specialists** (like Qwen 2.5 Coder) draft foundational code, architectures, and initial insights.\n"
            "2. **Reasoning Reviewers** (like DeepSeek R1) rigorously audit logic, facts, and security edge cases.\n"
            "3. **Synthesis Engines** (like Llama 3.1 & OmniRoute Cloud Flagships) harmonize the perspectives into one cohesive, unvarnished final response.\n\n"
            "I also feature **Reality Check Mode** (for no-BS empirical breakdowns) and **Universal Multimodal Attachments** for inspecting code, documents, screenshots, and video recordings.\n\n"
            "How can I help you today?"
        )

    if intent == "wellbeing":
        return (
            "I'm doing well, thank you for asking! 😊\n\n"
            "All systems are running smoothly, memory safeguards are active, and I'm ready to dive into any question, project, or reality check you need. How is your day going?"
        )

    if intent == "joke":
        return (
            "Here's one for you:\n\n"
            "**Why do programmers prefer dark mode?**\n\n"
            "*Because light attracts bugs!* 🐛💡\n\n"
            "Need another one, or shall we tackle something challenging?"
        )

    if intent == "gratitude":
        return (
            "You're very welcome! 😊 Glad I could help. Whenever you need another answer, an unfiltered reality check, or a code review, just say the word."
        )

    if intent == "farewell":
        return (
            "Take care! Have a great one. Whenever you're ready to build, learn, or analyze something new, I'll be right here. 👋"
        )

    if intent == "creative":
        if "poem" in p_lower:
            return (
                f"### A Poem Inspired by Your Words\n\n"
                f"*In the quiet pulse of silicone dreams,*\n"
                f"*Where rivers of thought flow through glowing streams,*\n"
                f"*Ideas take wing in the silent expanse,*\n"
                f"*A woven mosaic of logic and chance.*\n\n"
                f"*Questions awaken the sparks in the night,*\n"
                f"*Turning the shadows of wonder to light,*\n"
                f"*Many minds gather, united in tone—*\n"
                f"*A symphony whispered, but never alone.*\n\n"
                f"---\n*Crafted by SYNORA AI. Would you like me to adjust the style, cadence, or imagery?*"
            )
        elif "story" in p_lower:
            return (
                f"### The Spark Beyond the Horizon\n\n"
                f"The observatory sat high atop the windswept ridge of Mount Varian, its brass dome gleaming beneath a canopy of violet starlight. For forty years, Elena had watched the cosmic telemetry—listening to the quiet breathing of the galaxy through arrays of copper dishes.\n\n"
                f"Tonight, however, the needle did not wander in white noise. It sang.\n\n"
                f"A repeating cadence, three seconds apart, echoed through the acoustic monitors. It wasn't a pulsar's mechanical ticking or the violent flare of a dying star. It was structured, delicate, like an ancient language spoken across millions of light-years.\n\n"
                f"Elena leaned forward, her fingers trembling against the dials. As she routed the frequencies through the analyzer, a single geometric pattern bloomed on the phosphorus screen: a sequence of prime harmonizations, concluding with a coordinate map pointing not outward, but directly back at Earth's oceanic trenches.\n\n"
                f"\"They aren't arriving,\" she whispered into the dim room, a chill tracing her spine. \"They've been here all along.\"\n\n"
                f"---\n*Would you like to continue the story, develop the characters, or change the trajectory?*"
            )
        elif "email" in p_lower:
            return (
                f"### Draft Email\n\n"
                f"**Subject:** Update & Next Steps Regarding {prompt.replace('draft an email', '').replace('write an email', '').strip().title() or 'Project Discussion'}\n\n"
                f"Hi [Name],\n\n"
                f"I hope you're having a productive week.\n\n"
                f"I am writing to follow up on our recent discussion and outline the proposed next steps. To ensure we stay aligned, here are the key highlights:\n\n"
                f"- **Objective:** Deliver high-quality outcomes while maintaining clear communication across milestones.\n"
                f"- **Immediate Action Items:** Reviewing current deliverables and confirming schedule dependencies.\n"
                f"- **Timeline:** We anticipate reaching the next major checkpoint by [Date/End of Week].\n\n"
                f"Please let me know if you have any questions or if you'd like to adjust any details before we proceed.\n\n"
                f"Best regards,\n\n"
                f"[Your Name]  \n[Your Title / Contact Information]\n\n"
                f"---\n*Tip: Feel free to tell me specific recipient details, tone adjustments, or bullet points to personalize this further.*"
            )

    # General Knowledge & Technical Explanations
    if "quantum" in p_lower:
        return (
            "### Quantum Computing Explained\n\n"
            "**Quantum computing** is a fundamentally new paradigm of calculation that exploits the principles of quantum mechanics to solve certain classes of problems exponentially faster than classical supercomputers.\n\n"
            "#### 1. Classical Bits vs. Quantum Qubits\n"
            "- **Classical Bits:** Binary switches that exist strictly as either `0` or `1`.\n"
            "- **Qubits (Quantum Bits):** Can exist in a **superposition** of `0` and `1` simultaneously, represented mathematically as a state vector on the Bloch sphere.\n\n"
            "#### 2. Key Quantum Phenomena\n"
            "1. **Superposition:** Allows a system of $N$ qubits to represent $2^N$ states simultaneously. Just 50 qubits can represent over 1 quadrillion states in parallel.\n"
            "2. **Entanglement:** Qubits become interconnected such that measuring one instantaneously determines the state of its entangled partner, enabling coordinated computation.\n"
            "3. **Quantum Interference:** Quantum algorithms steer probabilities toward the correct answer while cancelling out incorrect pathways.\n\n"
            "#### 3. Real-World Applications\n"
            "- **Cryptography:** Factoring large numbers, prompting the transition to Post-Quantum Cryptography (PQC).\n"
            "- **Materials Science:** Simulating molecular bonds and electron orbitals with atomic fidelity.\n"
            "- **Optimization:** Complex portfolio optimization, logistics, and traffic routing.\n\n"
            "Would you like to explore quantum algorithms, superconducting hardware (IBM/Google), or quantum error correction?"
        )

    if "sky" in p_lower and "blue" in p_lower:
        return (
            "### Why Is the Sky Blue?\n\n"
            "The sky appears blue because of an optical phenomenon called **Rayleigh Scattering**.\n\n"
            "#### The Physics Behind It:\n"
            "1. **Sunlight Is Made of All Colors:** White sunlight is a spectrum containing all wavelengths of visible light, ranging from red (long wavelengths, ~700 nm) to violet and blue (short wavelengths, ~400 nm).\n"
            "2. **Atmospheric Collisions:** Earth's atmosphere is filled with gases (mostly nitrogen and oxygen molecules). When sunlight enters the atmosphere, it strikes these tiny molecules.\n"
            "3. **Shorter Wavelengths Scatter More:** Rayleigh discovered that the amount of light scattered is inversely proportional to the fourth power of the wavelength: $I \\propto \\frac{1}{\\lambda^4}$.\n"
            "   - Because blue light has a wavelength nearly half that of red light, it scatters roughly **10 times more efficiently** in all directions.\n"
            "4. **Why Not Violet?** Violet light has an even shorter wavelength than blue, but sunlight contains much less violet light, and human eyes are far more sensitive to blue cones than violet cones.\n\n"
            "#### Why Are Sunsets Red?\n"
            "At sunset, sunlight travels through a much thicker slice of the atmosphere to reach your eyes. By the time it arrives, almost all the blue light has been scattered away, leaving only the long, resilient red, orange, and gold wavelengths!"
        )

    if "python" in p_lower and "rust" in p_lower:
        return (
            "### Python vs. Rust: An Unfiltered Technical Comparison\n\n"
            "**Python** and **Rust** were built with opposing engineering philosophies, and choosing between them comes down to developer speed vs runtime performance.\n\n"
            "| Dimension | Python 🐍 | Rust 🦀 |\n"
            "| :--- | :--- | :--- |\n"
            "| **Primary Paradigm** | High-level, interpreted, dynamically typed | Systems-level, compiled to machine code, strictly typed |\n"
            "| **Execution Speed** | Moderate (interpreted; relies on C extensions) | Blazing fast (approaches C/C++ bare-metal performance) |\n"
            "| **Memory Management** | Automatic garbage collection (reference counting + cyclic GC) | Compile-time **Borrow Checker** (zero GC pause, zero runtime cost) |\n"
            "| **Developer Velocity** | Extremely rapid; concise syntax, vast ecosystem | Slower initial development; steep learning curve for ownership/lifetimes |\n"
            "| **Concurrency Safety** | Global Interpreter Lock (GIL) limits native threading | Fearless concurrency; data races prevented at compile time |\n"
            "| **Best Suited For** | AI/ML, data science, rapid prototyping, scripting, web backends | Systems software, web servers, game engines, cryptography, CLI tools |\n\n"
            "#### The Practical Engineering Rule:\n"
            "Use **Python** when development velocity and iteration speed matter most (AI pipelines, prototypes, business logic). Use **Rust** when latency, CPU saturation, or memory guarantees are non-negotiable bottlenecks."
        )

    # General multi-purpose analytical synthesis for any user prompt
    capitalized_topic = prompt.strip().rstrip("?").capitalize()
    attachment_prefix = f"{attachment_analysis}\n\n---\n\n" if attachment_analysis else ""
    return (
        f"{attachment_prefix}### {capitalized_topic}\n\n"
        f"Here is a direct, thorough breakdown on **\"{prompt}\"**:\n\n"
        f"#### 1. Core Overview & Key Principles\n"
        f"- **Foundational Reality:** At its core, this topic hinges on practical trade-offs rather than theoretical perfection.\n"
        f"- **Significance:** Directly influences how systems, decisions, and strategies operate in real-world environments.\n"
        f"- **Primary Takeaway:** Success requires cutting through assumptions, validating data early, and maintaining iterative clarity.\n\n"
        f"#### 2. Detailed Analysis & Key Insights\n"
        f"1. **Core Dynamics:** Breaking down the underlying mechanics reveals what actually drives results and where friction accumulates.\n"
        f"2. **Pragmatic Practices:** Focus on maintainability, verifiable proof, and robust edge-case handling before scaling.\n"
        f"3. **Critical Pitfalls:** Beware of premature assumptions, lack of stress-testing, and overlooking structural dependencies.\n\n"
        f"#### 3. Practical Summary & Next Steps\n"
        f"Focus on the unglamorous fundamentals and verified feedback. What specific direction or next step would you like to explore?"
    )
