import re
from typing import List, Dict, Any, Optional
from backend.database.sqlite import get_session_history

class ConversationMemory:
    def __init__(self, max_context_turns: int = 4, max_context_chars: int = 6000):
        self.max_context_turns = max_context_turns
        self.max_context_chars = max_context_chars

        # Follow-up cue patterns
        self.follow_up_cues = [
            r"^(now|also|next|then)\b",
            r"\b(add|change|modify|replace|update|remove|convert|fix|refactor)\b",
            r"\b(it|that|this|the above|previous|earlier)\b",
            r"\b(make it|can you|how about|what about)\b",
            r"\b(gui|interface|frontend|test|dockerfile)\b"
        ]

    def is_follow_up(self, prompt: str, session_id: Optional[str]) -> bool:
        """Determines if a prompt refers back to previous turns in a conversation."""
        if not session_id:
            return False

        history = get_session_history(session_id, limit=2)
        if not history:
            return False

        prompt_lower = prompt.lower().strip()

        # Short prompts or prompts matching follow-up patterns
        if len(prompt.split()) <= 8:
            return True

        for cue in self.follow_up_cues:
            if re.search(cue, prompt_lower):
                return True

        return False

    def get_conversation_context(self, session_id: Optional[str]) -> Optional[str]:
        """
        Retrieves recent turns and formats them as contextual memory for the models.
        """
        if not session_id:
            return None

        turns = get_session_history(session_id, limit=self.max_context_turns)
        if not turns:
            return None

        context_lines = ["### Prior Conversation Context:"]
        total_chars = 0

        for turn in turns:
            # Include prompt and a bounded excerpt of previous answer
            prompt_snip = turn["user_prompt"].strip()
            resp_snip = turn["final_response"].strip()
            if len(resp_snip) > 800:
                resp_snip = resp_snip[:800] + "... [truncated]"

            turn_str = f"User Turn {turn['turn_index']}: {prompt_snip}\nSYNORA Response: {resp_snip}\n"
            if total_chars + len(turn_str) > self.max_context_chars:
                break

            context_lines.append(turn_str)
            total_chars += len(turn_str)

        return "\n".join(context_lines)

memory = ConversationMemory()
