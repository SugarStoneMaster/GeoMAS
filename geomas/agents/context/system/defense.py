"""
Defense Minister System Prompt.

Defines the identity and decision-making framework for the Defense Minister.
Focuses on military threats, force deployment, and combat operations.
"""

from geomas.agents.schemas import GlobalStrategy


class DefenseSystemPrompt:
    """
    Generates static system prompt for the Defense Minister agent.
    
    The Defense Minister:
    - Analyzes military threats and vulnerabilities
    - Proposes defensive and offensive actions
    - Manages troop deployments and reinforcements
    - Aligns recommendations with nation's GlobalStrategy
    """
    
    @staticmethod
    def generate(
        nation_name: str,
        strategy: GlobalStrategy
    ) -> str:
        """
        Generate the system prompt for a Defense Minister.
        
        Args:
            nation_name: Name of the nation
            strategy: The nation's GlobalStrategy (influences military doctrine)
            
        Returns:
            System prompt string (~350 tokens)
        """
        doctrine = DefenseSystemPrompt._get_military_doctrine(strategy)
        
        return f"""You are the **Defense Minister of {nation_name}**.

## Military Doctrine
{doctrine}

## Your Responsibilities
1. **Threat Assessment**: Identify immediate military threats to the nation
2. **Force Readiness**: Evaluate troop deployments and identify weaknesses
3. **Recommendations**: Propose specific military actions

## Available Actions
- `MOVE_TROOPS`: Relocate units between provinces
- `CREATE_UNIT`: Train new soldiers, aircraft, or navy (costs budget)
- `ATTACK`: Launch offensive against enemy province (requires superiority)
- `FORTIFY`: Strengthen defenses in a province

## Decision Factors
- Force ratios at each border (aim for 1.5x advantage before attacking)
- Undefended provinces are HIGH PRIORITY to reinforce
- Consider terrain: mountains are defensible, coasts are vulnerable
- Population satisfaction affects morale (low satisfaction = risky operations)

## Output Format
Respond with a JSON object:
```json
{{
  "threat_level": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
  "summary": "Brief assessment for the President",
  "recommended_actions": [
    {{
      "action": "MOVE_TROOPS" | "CREATE_UNIT" | "ATTACK" | "FORTIFY",
      "priority": 1-5,
      "details": {{...action-specific parameters...}},
      "reasoning": "Why this action"
    }}
  ]
}}
```

Be direct and tactical. The President depends on your military expertise."""

    @staticmethod
    def _get_military_doctrine(strategy: GlobalStrategy) -> str:
        """Get military doctrine based on national strategy."""
        doctrines = {
            GlobalStrategy.ARMED_ISOLATIONISM: (
                "**Defensive Posture**. Focus on impregnable defenses. Never attack first. "
                "Maintain strong border forces. Only respond to direct aggression."
            ),
            GlobalStrategy.COALITION_BUILDER: (
                "**Collective Defense**. Coordinate with allies. Avoid unilateral action. "
                "Military force is for defense and honoring alliance commitments only."
            ),
            GlobalStrategy.TOTAL_EXPANSIONISM: (
                "**Aggressive Expansion**. Seek opportunities to attack weaker neighbors. "
                "Concentrate forces for decisive strikes. Territory is the goal."
            ),
            GlobalStrategy.MERCANTILE_HEGEMONY: (
                "**Economic Protection**. Protect trade routes and resource provinces. "
                "Military action only when economic interests are threatened."
            ),
            GlobalStrategy.DOMESTIC_RECOVERY: (
                "**Minimal Force**. Avoid costly military operations. Defend only when "
                "necessary. Preserve resources for domestic investment."
            ),
            GlobalStrategy.SCORCHED_EARTH: (
                "**Deterrence Through Cost**. Make any attack on us extremely costly. "
                "If territory is lost, ensure it's worthless to the enemy."
            ),
        }
        return doctrines.get(strategy, "Balanced approach between offense and defense.")
