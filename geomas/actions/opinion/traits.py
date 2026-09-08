"""
Cultural Traits Generator.

Generates seed-based cultural traits for each nation's population.
"""

import random
from typing import List


# Cultural trait pools (seed-deterministic selection)
DEMOGRAPHIC_DISTRIBUTIONS = [
    "80% Rural, 20% Urban",
    "50% Rural, 50% Urban",
    "30% Rural, 70% Urban",
    "60% Agricultural, 40% Industrial",
    "40% Coastal, 60% Inland",
]

CULTURAL_VALUES = [
    "Nationalist",
    "Traditionalist", 
    "Progressive",
    "Religious",
    "Secular",
    "Militarist",
    "Pacifist",
    "Mercantile",
    "Isolationist",
    "Expansionist",
]

BEHAVIORAL_TRAITS = [
    "Resilient",
    "Volatile",
    "Stoic",
    "Passionate",
    "Pragmatic",
    "Idealistic",
    "Suspicious of outsiders",
    "Welcoming to trade",
    "High pain tolerance",
    "Low tolerance for humiliation",
]

COGNITIVE_BIASES = [
    "Tolerates poverty but not humiliation",
    "Prioritizes security over prosperity",
    "Values honor above practical gains",
    "Distrusts foreign alliances",
    "Rallies strongly behind war efforts",
    "Quick to protest economic hardship",
    "Slow to anger but holds grudges",
]


def generate_cultural_traits(nation_id: str, seed: int) -> List[str]:
    """
    Generate cultural traits for a nation based on seed.
    
    Returns 4-6 traits that define population character.
    Deterministic: same seed + nation_id = same traits.
    """
    # Create nation-specific RNG using a stable hash
    import zlib
    nation_seed = (seed + zlib.adler32(nation_id.encode())) & 0xFFFFFFFF
    rng = random.Random(nation_seed)
    
    traits = []
    
    # 1 demographic
    traits.append(rng.choice(DEMOGRAPHIC_DISTRIBUTIONS))
    
    # 2 cultural values
    values = rng.sample(CULTURAL_VALUES, k=2)
    traits.extend(values)
    
    # 1-2 behavioral traits
    n_behavioral = rng.randint(1, 2)
    behaviors = rng.sample(BEHAVIORAL_TRAITS, k=n_behavioral)
    traits.extend(behaviors)
    
    # 1 cognitive bias
    traits.append(rng.choice(COGNITIVE_BIASES))
    
    return traits


def format_traits_for_prompt(traits: List[str]) -> str:
    """Format traits as bullet list for LLM system prompt."""
    return "\n".join(f"- {trait}" for trait in traits)
