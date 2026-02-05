"""
Public Opinion Input Builder.

Generates dynamic context for the Public Opinion agent.
Includes events affecting population, satisfaction history, and cultural context.
"""

from typing import Optional, List, Dict, Any
from geomas.schemas.world import WorldState, NationState


class OpinionInputBuilder:
    """
    Builds dynamic input context for the Public Opinion agent.
    
    The Public Opinion agent receives:
    - Current satisfaction level and trend
    - Recent events affecting the population
    - Government actions impacting welfare
    - War/peace status (affects morale)
    """
    
    def __init__(self, world: WorldState):
        self.world = world
    
    def build(
        self,
        nation_id: str,
        recent_events: Optional[List[str]] = None,
        satisfaction_history: Optional[List[float]] = None,
        government_actions: Optional[List[str]] = None,
    ) -> str:
        """
        Build the input context for the Public Opinion agent.
        
        Args:
            nation_id: Nation ID
            recent_events: Events that affect public mood
            satisfaction_history: Recent satisfaction values (for trend)
            government_actions: Actions taken by the government
            
        Returns:
            Formatted input prompt (~1000 tokens max)
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return "Error: Nation not found."
        
        sections = []
        
        # 1. Current Satisfaction State
        sections.append(self._build_satisfaction_state(nation, satisfaction_history))
        
        # 2. War/Peace Status
        sections.append(self._build_conflict_status(nation_id))
        
        # 3. Recent Events Affecting Population
        if recent_events:
            sections.append(self._build_events(recent_events))
        
        # 4. Government Actions to React To
        if government_actions:
            sections.append(self._build_government_actions(government_actions))
        
        # 5. Economic Conditions
        sections.append(self._build_economic_conditions(nation))
        
        return "\n\n".join(sections)
    
    def _build_satisfaction_state(
        self, 
        nation: NationState, 
        history: Optional[List[float]]
    ) -> str:
        """Build current satisfaction state and trend."""
        sat = nation.public_satisfaction
        
        # Determine trend
        if history and len(history) >= 2:
            recent = history[-3:] if len(history) >= 3 else history
            trend = recent[-1] - recent[0]
            if trend > 5:
                trend_desc = "📈 Rising"
            elif trend < -5:
                trend_desc = "📉 Falling"
            else:
                trend_desc = "→ Stable"
        else:
            trend_desc = "→ Unknown"
        
        # Mood description
        if sat < 10:
            mood = "⚠️ CRISIS - Civil unrest imminent"
        elif sat < 30:
            mood = "😠 DISCONTENT - Protests likely"
        elif sat < 50:
            mood = "😐 NEUTRAL - Tolerating the situation"
        elif sat < 70:
            mood = "😊 CONTENT - Supporting the government"
        elif sat < 90:
            mood = "😄 HAPPY - Strong national unity"
        else:
            mood = "🎉 EUPHORIC - Peak national pride"
        
        return f"""## 👥 PUBLIC MOOD
**Satisfaction:** {sat:.0f}%
**Trend:** {trend_desc}
**Mood:** {mood}

You are reacting to recent events and government decisions."""

    def _build_conflict_status(self, nation_id: str) -> str:
        """Build war/peace status affecting morale."""
        lines = ["## ⚔️ CONFLICT STATUS"]
        
        relationships = self.world.relationship_matrix.get(nation_id, {})
        
        at_war = []
        for other_id, status in relationships.items():
            if status == "WAR":
                other_name = self.world.nations[other_id].name
                at_war.append(other_name)
        
        if at_war:
            lines.append(f"**AT WAR WITH:** {', '.join(at_war)}")
            lines.append("\nWar affects the population:")
            lines.append("- Victories boost morale")
            lines.append("- Defeats and casualties hurt morale")
            lines.append("- Long wars cause war weariness")
        else:
            lines.append("**AT PEACE**")
            lines.append("\nPeace is valued, but the population may support just wars.")
        
        return "\n".join(lines)
    
    def _build_events(self, events: List[str]) -> str:
        """Build events affecting population."""
        lines = ["## 📰 RECENT EVENTS TO REACT TO"]
        lines.append("The population has heard about these events:")
        for event in events[-8:]:
            lines.append(f"- {event}")
        lines.append("\nConsider how each event makes the people feel.")
        return "\n".join(lines)
    
    def _build_government_actions(self, actions: List[str]) -> str:
        """Build government actions to react to."""
        lines = ["## 🏛️ GOVERNMENT ACTIONS"]
        lines.append("The government has taken these actions:")
        for action in actions[-5:]:
            lines.append(f"- {action}")
        lines.append("\nHow do the people feel about these decisions?")
        return "\n".join(lines)
    
    def _build_economic_conditions(self, nation: NationState) -> str:
        """Build economic conditions affecting population."""
        lines = ["## 💰 ECONOMIC CONDITIONS"]
        
        # Resource status
        if nation.total_food < 50:
            lines.append("⚠️ **FOOD SHORTAGE** - People are hungry")
        elif nation.total_food > 200:
            lines.append("✅ **Food abundant** - People are well-fed")
        
        if nation.total_energy < 50:
            lines.append("⚠️ **ENERGY SHORTAGE** - Factories idle, homes cold")
        elif nation.total_energy > 200:
            lines.append("✅ **Energy abundant** - Economy thriving")
        
        # Budget status
        if nation.total_budget < 100:
            lines.append("⚠️ **TREASURY EMPTY** - No funds for welfare")
        elif nation.total_budget > 5000:
            lines.append("✅ **Treasury full** - Government can invest in people")
        
        # Civil unrest
        if nation.civil_unrest_active:
            lines.append("\n🔥 **CIVIL UNREST ACTIVE** - Strikes and protests ongoing!")
        
        return "\n".join(lines)
