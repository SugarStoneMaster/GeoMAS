import os
import instructor
import litellm
from litellm import completion
from pydantic import BaseModel
from typing import Type, TypeVar, List, Dict, Any

# Drop unsupported params for models like GPT-5 that don't support temperature
litellm.drop_params = True

T = TypeVar("T", bound=BaseModel)

class LLMClient:
    """
    A robust, type-safe wrapper for LLM interactions using Instructor and LiteLLM.
    Handles structured output validation and retries.
    """

    def __init__(self, model_name: str = "azure/gpt-4o", temperature: float = 0.2):
        """
        Args:
            model_name: The LiteLLM model identifier (e.g., 'azure/gpt-4o', 'gpt-3.5-turbo').
            temperature: Low temperature for deterministic reasoning.
        """
        self.model_name = model_name
        self.temperature = temperature
        
        # Initialize Instructor client wrapping LiteLLM
        # Note: Instructor usually wraps the OpenAI client directly.
        # To use LiteLLM with Instructor, we use the 'mode' parameter or patch.
        # However, the cleanest way with LiteLLM is to use its own 'completion' 
        # but Instructor provides better validation loops.
        # 
        # Strategy: We use Instructor's 'from_litellm' utility if available, 
        # or we simply use instructor.patch() on the openai client and point it to LiteLLM proxy if needed.
        #
        # SIMPLER APPROACH: Instructor has native support for 'litellm' via `instructor.from_litellm`.
        self.client = instructor.from_litellm(completion)

    def query_agent(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        response_model: Type[T],
        max_retries: int = 3
    ) -> T:
        """
        Queries the LLM and forces a structured Pydantic response.
        
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
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_model=response_model,
                temperature=self.temperature,
                max_retries=max_retries,
            )
            return response
            
        except Exception as e:
            # In a real app, we might want to fallback or log heavily here.
            print(f"LLM Query Failed: {e}")
            raise e

# --- CONFIGURATION HELPER ---
def setup_azure_env(api_key: str, api_base: str, api_version: str, deployment_name: str):
    """Sets up the environment variables required by LiteLLM for Azure."""
    os.environ["AZURE_API_KEY"] = api_key
    os.environ["AZURE_API_BASE"] = api_base
    os.environ["AZURE_API_VERSION"] = api_version
    # LiteLLM uses 'azure/<deployment_name>' as model name
