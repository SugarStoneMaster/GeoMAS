"""
Token usage observability logger.
"""
import csv
import os
import time
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TokenUsageEntry(BaseModel):
    """A single record of LLM token usage."""
    timestamp: float = Field(default_factory=time.time)
    turn: int
    nation_id: str
    role: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    reasoning_tokens: Optional[int] = None

class TokenLogger:
    """
    Accumulates token usage data in memory and flushes to CSV.
    """
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.entries: List[TokenUsageEntry] = []
        
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def log(
        self, 
        turn: int, 
        nation_id: str, 
        role: str, 
        model: str, 
        input_tokens: int, 
        output_tokens: int, 
        total_tokens: int,
        reasoning_tokens: Optional[int] = None
    ):
        """Append an entry to the in-memory log."""
        entry = TokenUsageEntry(
            turn=turn,
            nation_id=nation_id,
            role=role,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            reasoning_tokens=reasoning_tokens
        )
        self.entries.append(entry)

    def save_to_csv(self, filename: str = "token_usage.csv"):
        """Save all accumulated entries to a CSV file."""
        if not self.entries:
            return

        filepath = os.path.join(self.log_dir, filename)
        file_exists = os.path.isfile(filepath)

        fieldnames = [
            "timestamp", "turn", "nation_id", "role", "model", 
            "input_tokens", "output_tokens", "total_tokens", "reasoning_tokens"
        ]

        try:
            with open(filepath, mode='a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                
                for entry in self.entries:
                    writer.writerow(entry.model_dump())
            
            # Clear entries after successful save to avoid duplicates
            self.entries = []
            print(f"✅ Token usage saved to {filepath}")
        except Exception as e:
            print(f"❌ Failed to save token usage: {e}")

# Global singleton-like instance for easy access
token_logger = TokenLogger()
