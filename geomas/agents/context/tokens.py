"""
Token Counter.

Provides accurate token counting using tiktoken for GPT models.
Used to validate that prompts stay within budget limits.
"""

from typing import Optional
import tiktoken


class TokenCounter:
    """
    Counts tokens using OpenAI's tiktoken library.
    
    Uses cl100k_base encoding (GPT-4, GPT-3.5-turbo) for accurate counting.
    Falls back to character-based approximation if tiktoken fails.
    """
    
    # Default token budgets
    DEFAULT_SYSTEM_BUDGET = 800
    DEFAULT_INPUT_BUDGET = 4200
    DEFAULT_TOTAL_BUDGET = 5000
    
    def __init__(self, model: str = "gpt-4"):
        """
        Initialize the token counter.
        
        Args:
            model: Model name for encoding selection
        """
        self.model = model
        try:
            # cl100k_base is used by GPT-4 and GPT-3.5-turbo
            self.encoding = tiktoken.get_encoding("cl100k_base")
            self._use_tiktoken = True
        except Exception:
            # Fallback to approximation
            self._use_tiktoken = False
    
    def count(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        if not text:
            return 0
        
        if self._use_tiktoken:
            return len(self.encoding.encode(text))
        else:
            # Approximation: ~4 characters per token for English text
            return len(text) // 4
    
    def count_messages(self, messages: list[dict]) -> int:
        """
        Count tokens for a list of chat messages.
        
        Args:
            messages: List of {"role": "...", "content": "..."} dicts
            
        Returns:
            Total tokens including message formatting overhead
        """
        total = 0
        for message in messages:
            # Each message has ~4 token overhead for formatting
            total += 4
            total += self.count(message.get("role", ""))
            total += self.count(message.get("content", ""))
        # Final message separator
        total += 2
        return total
    
    def validate_budget(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = DEFAULT_TOTAL_BUDGET
    ) -> tuple[bool, dict]:
        """
        Validate that prompts fit within token budget.
        
        Args:
            system_prompt: System prompt text
            user_prompt: User/input prompt text
            max_tokens: Maximum allowed tokens
            
        Returns:
            Tuple of (is_valid, details_dict)
        """
        system_tokens = self.count(system_prompt)
        user_tokens = self.count(user_prompt)
        total_tokens = system_tokens + user_tokens
        
        # Add message overhead (~10 tokens)
        total_with_overhead = total_tokens + 10
        
        is_valid = total_with_overhead <= max_tokens
        
        details = {
            "system_tokens": system_tokens,
            "user_tokens": user_tokens,
            "total_tokens": total_tokens,
            "total_with_overhead": total_with_overhead,
            "max_tokens": max_tokens,
            "is_valid": is_valid,
            "tokens_remaining": max_tokens - total_with_overhead,
            "utilization_percent": (total_with_overhead / max_tokens) * 100
        }
        
        return is_valid, details
    
    def estimate_response_budget(
        self,
        system_prompt: str,
        user_prompt: str,
        context_window: int = 8192
    ) -> int:
        """
        Estimate available tokens for response.
        
        Args:
            system_prompt: System prompt text
            user_prompt: User/input prompt text
            context_window: Model's context window size
            
        Returns:
            Tokens available for response
        """
        _, details = self.validate_budget(system_prompt, user_prompt, context_window)
        return max(0, details["tokens_remaining"])
    
    def get_breakdown(self, text: str, sections: Optional[list[str]] = None) -> dict:
        """
        Get token breakdown by sections.
        
        Args:
            text: Full text to analyze
            sections: Optional section markers to split on (e.g., ["==", "##"])
            
        Returns:
            Dict with section names and their token counts
        """
        if sections is None:
            sections = ["==", "##"]
        
        result = {"total": self.count(text)}
        
        # Simple section detection
        lines = text.split("\n")
        current_section = "header"
        current_content = []
        
        for line in lines:
            is_section = any(marker in line for marker in sections)
            if is_section and current_content:
                result[current_section] = self.count("\n".join(current_content))
                current_section = line.strip()[:50]  # Truncate long headers
                current_content = []
            else:
                current_content.append(line)
        
        if current_content:
            result[current_section] = self.count("\n".join(current_content))
        
        return result


# Singleton instance for convenience
_default_counter: Optional[TokenCounter] = None


def get_token_counter() -> TokenCounter:
    """Get the default token counter instance."""
    global _default_counter
    if _default_counter is None:
        _default_counter = TokenCounter()
    return _default_counter


def count_tokens(text: str) -> int:
    """Convenience function to count tokens."""
    return get_token_counter().count(text)


def validate_prompt_budget(system: str, user: str, max_tokens: int = 5000) -> tuple[bool, dict]:
    """Convenience function to validate prompts."""
    return get_token_counter().validate_budget(system, user, max_tokens)
