"""
Population Opinion LLM Agent.

TODO: Implement the Population Opinion Agent that modulates satisfaction multipliers.

This agent represents the "Voice of the People" and influences how the population
reacts to government decisions and world events.

SYSTEM PROMPT REQUIREMENTS:
--------------------------
The agent should receive:
1. Demographics (seed-generated):
   - Urban/Rural distribution
   - Age distribution
   - Economic sectors

2. Cultural Traits (from traits.py):
   - Generated deterministically from seed + nation_id
   - Example: ["Nationalist", "Religious", "High pain tolerance"]

3. Government Actions this turn:
   - Economic decisions (INVEST_WELFARE, RAISE_WAR_TAX)
   - Military decisions (wars declared, battles fought)
   - Diplomatic decisions (alliances, treaties)

4. World Events affecting this nation:
   - Resource surplus/deficit
   - War casualties
   - Territory gains/losses

OUTPUT:
-------
The agent returns two multipliers (0.1 to 2.0):
- multiplier_increase: How much to amplify POSITIVE satisfaction changes
- multiplier_decrease: How much to amplify NEGATIVE satisfaction changes

EXAMPLES:
---------
- A nationalist population might have high multiplier_decrease when humiliated
- A resilient population might have low multiplier_decrease during hardship
- A war-weary population might have low multiplier_increase for victories

PROMPT TEMPLATE (EXAMPLE):
--------------------------
SYSTEM: Sei la "Voce del Popolo" della Nazione di {nation_name}.

DEMOGRAPHICS:
{demographics}

CULTURAL TRAITS:
{cultural_traits}

EVENTS THIS TURN:
{events}

GOVERNMENT ACTIONS:
{actions}

Rispondi SOLO con JSON:
{
    "multiplier_increase": <float 0.1-2.0>,
    "multiplier_decrease": <float 0.1-2.0>,
    "reasoning": "<brief explanation>"
}
"""

from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from geomas.schemas.world import NationState, WorldState


# TODO: Implement this function
def get_population_opinion_prompt(
    nation: 'NationState',
    world: 'WorldState',
    events: list[str],
    actions: list[str],
) -> str:
    """
    Generate the system prompt for the Population Opinion agent.
    
    TODO: Implement this to create a prompt based on:
    - nation.cultural_traits (seed-generated)
    - nation demographics
    - events affecting the nation
    - government actions this turn
    """
    raise NotImplementedError("Population Opinion Agent not yet implemented")


# TODO: Implement this function
def parse_population_response(response: str) -> Dict[str, Any]:
    """
    Parse the LLM response to extract multipliers.
    
    TODO: Implement JSON parsing with validation:
    - multiplier_increase: clamp to 0.1-2.0
    - multiplier_decrease: clamp to 0.1-2.0
    - reasoning: optional string
    """
    raise NotImplementedError("Population Opinion Agent not yet implemented")
