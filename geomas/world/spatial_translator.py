from typing import List, Dict, Tuple
from geomas.schemas.world import WorldState, TerrainType # Updated import
from geomas.world.spatial_manager import SpatialManager

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

        # 2. Border Analysis (Threats & Terrain)
        threat_desc = self._analyze_borders(nation_id)
        report_parts.append(f"**BORDERS & THREATS:** {threat_desc}")

        # 3. Strategic Depth (Capital Safety)
        depth_desc = self._analyze_strategic_depth(nation_id)
        report_parts.append(f"**STRATEGIC DEPTH:** {depth_desc}")

        # 4. Resource Analysis (Economy)
        res_desc = self._analyze_resources(nation_id)
        report_parts.append(f"**RESOURCES:** {res_desc}")

        return "\n\n".join(report_parts)

    def _analyze_geography(self, nation_id: str) -> str:
        """Determines if the nation is Landlocked, Island, or Continental."""
        nation = self.world.nations[nation_id]
        total_provinces = len(nation.province_ids)
        coastal_provinces = self.spatial.get_coastal_provinces(nation_id)
        
        land_neighbors = self.spatial.get_neighboring_nations(nation_id)
        
        if not coastal_provinces:
            return f"You are a **Landlocked State**. You control {total_provinces} provinces but have **ZERO sea access**. You are entirely dependent on neighbors for maritime trade."
        
        if not land_neighbors:
            return f"You are an **Island Nation** (Thalassocracy). You share NO land borders with any other nation. Your defense relies entirely on your navy."
        
        coast_ratio = len(coastal_provinces) / total_provinces
        if coast_ratio > 0.6:
            return f"You are a **Maritime Power**. Most of your territory ({int(coast_ratio*100)}%) is coastal, but you do share land borders."
        else:
            return f"You are a **Continental Power**. Only {len(coastal_provinces)} of your {total_provinces} provinces are coastal."

    def _analyze_borders(self, nation_id: str) -> str:
        """Identifies neighbors and potential encirclement risks, weighted by terrain."""
        neighbors = self.spatial.get_neighboring_nations(nation_id)
        if not neighbors:
            return "You are isolated and safe from immediate land invasion."

        descriptions = []
        border_provinces = self.spatial.get_border_provinces(nation_id)
        
        neighbor_stats = {} 
        
        for p_id in border_provinces:
            prov = self.world.provinces[p_id]
            
            risk_modifier = 0.3 if prov.terrain == TerrainType.MOUNTAIN else 1.0
            
            for n_id in prov.neighbors:
                neighbor_prov = self.world.provinces.get(n_id)
                if neighbor_prov and neighbor_prov.owner_id and neighbor_prov.owner_id != nation_id:
                    enemy_id = neighbor_prov.owner_id
                    if enemy_id not in neighbor_stats:
                        neighbor_stats[enemy_id] = {"segments": 0, "risk_score": 0.0}
                    
                    neighbor_stats[enemy_id]["segments"] += 1
                    neighbor_stats[enemy_id]["risk_score"] += risk_modifier
        
        for enemy_id, stats in neighbor_stats.items():
            enemy_name = self.world.nations[enemy_id].name
            segments = stats["segments"]
            risk = stats["risk_score"]
            
            avg_risk = risk / segments if segments > 0 else 1.0
            
            if segments > 5:
                size_desc = "massive border"
            elif segments > 2:
                size_desc = "significant border"
            else:
                size_desc = "small border"
            
            if avg_risk < 0.5:
                def_desc = "**highly defensible** (Mountains)"
            else:
                def_desc = "**vulnerable** (Open Plains/Coast)"
            
            descriptions.append(f"You share a {size_desc} with {enemy_name}, which is {def_desc}.")
            
        return " ".join(descriptions)

    def _analyze_strategic_depth(self, nation_id: str) -> str:
        """Calculates how far the Capital is from the nearest enemy."""
        nation = self.world.nations[nation_id]
        if not nation.capital_province_id:
            return "Capital location unknown."
            
        border_provinces = self.spatial.get_border_provinces(nation_id)
        if not border_provinces:
            return "Your Capital is safe (Island)."
            
        min_hops = float('inf')
        for bp_id in border_provinces:
            hops = self.spatial.get_path_length(nation.capital_province_id, bp_id)
            if hops != -1 and hops < min_hops:
                min_hops = hops
        
        if min_hops <= 1:
            return "**CRITICAL DANGER:** Your Capital is on the frontline (1 hop from border). You have **Zero Strategic Depth**."
        elif min_hops <= 3:
            return "Your Capital is vulnerable (Shallow Strategic Depth). An enemy breakthrough would threaten it quickly."
        else:
            return f"Your Capital is secure deep inland ({min_hops} hops from border). You have **Excellent Strategic Depth**."

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
                    alerts.append(f"**{res_type.upper()} AT RISK:** {int(ratio*100)}% of production is on the border.")
        
        if not alerts:
            return "Your key resources are well-protected inland."
        else:
            return " ".join(alerts)
