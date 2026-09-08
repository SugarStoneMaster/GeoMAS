"""
Delta Analysis Module.

Provides utilities to compare two WorldStates or Simulation Timelines
to identify key differences (divergence) for Counterfactual Analysis.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from geomas.schemas.world import WorldState, NationState
# TYPE_CHECKING import to avoid circular dependency if LLMClient imports this? 
# LLMClient doesn't import this.
# But for type hint 'LLMClient', we can use string forward reference.

class DivergenceExplanation(BaseModel):
    """Structured explanation of divergence."""
    explanation: str

class DeltaAnalyzer:
    """
    Analyzes differences between two simulation states.
    """

    @staticmethod
    def explain_divergence(
        base: WorldState, 
        fork: WorldState, 
        client: 'LLMClient',
        injection_description: str
    ) -> str:
        """
        Generate a natural language explanation for why the fork diverged.
        """
        deltas = DeltaAnalyzer.compare_worlds(base, fork)
        score = DeltaAnalyzer.calculate_divergence_score(base, fork)
        
        # Format deltas for prompt (Reuse summary logic)
        summary = f"Divergence Score: {score:.1f}\n\n"
        
        # 1. Major Nation Changes
        summary += "## Nation Changes\n"
        for nid, d in deltas["nations"].items():
            # Only include significant changes
            changes = []
            if abs(d["satisfaction"]) > 5:
                changes.append(f"Satisfaction: {d['satisfaction']:+.1f}")
            if abs(d["power"]) > 10:
                changes.append(f"Power: {d['power']:+.1f}")
            if d["military"]["soldiers"] != 0:
                changes.append(f"Troops: {d['military']['soldiers']:+d}")
            if d["resources"]["budget"] != 0:
                 changes.append(f"Budget: {d['resources']['budget']:+.1f}")
            
            if changes:
                summary += f"- {nid}: {', '.join(changes)}\n"
                
        # 2. Global Changes
        summary += "\n## Global Changes\n"
        summary += f"Trust Divergence: {deltas['global']['total_trust_divergence']:.1f}\n"
        if deltas["global"]["relationship_changes"]:
            summary += "Relationship Shifts:\n"
            for rel in deltas["global"]["relationship_changes"]:
                summary += f"  - {rel['pair']} changed from {rel['base']} to {rel['fork']}\n"
        
        system_prompt = "You are an expert geopolitical analyst."
        user_prompt = f"""Comparing two timelines:
1. **Base Timeline**: Standard run.
2. **Counterfactual Timeline**: Diverged at Turn {base.turn} with injection: "{injection_description}".

## Observed Differences (Delta)
{summary}

## Task
Explain **WHY** these changes occurred based on the injection. Focus on the causal chain.
Keep it concise (max 3 sentences)."""

        response = client.query_agent(
            system_prompt, 
            user_prompt, 
            DivergenceExplanation
        )
        return response.explanation

    @staticmethod
    def compare_worlds(base: WorldState, fork: WorldState) -> Dict[str, Any]:
        """
        Compare two world states at the same turn (or different if needed).
        Returns a dictionary of deltas by nation and global metrics.
        """
        deltas = {"nations": {}, "global": {}}
        
        # 1. Nation Deltas
        for nation_id in base.nations:
            if nation_id not in fork.nations:
                continue
                
            n_base = base.nations[nation_id]
            n_fork = fork.nations[nation_id]
            
            deltas["nations"][nation_id] = {
                "satisfaction": n_fork.public_satisfaction - n_base.public_satisfaction,
                "power": n_fork.power_projection - n_base.power_projection,
                "resources": {
                    "budget": n_fork.total_budget - n_base.total_budget,
                    "food": n_fork.total_food - n_base.total_food,
                    "energy": n_fork.total_energy - n_base.total_energy,
                    "materials": n_fork.total_materials - n_base.total_materials,
                },
                "military": {
                    "soldiers": n_fork.total_soldiers - n_base.total_soldiers,
                    "nukes": n_fork.nukes - n_base.nukes,
                }
            }

        # 2. Global Deltas (Trust & Relationships)
        trust_diff = 0.0
        rel_changes = []
        
        for n1 in base.trust_matrix:
            for n2 in base.trust_matrix[n1]:
                t_base = base.trust_matrix[n1][n2]
                t_fork = fork.trust_matrix.get(n1, {}).get(n2, 50.0)
                trust_diff += abs(t_fork - t_base)
                
                # Relationships
                r_base = base.relationship_matrix.get(n1, {}).get(n2, "PEACE")
                r_fork = fork.relationship_matrix.get(n1, {}).get(n2, "PEACE")
                
                if r_base != r_fork:
                    # Avoid duplicates (n1-n2 vs n2-n1) by sorting
                    pair = sorted([n1, n2])
                    change = {"pair": pair, "base": r_base, "fork": r_fork}
                    if change not in rel_changes:
                        rel_changes.append(change)
        
        deltas["global"] = {
            "total_trust_divergence": trust_diff,
            "relationship_changes": rel_changes,
            "turn_divergence": fork.turn - base.turn
        }
            
        return deltas

    @staticmethod
    def compare_timelines(base_history: List[WorldState], fork_history: List[WorldState]) -> List[Dict[str, Any]]:
        """
        Compare two timelines step-by-step.
        Returns a list of deltas for each overlapping turn.
        """
        timeline_deltas = []
        min_len = min(len(base_history), len(fork_history))
        
        for i in range(min_len):
            timeline_deltas.append(
                DeltaAnalyzer.compare_worlds(base_history[i], fork_history[i])
            )
            
        return timeline_deltas

    @staticmethod
    def calculate_divergence_score(base: WorldState, fork: WorldState) -> float:
        """
        Calculate a single scalar representing how much the fork has diverged from base.
        Weighted sum of attribute differences.
        """
        deltas = DeltaAnalyzer.compare_worlds(base, fork)
        score = 0.0
        
        # Weights
        W_SAT = 1.0
        W_POWER = 0.1
        W_TRUST = 0.5
        W_REL = 50.0  # Relationship change is huge
        
        # Nation scores
        for n_id, n_data in deltas["nations"].items():
            score += abs(n_data["satisfaction"]) * W_SAT
            score += abs(n_data["power"]) * W_POWER
        
        # Global scores
        score += deltas["global"]["total_trust_divergence"] * W_TRUST
        score += len(deltas["global"]["relationship_changes"]) * W_REL
        
        return score
