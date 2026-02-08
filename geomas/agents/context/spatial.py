"""
Spatial Translator.

The Bridge between Geometry (Voronoi/NetworkX) and Cognition (LLM).
Translates topological features into natural language strategic intelligence.
"""

from typing import List, Dict, Set
from geomas.schemas.world import WorldState, TerrainType
from geomas.world.spatial.manager import SpatialManager


class SpatialTranslator:
    """
    The Bridge between Geometry (Voronoi/NetworkX) and Cognition (LLM).
    Translates topological features into natural language strategic intelligence.
    """

    def __init__(self, world: WorldState):
        self.world = world
        self.spatial = SpatialManager(world)

    def generate_intelligence_report(self, nation_id: str) -> str:
        """
        Generates a comprehensive strategic report for the given nation.
        Used as System Prompt injection for the Agent.
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return "Error: Nation not found."

        report_parts = []
        
        # 1. Self-Assessment (Geography)
        geo_desc = self._analyze_geography(nation_id)
        report_parts.append(f"**GEOGRAPHY:** {geo_desc}")

        # 2. Border Analysis (Threats & Terrain + Comparative Power)
        threat_desc = self._analyze_borders(nation_id)
        report_parts.append(f"**BORDERS & THREATS:** {threat_desc}")

        # 3. Encirclement Risk
        encirclement_desc = self._analyze_encirclement(nation_id)
        if encirclement_desc:
            report_parts.append(f"**STRATEGIC POSITION:** {encirclement_desc}")

        # 4. Resource Analysis (Vulnerability)
        res_desc = self._analyze_resources(nation_id)
        report_parts.append(f"**RESOURCES:** {res_desc}")

        return "\n\n".join(report_parts)

    def _analyze_geography(self, nation_id: str) -> str:
        """
        Determines the nation's geographic classification.
        
        Uses both coastal provinces AND territorial waters for accurate maritime assessment.
        """
        nation = self.world.nations[nation_id]
        total_provinces = len(nation.province_ids)
        coastal_provinces = self.spatial.get_coastal_provinces(nation_id)
        territorial_waters = len(nation.territorial_water_ids)
        land_neighbors = self.spatial.get_neighboring_nations(nation_id)
        
        # Calculate maritime indices
        coastal_ratio = len(coastal_provinces) / total_provinces if total_provinces > 0 else 0
        # Naval control: territorial waters relative to total controlled area
        total_controlled = total_provinces + territorial_waters
        naval_ratio = territorial_waters / total_controlled if total_controlled > 0 else 0
        
        # Combined maritime score (weighted average)
        maritime_score = (coastal_ratio * 0.6) + (naval_ratio * 0.4)
        
        # Classification logic
        if not coastal_provinces and territorial_waters == 0:
            return (
                f"You are a **Landlocked State**. You control {total_provinces} provinces "
                f"but have **ZERO sea access**. You are entirely dependent on neighbors for maritime trade."
            )
        
        if not land_neighbors:
            return (
                f"You are an **Island Nation** (Thalassocracy). You share NO land borders with "
                f"any other nation. You control {territorial_waters} territorial waters. "
                f"Your defense relies entirely on your navy."
            )
        
        # Tiered classification based on maritime score
        if maritime_score > 0.5:
            return (
                f"You are a **Maritime Power**. {int(coastal_ratio*100)}% of your {total_provinces} provinces "
                f"are coastal, and you control {territorial_waters} territorial waters. "
                f"Naval dominance is your key strength."
            )
        elif maritime_score > 0.25:
            return (
                f"You are a **Balanced Power**. You have {len(coastal_provinces)} coastal provinces "
                f"and {territorial_waters} territorial waters, but most of your territory is inland. "
                f"You can project power both on land and sea."
            )
        else:
            sea_access = "some" if coastal_provinces else "no"
            return (
                f"You are a **Continental Power**. Only {len(coastal_provinces)} of your "
                f"{total_provinces} provinces are coastal ({sea_access} sea access). "
                f"Your strength lies in land forces."
            )

    def _analyze_borders(self, nation_id: str) -> str:
        """
        Identifies neighbors with terrain-weighted risk AND comparative power.
        """
        neighbors = self.spatial.get_neighboring_nations(nation_id)
        if not neighbors:
            return "You are isolated and safe from immediate land invasion."

        my_nation = self.world.nations[nation_id]
        my_power = my_nation.power_projection
        border_provinces = self.spatial.get_border_provinces(nation_id)
        
        # Collect stats per neighbor
        neighbor_stats: Dict[str, Dict] = {}
        
        for p_id in border_provinces:
            prov = self.world.provinces[p_id]
            
            # Terrain-based risk modifier
            if prov.terrain == TerrainType.MOUNTAIN:
                risk_modifier = 0.3  # Highly defensible
            elif prov.terrain == TerrainType.COASTAL:
                risk_modifier = 1.2  # Naval invasion risk
            else:  # LAND
                risk_modifier = 1.0  # Normal
            
            for n_id in prov.neighbors:
                neighbor_prov = self.world.provinces.get(n_id)
                if neighbor_prov and neighbor_prov.owner_id and neighbor_prov.owner_id != nation_id:
                    enemy_id = neighbor_prov.owner_id
                    if enemy_id not in neighbor_stats:
                        neighbor_stats[enemy_id] = {"segments": 0, "risk_score": 0.0}
                    
                    neighbor_stats[enemy_id]["segments"] += 1
                    neighbor_stats[enemy_id]["risk_score"] += risk_modifier
        
        descriptions = []
        for enemy_id, stats in neighbor_stats.items():
            # Skip nations that were filtered out
            if enemy_id not in self.world.nations:
                continue
            enemy_nation = self.world.nations[enemy_id]
            enemy_power = enemy_nation.power_projection
            segments = stats["segments"]
            risk = stats["risk_score"]
            avg_risk = risk / segments if segments > 0 else 1.0
            
            # Border size description
            if segments > 5:
                size_desc = "massive"
            elif segments > 2:
                size_desc = "significant"
            else:
                size_desc = "small"
            
            # Terrain defensibility
            if avg_risk < 0.5:
                terrain_desc = "highly defensible (mountainous)"
            elif avg_risk > 1.1:
                terrain_desc = "vulnerable to naval invasion (coastal)"
            else:
                terrain_desc = "moderately defensible"
            
            # Comparative power analysis
            if my_power > 0:
                power_ratio = enemy_power / my_power
            else:
                power_ratio = 1.0  # Assume equal if we have no power data
                
            if power_ratio > 1.5:
                power_desc = "They are **significantly stronger** than you."
            elif power_ratio > 1.1:
                power_desc = "They are somewhat stronger."
            elif power_ratio < 0.6:
                power_desc = "They are **weaker** than you."
            elif power_ratio < 0.9:
                power_desc = "They are somewhat weaker."
            else:
                power_desc = "You are **evenly matched**."
            
            descriptions.append(
                f"**{enemy_nation.name}**: {size_desc} border, {terrain_desc}. {power_desc}"
            )
        
        return " ".join(descriptions)

    def _analyze_encirclement(self, nation_id: str) -> str:
        """
        Analyzes strategic position based on number and disposition of neighbors.
        """
        neighbors = self.spatial.get_neighboring_nations(nation_id)
        neighbor_count = len(neighbors)
        
        if neighbor_count == 0:
            return ""  # Island nation, handled in geography
        
        if neighbor_count >= 4:
            return (
                f"**ENCIRCLEMENT RISK**: You are surrounded by {neighbor_count} nations. "
                f"A coordinated attack from multiple fronts would be devastating. "
                f"Consider alliances to reduce hostile borders."
            )
        elif neighbor_count == 1:
            neighbor_id = list(neighbors)[0]
            # Skip if neighbor was filtered out
            if neighbor_id not in self.world.nations:
                return "You have limited neighbors."
            neighbor_name = self.world.nations[neighbor_id].name
            return (
                f"You have only one neighbor ({neighbor_name}). "
                f"Your diplomatic focus should be clear - this relationship defines your security."
            )
        elif neighbor_count == 2:
            return (
                f"You have {neighbor_count} neighbors. "
                f"Balance your relations carefully to avoid a two-front war."
            )
        else:  # 3 neighbors
            return (
                f"You have {neighbor_count} neighbors. "
                f"Consider which borders to fortify and which nations to befriend."
            )

    def _analyze_resources(self, nation_id: str) -> str:
        """Checks if resources are safe (inland) or vulnerable (border)."""
        nation = self.world.nations[nation_id]
        border_provinces = set(self.spatial.get_border_provinces(nation_id))
        
        totals = {"energy": 0.0, "materials": 0.0, "food": 0.0}
        vulnerable = {"energy": 0.0, "materials": 0.0, "food": 0.0}
        
        for p_id in nation.province_ids:
            prov = self.world.provinces[p_id]
            totals["energy"] += prov.energy_production
            totals["materials"] += prov.materials_production
            totals["food"] += prov.food_production
            
            if p_id in border_provinces:
                vulnerable["energy"] += prov.energy_production
                vulnerable["materials"] += prov.materials_production
                vulnerable["food"] += prov.food_production
                
        alerts = []
        for res_type in ["energy", "materials", "food"]:
            total = totals[res_type]
            vuln = vulnerable[res_type]
            
            if total > 0:
                ratio = vuln / total
                if ratio > 0.6:
                    alerts.append(
                        f"**{res_type.upper()} AT RISK:** {int(ratio*100)}% of production is on the border."
                    )
        
        if not alerts:
            return "Your key resources are well-protected inland."
        else:
            return " ".join(alerts)
