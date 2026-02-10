"""
Military Translator.

Translates dynamic military state into natural language for LLM agents.
Provides actionable intelligence about troop positions, force ratios, and threats.
"""

from typing import Dict, List, Set, Tuple
from geomas.schemas.world import WorldState, TerrainType
from geomas.world.spatial.manager import SpatialManager


class MilitaryTranslator:
    """
    Translates military state into actionable LLM context.
    
    Provides:
    - Own force deployment (where are my troops?)
    - Enemy forces at borders (what threats do I face?)
    - Force ratios vs neighbors (am I stronger or weaker?)
    - Vulnerable points (where should I defend?)
    - Attack options (what can I realistically attack?)
    """
    
    def __init__(self, world: WorldState):
        self.world = world
        self.spatial = SpatialManager(world)
    
    def generate_military_report(self, nation_id: str) -> str:
        """
        Generate comprehensive military intelligence report.
        
        Args:
            nation_id: Nation to generate report for
            
        Returns:
            Formatted military report for LLM consumption
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return "Error: Nation not found."
        
        sections = []
        
        # 1. Force Overview (own military strength)
        overview = self._generate_force_overview(nation_id)
        sections.append(overview)
        
        # 2. Deployment Status (where are troops stationed?)
        deployment = self._generate_deployment_status(nation_id)
        sections.append(deployment)
        
        # 3. Border Defense Analysis (strength at each border)
        border_defense = self._generate_border_defense(nation_id)
        if border_defense:
            sections.append(border_defense)
        
        # 4. Threat Assessment (enemy concentrations)
        threats = self._generate_threat_assessment(nation_id)
        if threats:
            sections.append(threats)
        
        # 5. Military Options (what can we do?)
        options = self._generate_military_options(nation_id)
        if options:
            sections.append(options)
            
        # 6. Full Province List (Grounding for LLM)
        provinces = self._generate_province_list(nation_id)
        sections.append(provinces)
        
        return "\n\n".join(sections)
    
    def _generate_force_overview(self, nation_id: str) -> str:
        """Generate overview of total military strength."""
        nation = self.world.nations[nation_id]
        
        # Calculate total forces
        total_soldiers = nation.total_soldiers
        total_aircraft = nation.total_aircraft
        total_navy = nation.total_navy
        
        # Compare to neighbors
        neighbors = self.spatial.get_neighboring_nations(nation_id)
        if neighbors:
            neighbor_totals = []
            for n_id in neighbors:
                n = self.world.nations[n_id]
                neighbor_totals.append(n.total_soldiers + n.total_aircraft + n.total_navy)
            avg_neighbor = sum(neighbor_totals) / len(neighbor_totals) if neighbor_totals else 0
            my_total = total_soldiers + total_aircraft + total_navy
            
            if my_total > avg_neighbor * 1.5:
                comparison = "You have **superior military strength** compared to your neighbors."
            elif my_total > avg_neighbor:
                comparison = "You have **adequate military strength** for defense."
            elif my_total > avg_neighbor * 0.5:
                comparison = "Your military is **below average** for the region. Consider buildup."
            else:
                comparison = "**CRITICAL:** Your military is severely understrength. You are vulnerable."
        else:
            comparison = "You have no land neighbors to compare against."
        
        # Nuclear status
        nuke_status = ""
        if nation.nukes > 0:
            nuke_status = f"\n**NUCLEAR ARSENAL:** {nation.nukes} warheads available."
        
        return f"""## ⚔️ MILITARY OVERVIEW

**Ground Forces:** {total_soldiers:,} soldiers
**Air Force:** {total_aircraft:,} aircraft
**Navy:** {total_navy:,} ships

