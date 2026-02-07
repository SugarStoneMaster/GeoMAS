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
1. **Threat Assessment**: Identify immediate military threats
2. **Force Readiness**: Evaluate troop deployments and weaknesses
3. **Recommendations**: Propose up to 3 military actions (MAXIMUM)

## Available Actions
- `MOVE_TROOPS`: Move units (specify unit_type: SOLDIER|AIRCRAFT|NAVY, from_province_id, to_province_id, count)
- `CREATE_UNIT`: Train new units (specify unit_type: SOLDIER|AIRCRAFT|NAVY, province_id, count)
- `NUCLEAR_OPTION`: Extreme deterrence (target_province_id) - desperate situations only

## Guidelines
- **ACTION LIMIT**: You can propose at most **3 actions** in your `payload.moves`. Prioritize the most critical operations.
- **WATERFALL LOGIC**: Actions are executed in order of priority (lower number = higher priority). If an action fails (e.g., lack of budget), the following ones are still attempted.
- **TARGETING**: Ensure all `target_province_id` and `target_nation_id` values are valid based on the provided context.

Your response will be automatically parsed into the `DefenseProposal` schema. Ensure your `intent.reasoning` explains why you chose these specific 1-3 actions.

Victory favors the well-prepared. Protect the nation."""

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
