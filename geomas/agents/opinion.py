"""
Population Opinion LLM Agent.

Represents the "Voice of the People" and influences how the population
reacts to government decisions and world events.

The agent runs POST-EXECUTION and returns multipliers that modulate
how strongly the population reacts to positive/negative events.
"""

from typing import TYPE_CHECKING, Dict, Any, Optional, List
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from geomas.agents.llm_client import LLMClient
    from geomas.schemas.world import NationState, WorldState


from geomas.agents.context.system.opinion import OpinionSystemPrompt
from geomas.agents.context.input.opinion import OpinionInputBuilder


class OpinionResponse(BaseModel):
    """Structured response from the Opinion agent."""
    multiplier_increase: float = Field(
        default=1.0,
        ge=0.1,
        le=2.0,
        description="Multiplier for positive satisfaction changes (0.1-2.0)"
    )
    multiplier_decrease: float = Field(
        default=1.0,
        ge=0.1,
        le=2.0,
        description="Multiplier for negative satisfaction changes (0.1-2.0)"
    )
    mood: str = Field(
        default="NEUTRAL",
        description="Current population mood"
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of the population's reaction"
    )
    last_system_prompt: Optional[str] = Field(None, exclude=True)
    last_input_prompt: Optional[str] = Field(None, exclude=True)
    raw_json: Optional[str] = Field(None, exclude=True)


class OpinionAgent:
    """
    Agent that represents the population's reaction to events and actions.
    
    Runs after government actions are executed and modulates satisfaction changes
    based on cultural traits and current events.
    """
    
    def __init__(
        self,
        nation_id: str,
        nation_name: str,
        cultural_traits: List[str],
        llm_client: Optional['LLMClient'] = None,
        world: Optional['WorldState'] = None,
        government_type = None
    ):
        self.nation_id = nation_id
        self.nation_name = nation_name
        self.cultural_traits = cultural_traits
        self.llm_client = llm_client
        self.world = world
        self.government_type = government_type
        
        # Traces for analysis
        self.last_system_prompt: Optional[str] = None
        self.last_input_prompt: Optional[str] = None
        self.last_response: Optional[OpinionResponse] = None
        self.trace_history: dict = {} # turn -> trace
        # Eager Initialization
        self.system_prompt = OpinionSystemPrompt.generate(
            nation_name, cultural_traits, government_type=government_type
        )
    
    def react(
        self,
        events: List[str],
        government_actions: List[str],
        current_satisfaction: float,
        at_war: bool,
        turn: int = 1
    ) -> OpinionResponse:
        """
        Generate population reaction to recent events and government actions.
        
        Args:
            events: World events affecting this nation
            government_actions: Actions taken by the government this turn
            current_satisfaction: Current satisfaction level (0-100)
            at_war: Whether the nation is currently at war
            turn: Current turn number
            
        Returns:
            OpinionResponse with multipliers
        """
        if not self.llm_client:
            # Fallback: deterministic reaction based on traits
            response = self._deterministic_reaction(
                events, government_actions, current_satisfaction, at_war
            )
            # Minimal trace for fallback
            self.trace_history[turn] = {
                "system_prompt": "Deterministic Fallback",
                "user_prompt": f"Satisfaction: {current_satisfaction}%",
                "proposal": response
            }
            return response
        
        # Build prompt using new architecture if world is available
        if self.world:
            system_prompt = self.system_prompt
            input_builder = OpinionInputBuilder(self.world)
            input_prompt = input_builder.build(
                nation_id=self.nation_id,
                turn=turn,
                recent_events=events,
                government_actions=government_actions
            )
        else:
            # Fallback to internal builders
            system_prompt = self._build_system_prompt()
            input_prompt = self._build_input_prompt(
                events, government_actions, current_satisfaction, at_war, turn
            )
        
        # Query LLM
        response = self.llm_client.query_agent(
            system_prompt=system_prompt,
            user_prompt=input_prompt,
            response_model=OpinionResponse
        )
        
        # Capture prompts in agent AND response for persistence
        self.last_system_prompt = system_prompt
        self.last_input_prompt = input_prompt
        self.last_response = response  # Store for SimulationEngine
        response.last_system_prompt = system_prompt
        response.last_input_prompt = input_prompt
        response.raw_json = self.llm_client.last_raw_content
        
        # Save to trace history for Dashboard Inspector
        self.trace_history[turn] = {
            "system_prompt": system_prompt,
            "user_prompt": input_prompt,
            "proposal": response
        }
        
        return response
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the Opinion agent (Fallback)."""
        traits_text = ", ".join(self.cultural_traits) if self.cultural_traits else "Balanced outlook"
        
        return f"""You are the **Public Opinion of {self.nation_name}**.

## Cultural Traits
Your population is characterized by: **{traits_text}**

These traits influence how strongly you react:
- Some cultures value military glory, others prefer peace
- Some prioritize economic prosperity, others value traditions
- Some trust their government, others are skeptical

