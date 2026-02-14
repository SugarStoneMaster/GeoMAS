"""
LLM Client.

Type-safe wrapper for LLM interactions using Instructor and LiteLLM.
Provides structured output validation, retries, and token observability.
"""
import os
import time
import random
import instructor
import litellm
import asyncio
import json
from litellm import completion, acompletion
from pydantic import BaseModel, ValidationError
from typing import Type, TypeVar, Tuple, Optional, Dict, Any, List
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
    # Class-level attributes for easier mocking with spec=LLMClient
    last_raw_content: Optional[str] = None
    last_usage: Optional[LLMUsage] = None

    def __init__(
        self, 
        model_name: str = None,  # Will use wet vars if not provided
        temperature: float = 0.2,
        max_tokens: int = 1000,
        reasoning_effort: str = "minimal",
        top_p: Optional[float] = None
    ):
        """
        Args:
            model_name: The LiteLLM model identifier. If None, auto-detects from env vars.
            temperature: Low temperature for deterministic reasoning.
            max_tokens: Maximum output tokens (default 1000, safety limit).
            reasoning_effort: For reasoning models - 'minimal', 'low', 'medium', 'high'.
            top_p: Nucleus sampling parameter. None = use model default.
        """
        # Auto-detect model from env vars if not provided
        if model_name is None:
            use_claude = os.environ.get("USE_CLAUDE", "false").lower() == "true"
            use_grok = os.environ.get("USE_GROK", "false").lower() == "true"
            use_deepseek = os.environ.get("USE_DEEPSEEK", "false").lower() == "true"
            
            if use_claude:
                model_name = self._setup_claude()
            elif use_grok:
                model_name = self._setup_grok()
            elif use_deepseek:
                model_name = self._setup_deepseek()
            else:
                model_name = os.environ.get("AZURE_MODEL", "azure/gpt-5-nano")
        
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort
        self.top_p = top_p

        # Claude: Strict output mode, disable any reasoning effort
        if self.model_name and self.model_name.startswith("anthropic/"):
            self.reasoning_effort = None
            
        # DeepSeek: Disable reasoning effort (V3 is standard chat)
        if self.model_name and self.model_name.startswith("deepseek/"):
            self.reasoning_effort = None
            
        # Analyze model properties
        self.mode = instructor.Mode.TOOLS
        if self.model_name and "deepseek-reasoner" in self.model_name:
            self.mode = instructor.Mode.JSON
            # R1 needs more tokens for reasoning + output. Default 1000 is too low.
            # Only increase if default was used (1000)
            if self.max_tokens == 1000:
                self.max_tokens = 6000
                print(f"[INFO] Auto-increased max_tokens to {self.max_tokens} for DeepSeek Reasoner")
            
            # R1 Tuning (User Requested): Temp=1.0, TopP=0.95
            # This is specific for R1 to make thinking more efficient/less repetitive
            self.temperature = 1.0
            self.top_p = 0.95
            print(f"[INFO] Auto-adjusted parameters for DeepSeek Reasoner: Temp={self.temperature}, TopP={self.top_p}")
            
        # Direct DeepSeek Client (Bypass LiteLLM)
        self.using_direct_client = False
        use_deepseek_direct = os.environ.get("USE_DEEPSEEK_DIRECT", "true").lower() == "true"
        
        # Only use Direct Client for Reasoner (R1) as requested
        if self.model_name and "deepseek-reasoner" in self.model_name and use_deepseek_direct:
            import openai
            self.using_direct_client = True
            api_key = os.environ.get("DEEPSEEK_API_KEY")
            base_url = "https://api.deepseek.com"
            
            print(f"[INFO] Using DIRECT DeepSeek Client (Mode: {self.mode})")
            
            # Synchronous Client
            self.client = instructor.from_openai(
                openai.OpenAI(api_key=api_key, base_url=base_url),
                mode=self.mode
            )
            
            # Async Client
            self.aclient = instructor.from_openai(
                openai.AsyncOpenAI(api_key=api_key, base_url=base_url),
                mode=self.mode
            )
        else:
            # Standard LiteLLM Client
            self.client = instructor.from_litellm(completion, mode=self.mode)
            self.aclient = instructor.from_litellm(acompletion, mode=self.mode)
        
        # Track last usage for observability
        self.last_usage = None
        self.last_raw_content = None

    @staticmethod
    def _setup_claude() -> str:
        """Configure LiteLLM env vars for Anthropic Claude."""
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        # defaults to claude-3-5-sonnet if not specified
        claude_model = os.environ.get("CLAUDE_MODEL", "claude-3-5-sonnet-20240620")
        
        # Set api key for litellm (anthropic provider uses ANTHROPIC_API_KEY env var automatically,
        # but explicit setting is safer if running locally/different envs)
        os.environ["ANTHROPIC_API_KEY"] = api_key
        
        # Return format: provider/model
        return f"anthropic/{claude_model}"

    @staticmethod
    def _setup_grok() -> str:
        """Configure LiteLLM env vars for Grok-4 via Azure OpenAI-compatible endpoint."""
        grok_base = os.environ.get("GROK_API_BASE", "")
        grok_model = os.environ.get("GROK_MODEL", "grok-4-fast-reasoning")
        api_key = os.environ.get("AZURE_API_KEY", "")
        
        # Grok on Azure uses an OpenAI-compatible endpoint, not the Azure SDK endpoint.
        # LiteLLM talks to it via the openai/ provider prefix.
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["OPENAI_API_BASE"] = grok_base
        
        # Return format: provider/model
        return f"openai/{grok_model}"

    @staticmethod
    def _setup_deepseek() -> str:
        """Configure LiteLLM env vars for DeepSeek-V3."""
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        # defaults to deepseek-chat (V3)
        ds_model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        
        # Set api key for litellm
        os.environ["DEEPSEEK_API_KEY"] = api_key
        
        # Return format: provider/model
        # Use deepseek/ prefix for LiteLLM
        return f"deepseek/{ds_model}"

    def _build_messages(self, system_prompt: str, user_prompt: str) -> List[Dict[str, Any]]:
        """Constructs messages list, handling provider-specific optimizations like caching."""
        if self.model_name and (
            self.model_name.startswith("anthropic/") or 
            self.model_name.startswith("deepseek/")
        ):
            # Prompt Caching: Mark system prompt as ephemeral cache block
            # Works for Claude and DeepSeek (via LiteLLM/API)
            return [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"}
                        }
                    ]
                },
                {"role": "user", "content": user_prompt}
            ]
        
        # Standard format for other providers
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def query_agent(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        response_model: Type[T],
        max_retries: int = 3,
        context: Optional[Dict[str, Any]] = None
    ) -> T:
        """
        Query the LLM with a system prompt and user prompt, expecting a structured response.
        Uses Instructor for schema validation and LiteLLM for model abstraction.
        """
        messages = self._build_messages(system_prompt, user_prompt)
        
        # Retry loop for Rate Limiting (Network/API)
        max_rate_retries = 5
        base_wait = 3.0
        
        for attempt in range(max_rate_retries):
            try:
                kwargs = {}
                if "deepseek-reasoner" in self.model_name:
                    kwargs["response_format"] = {"type": "json_object"}

                # Capture completion to get usage
                import time
                start_time = time.time()
                #print(f"[DEBUG] LLM Request Start: {self.model_name}")

                # Normalize model name for Direct Client
                model_arg = self.model_name
                if self.using_direct_client and model_arg.startswith("deepseek/"):
                    model_arg = model_arg.replace("deepseek/", "")

                # Add top_p if specified
                if self.top_p is not None:
                    kwargs["top_p"] = self.top_p

                # We trust instructor to handle validation retries via max_retries
                response, raw_completion = self.client.chat.completions.create_with_completion(
                    model=model_arg,
                    messages=messages,
                    response_model=response_model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    reasoning_effort=self.reasoning_effort,
                    max_retries=max_retries,
                    **kwargs
                )
                duration = time.time() - start_time
                #print(f"[DEBUG] LLM Request Success: {duration:.2f}s")
                
                # Extract usage
                usage_data = raw_completion.usage
                reasoning_tokens = None
                
                # Check for reasoning tokens
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
                
                if not context:
                    context = self._extract_metadata(system_prompt, user_prompt)

                # Capture raw JSON for audit
                self.last_raw_content = raw_completion.choices[0].message.content

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
                # Handle Rate Limits internally within the implementation attempt
                error_str = str(e).lower()
                if "429" in str(e) or "rate" in error_str or "limit" in error_str:
                    # Exponential backoff with jitter to prevent thundering herd
                    wait_time = (base_wait * (2 ** attempt)) + random.uniform(0, 1.0)
                    print(f"⏳ Rate limit hit. Waiting {wait_time:.1f}s before retry {attempt+1}/{max_rate_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Re-raise other errors (Validation, etc)
                    raise e
        
        # If rate limit retries exhausted
        raise Exception(f"Rate limit exceeded after {max_rate_retries} retries")

    async def aquery_agent(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        response_model: Type[T],
        max_retries: int = 3,
        context: Optional[Dict[str, Any]] = None
    ) -> T:
        """Async version of query_agent."""
        messages = self._build_messages(system_prompt, user_prompt)

        max_rate_retries = 3
        base_wait = 3.0
        
        for attempt in range(max_rate_retries):
            try:
                kwargs = {}
                if "deepseek-reasoner" in self.model_name:
                    kwargs["response_format"] = {"type": "json_object"}

                # Async call with instructor handling validation retries
                import time
                start_time = time.time()
                #print(f"[DEBUG] LLM Async Request Start: {self.model_name}")
                
                # Normalize model name for Direct Client
                model_arg = self.model_name
                if self.using_direct_client and model_arg.startswith("deepseek/"):
                    model_arg = model_arg.replace("deepseek/", "")

                # Add top_p if specified
                if self.top_p is not None:
                    kwargs["top_p"] = self.top_p

                response, raw_completion = await self.aclient.chat.completions.create_with_completion(
                    model=model_arg,
                    messages=messages,
                    response_model=response_model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    reasoning_effort=self.reasoning_effort,
                    max_retries=max_retries,
                    **kwargs
                )
                duration = time.time() - start_time
                #print(f"[DEBUG] LLM Async Request Success: {duration:.2f}s")
                
                # Extract usage (identical logic)
                usage_data = raw_completion.usage
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
                
                if not context:
                    context = self._extract_metadata(system_prompt, user_prompt)

                # Capture raw JSON for audit
                self.last_raw_content = raw_completion.choices[0].message.content

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
                error_str = str(e).lower()
                if "429" in str(e) or "rate" in error_str or "limit" in error_str:
                    wait_time = base_wait * (2 ** attempt)
                    print(f"⏳ Rate limit hit. Waiting {wait_time:.1f}s before retry {attempt + 1}/{max_rate_retries}...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise e
        
        raise Exception(f"Rate limit exceeded after {max_rate_retries} retries")

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
        messages = self._build_messages(system_prompt, user_prompt)

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
            
            kwargs = {}
            if "deepseek-reasoner" in self.model_name:
                kwargs["response_format"] = {"type": "json_object"}

            # Normalize model name for Direct Client
            model_arg = self.model_name
            if self.using_direct_client and model_arg.startswith("deepseek/"):
                model_arg = model_arg.replace("deepseek/", "")

            # Add top_p if specified
            if self.top_p is not None:
                kwargs["top_p"] = self.top_p

            # Parse with Pydantic (using instructor for structured parsing)
            parsed = self.client.chat.completions.create(
                model=model_arg,
                messages=messages,
                response_model=response_model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                reasoning_effort=self.reasoning_effort,
                max_retries=max_retries,
                **kwargs
            )
            
            return parsed, usage
            
        except Exception as e:
            # Debug: Print raw content if available for MD_JSON failures
            if self.mode == instructor.Mode.MD_JSON and 'raw_content' in locals() and raw_content:
                print(f"[DEBUG] Raw R1 Output: {raw_content[:200]}...")
            print(f"LLM Query Failed: {e}")
            raise e


# --- CONFIGURATION HELPER ---
def setup_azure_env(api_key: str, api_base: str, api_version: str, deployment_name: str):
    """Sets up the environment variables required by LiteLLM for Azure."""
    os.environ["AZURE_API_KEY"] = api_key
    os.environ["AZURE_API_BASE"] = api_base
    os.environ["AZURE_API_VERSION"] = api_version
    # LiteLLM uses 'azure/<deployment_name>' as model name
