"""
LLM Client.

Type-safe wrapper for LLM interactions using Instructor and LiteLLM.
Provides structured output validation, retries, and token observability.
"""
import os
import instructor
import litellm
from litellm import completion
from pydantic import BaseModel
from typing import Type, TypeVar, Tuple, Optional, Dict, Any
from dataclasses import dataclass

from geomas.analysis.token_logger import token_logger

# Drop unsupported params for models like GPT-5 that don't support temperature
litellm.drop_params = True

T = TypeVar("T", bound=BaseModel)


@dataclass
class LLMUsage:
    """Token usage statistics from an LLM call."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    reasoning_tokens: Optional[int] = None  # For models with chain-of-thought
    
    def __str__(self) -> str:
        base = f"📊 Tokens: {self.prompt_tokens} in → {self.completion_tokens} out = {self.total_tokens} total"
        if self.reasoning_tokens:
            base += f" (reasoning: {self.reasoning_tokens})"
        return base


@dataclass
class LLMResponse:
    """Response from LLM including parsed model and usage stats."""
    data: BaseModel  # The parsed Pydantic model
    usage: LLMUsage
    raw_content: Optional[str] = None  # Raw text before parsing (if available)


class LLMClient:
    """
    A robust, type-safe wrapper for LLM interactions using Instructor and LiteLLM.
    Handles structured output validation, retries, and provides token observability.
    """

    def __init__(
        self, 
        model_name: str = None,  # Will use AZURE_MODEL env var if not provided
        temperature: float = 0.2,
        max_tokens: int = 1000,
        reasoning_effort: str = "minimal"
    ):
        """
        Args:
            model_name: The LiteLLM model identifier. If None, uses AZURE_MODEL env var.
            temperature: Low temperature for deterministic reasoning.
            max_tokens: Maximum output tokens (default 1000, safety limit).
            reasoning_effort: For reasoning models - 'minimal', 'low', 'medium', 'high'.
        """
        # Use env var if model_name not provided
        if model_name is None:
            model_name = os.environ.get("AZURE_MODEL", "azure/gpt-5-nano")
        
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort
        self.client = instructor.from_litellm(completion)
        
        # Track last usage for observability
        self.last_usage: Optional[LLMUsage] = None

    def query_agent(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        response_model: Type[T],
        max_retries: int = 3,
        context: Optional[Dict[str, Any]] = None
    ) -> T:
        """
        Queries the LLM and forces a structured Pydantic response.
        Now automatically extracts metadata (Turn, Nation, Role) from prompts.

        Args:
            system_prompt: The persona and rules.
            user_prompt: The context and task.
            response_model: The Pydantic class to validate against.
            max_retries: How many times to retry on validation error.

        Returns:
            An instance of response_model.

        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            # Capture completion to get usage
            response, raw_completion = self.client.chat.completions.create_with_completion(
                model=self.model_name,
                messages=messages,
                response_model=response_model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                reasoning_effort=self.reasoning_effort,
                max_retries=max_retries,
            )
            
            # Extract usage
            usage_data = raw_completion.usage
            reasoning_tokens = None
            
            # Check for reasoning tokens in various possible locations (LiteLLM/OpenAI standard)
            if hasattr(usage_data, 'completion_tokens_details') and usage_data.completion_tokens_details:
                details = usage_data.completion_tokens_details
                if hasattr(details, 'reasoning_tokens'):
                    reasoning_tokens = details.reasoning_tokens
                elif isinstance(details, dict):
                    reasoning_tokens = details.get('reasoning_tokens')
            
            # Fallback: check top-level if present (some versions/models)
            if reasoning_tokens is None and hasattr(usage_data, 'reasoning_tokens'):
                reasoning_tokens = usage_data.reasoning_tokens
            
            usage = LLMUsage(
                prompt_tokens=usage_data.prompt_tokens,
                completion_tokens=usage_data.completion_tokens,
                total_tokens=usage_data.total_tokens,
                reasoning_tokens=reasoning_tokens
            )
            self.last_usage = usage
            
            # AUTO-EXTRACT METADATA for logging if context not provided
            if not context:
                context = self._extract_metadata(system_prompt, user_prompt)

            # Log usage
            token_logger.log(
                turn=context.get("turn", 0),
                nation_id=context.get("nation_id", "unknown"),
                role=context.get("role", "unknown"),
                model=self.model_name,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                reasoning_tokens=usage.reasoning_tokens
            )

            return response
            
        except Exception as e:
            # Token usage might not be available on error, but we should handle it
            raise e

    def _extract_metadata(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Automatically extract metadata from prompts using regex."""
        import re
        meta = {"turn": 0, "nation_id": "unknown", "role": "unknown"}
        
        # 1. Turn: ## TURN (\d+)
        turn_match = re.search(r"## TURN (\d+)", user_prompt)
        if turn_match:
            meta["turn"] = int(turn_match.group(1))
            
        # 2. Role & Nation: You are the **(Role) of (Nation)**
        # Matches "Defense Minister of VALKYR" or "voice of the people of VALKYR"
        match = re.search(r"You are the \*\*(?P<role>.*?) of (?P<nation>.*?)\*\*", system_prompt)
        if match:
            meta["role"] = match.group("role")
            meta["nation_id"] = match.group("nation")
        else:
            # Fallback for individual matches
            role_match = re.search(r"You are the \*\*(.*?)\*\*", system_prompt)
            if role_match:
                meta["role"] = role_match.group(1)
            
            nation_match = re.search(r"of \*\*(.*?)\*\*", system_prompt)
            if nation_match:
                meta["nation_id"] = nation_match.group(1)
            
        return meta

    def query_agent_with_usage(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        response_model: Type[T],
        max_retries: int = 3
    ) -> Tuple[T, LLMUsage]:
        """
        Queries the LLM and returns both parsed response AND token usage.
        
        Args:
            system_prompt: The persona and rules.
            user_prompt: The context and task.
            response_model: The Pydantic class to validate against.
            max_retries: How many times to retry on validation error.
            
        Returns:
            Tuple of (parsed_response, usage_stats)
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            # Use raw litellm.completion to get full response with usage
            raw_response = completion(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                reasoning_effort=self.reasoning_effort,
            )
            
            # Extract usage
            usage_data = raw_response.usage
            reasoning_tokens = None
            
            if hasattr(usage_data, 'completion_tokens_details') and usage_data.completion_tokens_details:
                details = usage_data.completion_tokens_details
                if hasattr(details, 'reasoning_tokens'):
                    reasoning_tokens = details.reasoning_tokens
                elif isinstance(details, dict):
                    reasoning_tokens = details.get('reasoning_tokens')
            
            if reasoning_tokens is None and hasattr(usage_data, 'reasoning_tokens'):
                reasoning_tokens = usage_data.reasoning_tokens
            
            usage = LLMUsage(
                prompt_tokens=usage_data.prompt_tokens,
                completion_tokens=usage_data.completion_tokens,
                total_tokens=usage_data.total_tokens,
                reasoning_tokens=reasoning_tokens
            )
            self.last_usage = usage
            
            # Extract raw content
            raw_content = raw_response.choices[0].message.content
            
            # Parse with Pydantic (using instructor for structured parsing)
            parsed = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_model=response_model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                reasoning_effort=self.reasoning_effort,
                max_retries=max_retries,
            )
            
            return parsed, usage
            
        except Exception as e:
            print(f"LLM Query Failed: {e}")
            raise e


# --- CONFIGURATION HELPER ---
def setup_azure_env(api_key: str, api_base: str, api_version: str, deployment_name: str):
    """Sets up the environment variables required by LiteLLM for Azure."""
    os.environ["AZURE_API_KEY"] = api_key
    os.environ["AZURE_API_BASE"] = api_base
    os.environ["AZURE_API_VERSION"] = api_version
    # LiteLLM uses 'azure/<deployment_name>' as model name