## Your Role
You react to recent events and government decisions.
You do NOT make decisions - you reflect public sentiment.

## Output
Return two multipliers (0.1 to 2.0):
- **multiplier_increase**: How to amplify POSITIVE changes to satisfaction
- **multiplier_decrease**: How to amplify NEGATIVE changes to satisfaction

Examples:
- Nationalist population humiliated by defeat: multiplier_decrease = 1.8
- Resilient population during hardship: multiplier_decrease = 0.5
- War-weary population after long war: multiplier_increase = 0.7 (victories matter less)

Respond with JSON only."""

    def _build_input_prompt(
        self,
        events: List[str],
        government_actions: List[str],
        current_satisfaction: float,
        at_war: bool,
        turn: int = 1
    ) -> str:
        """Build the input prompt with current context."""
        # Mood description
        turn_header = f"## TURN {turn}\n\n"
        if current_satisfaction < 20:
            mood_desc = "ANGRY - On the verge of revolt"
        elif current_satisfaction < 40:
            mood_desc = "DISCONTENT - Unhappy with government"
        elif current_satisfaction < 60:
            mood_desc = "NEUTRAL - Tolerating the situation"
        elif current_satisfaction < 80:
            mood_desc = "CONTENT - Supporting the government"
        else:
            mood_desc = "EUPHORIC - Peak national pride"
        
        war_status = "AT WAR - Population is affected by military events" if at_war else "AT PEACE"
        
        events_text = "\n".join(f"- {e}" for e in events[-10:]) if events else "- No major events"
        actions_text = "\n".join(f"- {a}" for a in government_actions[-5:]) if government_actions else "- No actions taken"
        
        return turn_header + f"""## Current State
**Satisfaction:** {current_satisfaction:.0f}%
**Mood:** {mood_desc}
**Status:** {war_status}

## Recent Events
{events_text}

## Government Actions This Turn
{actions_text}

Based on cultural traits and events, how does the population react?"""

    def _deterministic_reaction(
        self,
        events: List[str],
        government_actions: List[str],
        current_satisfaction: float,
        at_war: bool
    ) -> OpinionResponse:
        """
        Fallback deterministic reaction when LLM is not available.
        
        Uses cultural traits to determine multipliers.
        """
        mult_inc = 1.0
        mult_dec = 1.0
        mood = "NEUTRAL"
        
        # Trait-based adjustments
        if "Nationalist" in self.cultural_traits:
            mult_dec *= 1.3  # More sensitive to defeats
            mult_inc *= 1.2  # More excited by victories
        
        if "Pacifist" in self.cultural_traits:
            mult_inc *= 0.8 if at_war else 1.2  # Less excited by war victories
            mult_dec *= 0.7 if not at_war else 1.3  # More affected by war
        
        if "Resilient" in self.cultural_traits:
            mult_dec *= 0.7  # Less affected by negative events
        
        if "Religious" in self.cultural_traits:
            mult_dec *= 0.9  # Slightly more accepting of hardship
        
        if "Militaristic" in self.cultural_traits:
            mult_inc *= 1.2 if at_war else 0.9
        
        if "Mercantile" in self.cultural_traits:
            # React more to economic events
            if any("TRADE" in e for e in events):
                mult_inc *= 1.3
        
        # War weariness
        if at_war and current_satisfaction < 40:
            mult_inc *= 0.8  # War-weary, victories matter less
            mult_dec *= 1.2  # Defeats hurt more
        
        # Clamp values
        mult_inc = max(0.1, min(2.0, mult_inc))
        mult_dec = max(0.1, min(2.0, mult_dec))
        
        # Determine mood
        if current_satisfaction < 30:
            mood = "DISCONTENT"
        elif current_satisfaction >= 70:
            mood = "CONTENT"
        
        return OpinionResponse(
            multiplier_increase=mult_inc,
            multiplier_decrease=mult_dec,
            mood=mood,
            reasoning=f"Deterministic reaction based on traits: {self.cultural_traits}"
        )


def apply_opinion_modifiers(
    nation: 'NationState',
    base_satisfaction_delta: float,
    opinion_response: OpinionResponse
) -> float:
    """
    Apply opinion multipliers to satisfaction change.
    
    Args:
        nation: Nation to update
        base_satisfaction_delta: Base change to satisfaction
        opinion_response: Response from Opinion agent
        
    Returns:
        Final satisfaction delta after multipliers
    """
    if base_satisfaction_delta > 0:
        final_delta = base_satisfaction_delta * opinion_response.multiplier_increase
    elif base_satisfaction_delta < 0:
        final_delta = base_satisfaction_delta * opinion_response.multiplier_decrease
    else:
        final_delta = 0
    
    # Apply to nation
    new_satisfaction = nation.public_satisfaction + final_delta
    nation.public_satisfaction = max(0, min(100, new_satisfaction))
    
    return final_delta