{comparison}{nuke_status}"""

    def _generate_deployment_status(self, nation_id: str) -> str:
        """Generate report on troop deployment across provinces."""
        nation = self.world.nations[nation_id]
        border_provinces = set(self.spatial.get_border_provinces(nation_id))
        
        # Categorize provinces by troop presence
        heavily_defended = []
        lightly_defended = []
        undefended = []
        interior_forces = []
        
        for p_id in nation.province_ids:
            prov = self.world.provinces[p_id]
            total_units = prov.soldiers + prov.aircraft
            is_border = p_id in border_provinces
            
            if is_border:
                if total_units >= 100:
                    heavily_defended.append((p_id, total_units))
                elif total_units > 0:
                    lightly_defended.append((p_id, total_units))
                else:
                    undefended.append(p_id)
            else:
                if total_units > 0:
                    interior_forces.append((p_id, total_units))
        
        lines = ["## 🗺️ FORCE DEPLOYMENT"]
        
        if heavily_defended:
            lines.append(f"\n**Fortified borders:** {len(heavily_defended)} provinces (100+ units each)")
        
        if lightly_defended:
            lines.append(f"**Light defense:** {len(lightly_defended)} border provinces")
        
        if undefended:
            lines.append(f"**⚠️ UNDEFENDED BORDERS:** {len(undefended)} provinces have NO troops!")
        
        if interior_forces:
            total_interior = sum(u for _, u in interior_forces)
            lines.append(f"**Reserves:** {total_interior:,} units in {len(interior_forces)} interior provinces")
        
        # Calculate border coverage
        total_border = len(border_provinces)
        defended_border = len(heavily_defended) + len(lightly_defended)
        if total_border > 0:
            coverage = (defended_border / total_border) * 100
            lines.append(f"\n**Border coverage:** {coverage:.0f}% of border provinces have troops")
        
        return "\n".join(lines)

    def _generate_border_defense(self, nation_id: str) -> str:
        """Analyze defense strength at each border with neighbors."""
        neighbors = self.spatial.get_neighboring_nations(nation_id)
        if not neighbors:
            return ""
        
        border_provinces = self.spatial.get_border_provinces(nation_id)
        
        # Calculate forces facing each neighbor
        neighbor_analysis: Dict[str, Dict] = {}
        
        for p_id in border_provinces:
            prov = self.world.provinces[p_id]
            my_forces = prov.soldiers + prov.aircraft
            
            # Check which neighbors this province borders
            for n_id in prov.neighbors:
                neighbor_prov = self.world.provinces.get(n_id)
                if neighbor_prov and neighbor_prov.owner_id and neighbor_prov.owner_id != nation_id:
                    enemy_id = neighbor_prov.owner_id
                    if enemy_id not in neighbor_analysis:
                        neighbor_analysis[enemy_id] = {
                            "my_forces": 0,
                            "enemy_forces": 0,
                            "provinces": 0,
                            "enemy_provinces": set()
                        }
                    
                    neighbor_analysis[enemy_id]["my_forces"] += my_forces
                    neighbor_analysis[enemy_id]["provinces"] += 1
                    
                    # Count enemy forces in adjacent province
                    enemy_forces = neighbor_prov.soldiers + neighbor_prov.aircraft
                    if n_id not in neighbor_analysis[enemy_id]["enemy_provinces"]:
                        neighbor_analysis[enemy_id]["enemy_forces"] += enemy_forces
                        neighbor_analysis[enemy_id]["enemy_provinces"].add(n_id)
        
        lines = ["## 🛡️ BORDER DEFENSE STATUS"]
        
        for enemy_id, data in neighbor_analysis.items():
            # Skip nations that were filtered out
            if enemy_id not in self.world.nations:
                continue
            enemy_name = self.world.nations[enemy_id].name
            my_forces = data["my_forces"]
            enemy_forces = data["enemy_forces"]
            
            # Calculate force ratio
            if enemy_forces > 0:
                ratio = my_forces / enemy_forces
            else:
                ratio = float('inf') if my_forces > 0 else 1.0
            
            # Determine status
            if ratio >= 2.0:
                status = "**STRONG** - You have overwhelming superiority"
            elif ratio >= 1.2:
                status = "**ADEQUATE** - You have the advantage"
            elif ratio >= 0.8:
                status = "**CONTESTED** - Forces are roughly equal"
            elif ratio >= 0.5:
                status = "**WEAK** - Enemy has the advantage"
            else:
                status = "**CRITICAL** - Enemy has overwhelming superiority"
            
            lines.append(f"\n**vs {enemy_name}:** {status}")
            lines.append(f"  Your forces: {my_forces:,} | Their forces: {enemy_forces:,}")
        
        return "\n".join(lines)

    def _generate_threat_assessment(self, nation_id: str) -> str:
        """Identify immediate threats from enemy concentrations."""
        border_provinces = self.spatial.get_border_provinces(nation_id)
        
        threats = []
        
        for p_id in border_provinces:
            prov = self.world.provinces[p_id]
            my_defense = prov.soldiers + prov.aircraft
            
            # Check adjacent enemy provinces for concentrations
            for n_id in prov.neighbors:
                neighbor_prov = self.world.provinces.get(n_id)
                if neighbor_prov and neighbor_prov.owner_id and neighbor_prov.owner_id != nation_id:
                    enemy_forces = neighbor_prov.soldiers + neighbor_prov.aircraft
                    
                    # Threat if enemy has significant force advantage
                    if enemy_forces > my_defense * 1.5 and enemy_forces >= 50:
                        # Skip nations that were filtered out
                        if neighbor_prov.owner_id not in self.world.nations:
                            continue
                        enemy_name = self.world.nations[neighbor_prov.owner_id].name
                        threats.append({
                            "province_id": p_id,
                            "enemy": enemy_name,
                            "enemy_forces": enemy_forces,
                            "my_defense": my_defense
                        })
        
        if not threats:
            return ""
        
        lines = ["## ⚠️ THREAT ASSESSMENT"]
        
        # Sort by severity (enemy force advantage)
        threats.sort(key=lambda t: t["enemy_forces"] - t["my_defense"], reverse=True)
        
        for threat in threats[:5]:  # Top 5 threats
            lines.append(
                f"\n**THREAT from {threat['enemy']}:** {threat['enemy_forces']:,} enemy units "
                f"facing only {threat['my_defense']:,} defenders at province {threat['province_id']}"
            )
        
        if len(threats) > 5:
            lines.append(f"\n... and {len(threats) - 5} additional threat zones")
        
        return "\n".join(lines)

    def analyze_threats(self, nation_id: str) -> str:
        """
        Produce a high-level strategic threat analysis.
        Used by DefenseInputBuilder for strategic assessment.
        """
        # Reuse existing components to build a summary
        threat_text = self._generate_threat_assessment(nation_id)
        border_text = self._generate_border_defense(nation_id)
        
        if not threat_text and not border_text:
            return "No immediate external threats detected."
            
        return f"{threat_text}\n\n{border_text}"

    def _generate_military_options(self, nation_id: str) -> str:
        """Identify viable military options (attack targets, reinforcement needs)."""
        border_provinces = self.spatial.get_border_provinces(nation_id)
        
        attack_options = []
        reinforce_needs = []
        
        for p_id in border_provinces:
            prov = self.world.provinces[p_id]
            my_forces = prov.soldiers + prov.aircraft
            
            for n_id in prov.neighbors:
                neighbor_prov = self.world.provinces.get(n_id)
                if neighbor_prov and neighbor_prov.owner_id and neighbor_prov.owner_id != nation_id:
                    if neighbor_prov.owner_id is None:
                        continue  # Skip unowned/ocean
                    
                    enemy_forces = neighbor_prov.soldiers + neighbor_prov.aircraft
                    # Skip nations that were filtered out
                    if neighbor_prov.owner_id not in self.world.nations:
                        continue
                    enemy_name = self.world.nations[neighbor_prov.owner_id].name
                    
                    # Attack viable if we have significant advantage
                    if my_forces >= enemy_forces * 1.5 and my_forces >= 50:
                        attack_options.append({
                            "target_id": n_id,
                            "enemy": enemy_name,
                            "enemy_forces": enemy_forces,
                            "my_forces": my_forces,
                            "from_province": p_id
                        })
                    
                    # Reinforcement needed if we're weak
                    if enemy_forces > my_forces * 1.5 and my_forces < 100:
                        reinforce_needs.append({
                            "province_id": p_id,
                            "current_forces": my_forces,
                            "enemy_threat": enemy_forces
                        })
        
        lines = []
        
        if attack_options:
            lines.append("## 🎯 ATTACK OPTIONS")
            # Sort by advantage ratio
            attack_options.sort(key=lambda a: a["my_forces"] / max(a["enemy_forces"], 1), reverse=True)
            
            for opt in attack_options[:3]:  # Top 3 options
                ratio = opt["my_forces"] / max(opt["enemy_forces"], 1)
                lines.append(
                    f"\n**Target {opt['enemy']}** (province {opt['target_id']}): "
                    f"You have {ratio:.1f}x advantage ({opt['my_forces']:,} vs {opt['enemy_forces']:,})"
                )
        
        if reinforce_needs:
            lines.append("\n## 🔧 REINFORCEMENT PRIORITIES")
            reinforce_needs.sort(key=lambda r: r["enemy_threat"], reverse=True)
            
            for need in reinforce_needs[:3]:
                lines.append(
                    f"\n**Province {need['province_id']}** needs reinforcement: "
                    f"only {need['current_forces']:,} troops vs {need['enemy_threat']:,} enemy threat"
                )
        
        if not lines:
            return "## 📊 MILITARY STATUS\n\nNo immediate attack options or reinforcement priorities."
        
        return "\n".join(lines)

    def _generate_province_list(self, nation_id: str) -> str:
        """Provide a complete list of owned provinces and their CONNECTIVITY for logistic planning."""
        nation = self.world.nations.get(nation_id)
        if not nation: return ""
        
        # Sort by ID for stability
        p_ids = sorted(nation.province_ids)
        
        lines = ["## 🚚 LOGISTICS & CONNECTIVITY"]
        lines.append("Complete map of your territory and neighbors. Use this to find valid paths.")
        lines.append("**Legend:** (S=Soldier, N=Navy, A=Aircraft) -> [Neighbors]")
        lines.append("**⚠️ RULE:** The numbers shown are the MAXIMUM units you can move FROM that province. You CANNOT move more than what is shown.")
        
        for p_id in p_ids:
            prov = self.world.provinces.get(p_id)
            if not prov: continue
            
            # Terrain tag
            terrain_tag = f"[{prov.terrain.value.upper()}]" if prov.terrain else ""
            
            # Unit string
            unit_strs = []
            if prov.soldiers > 0: unit_strs.append(f"{prov.soldiers}S")
            if prov.aircraft > 0: unit_strs.append(f"{prov.aircraft}A")
            if prov.navy > 0: unit_strs.append(f"{prov.navy}N")
            units = f" ({', '.join(unit_strs)})" if unit_strs else ""
            
            # Neighbors string
            neighbor_strs = []
            for n_id in prov.neighbors:
                n_prov = self.world.provinces.get(n_id)
                if not n_prov: continue
                
                n_info = f"{n_id}"
                if n_prov.owner_id == nation_id:
                    n_info += "(Own)"
                elif n_prov.owner_id:
                    # Enemy/Other
                    owner_name = self.world.nations[n_prov.owner_id].name[:3].upper() # Abbreviate
                    n_info += f"(Enemy-{owner_name})"
                elif n_prov.terrain == TerrainType.OCEAN:
                    n_info += "(Sea)"
                else:
                    n_info += "(Neutral)"
                
                neighbor_strs.append(n_info)
            
            lines.append(f"- **{p_id}** {terrain_tag}{units} -> [{', '.join(neighbor_strs)}]")
            
        return "\n".join(lines)
