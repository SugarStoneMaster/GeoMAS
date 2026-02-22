"""
Military Translator.

Translates dynamic military state into natural language for LLM agents.
Provides actionable intelligence about troop positions, force ratios, and threats.
The prompt is organized around STRATEGIC INTENTIONS — why to move troops —
rather than raw province-to-province movement lists.
"""

from typing import Dict, List, Set, Tuple
from collections import deque
from geomas.schemas.world import WorldState, TerrainType, RelationshipState
from geomas.world.spatial.manager import SpatialManager
from geomas.actions.defense.schemas import MOVEMENT_RANGE, MOVEMENT_ENERGY_COST, UnitType


class MilitaryTranslator:
    """
    Translates military state into actionable LLM context.

    Provides:
    - Own force deployment (where are my troops?)
    - Enemy forces at borders (what threats do I face?)
    - Force ratios vs neighbors (am I stronger or weaker?)
    - Vulnerable points (where should I defend?)
    - Intent-based strategic options (why to move troops, with JSON hints)
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
        sections.append(self._generate_force_overview(nation_id))

        # 2. Deployment Status (where are troops stationed?)
        sections.append(self._generate_deployment_status(nation_id))

        # 3. Border Defense Analysis (strength at each border)
        border_defense = self._generate_border_defense(nation_id)
        if border_defense:
            sections.append(border_defense)

        # 4. Threat Assessment (enemy concentrations)
        threats = self._generate_threat_assessment(nation_id)
        if threats:
            sections.append(threats)

        # 5. Intent-based Strategic Options (replaces raw movement list)
        sections.append(self._generate_strategic_intentions(nation_id))

        return "\n\n".join(sections)

    def _generate_force_overview(self, nation_id: str) -> str:
        """Generate overview of total military strength."""
        nation = self.world.nations[nation_id]

        total_soldiers = nation.total_soldiers
        total_aircraft = nation.total_aircraft
        total_navy = nation.total_navy

        neighbors = self.spatial.get_neighboring_nations(nation_id)
        if neighbors:
            neighbor_totals = [
                self.world.nations[n].total_soldiers + self.world.nations[n].total_aircraft + self.world.nations[n].total_navy
                for n in neighbors if n in self.world.nations
            ]
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

        nuke_status = ""
        if nation.nukes > 0:
            nuke_status = f"**☢️ NUCLEAR ARSENAL:** {nation.nukes} warheads available.\n\n"

        return f"""## MILITARY OVERVIEW

{nuke_status}**Ground Forces:** {total_soldiers:,} soldiers
**Air Force:** {total_aircraft:,} aircraft
**Navy:** {total_navy:,} ships

{comparison}"""

    def _generate_deployment_status(self, nation_id: str) -> str:
        """Generate report on troop deployment across provinces."""
        nation = self.world.nations[nation_id]
        border_provinces = set(self.spatial.get_border_provinces(nation_id))

        heavily_defended = []
        lightly_defended = []
        undefended = []
        interior_count = 0
        interior_units = 0

        for p_id in nation.province_ids:
            prov = self.world.provinces.get(p_id)
            if not prov:
                continue
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
                    interior_count += 1
                    interior_units += total_units

        lines = ["## FORCE DEPLOYMENT"]

        if heavily_defended:
            hd_str = ", ".join(f"{p_id}({u})" for p_id, u in heavily_defended[:8])
            lines.append(f"\n**Fortified borders ({len(heavily_defended)}):** {hd_str}")

        if lightly_defended:
            ld_str = ", ".join(f"{p_id}({u})" for p_id, u in lightly_defended[:8])
            lines.append(f"**Light defense ({len(lightly_defended)}):** {ld_str}")

        if undefended:
            ud_str = ", ".join(str(p_id) for p_id in undefended[:10])
            lines.append(f"**UNDEFENDED BORDERS ({len(undefended)}):** {ud_str}")
            lines.append("  → Consider CREATE_UNIT or MOVE_TROOPS to fill these gaps!")

        if interior_units > 0:
            lines.append(f"**Reserves (Interior):** {interior_units:,} units in {interior_count} provinces")

        # Guest Troops (Allied Stationing)
        guest_locs = []
        for p_id, province in self.world.provinces.items():
            if province.guest_troops and nation_id in province.guest_troops:
                gf = province.guest_troops[nation_id]
                s = gf.get("soldiers", 0)
                a_count = gf.get("aircraft", 0)
                if s > 0 or a_count > 0:
                    owner_name = self.world.nations.get(province.owner_id, {})
                    owner_name = owner_name.name if hasattr(owner_name, "name") else "Unknown"
                    guest_locs.append(f"{p_id} ({s}S/{a_count}A in {owner_name})")

        if guest_locs:
            lines.append(f"\n**EXPEDITIONARY FORCES (Guest):** {', '.join(guest_locs)}")
            lines.append("  → These troops are stationed in Allied territory. You can move them.")

        return "\n".join(lines)

    def _generate_border_defense(self, nation_id: str) -> str:
        """Analyze defense strength at each border with neighbors."""
        neighbors = self.spatial.get_neighboring_nations(nation_id)
        if not neighbors:
            return ""

        border_provinces = self.spatial.get_border_provinces(nation_id)
        neighbor_analysis: Dict[str, Dict] = {}

        for p_id in border_provinces:
            prov = self.world.provinces[p_id]
            my_forces = prov.soldiers + prov.aircraft

            for n_id in prov.neighbors:
                neighbor_prov = self.world.provinces.get(n_id)
                if neighbor_prov and neighbor_prov.owner_id and neighbor_prov.owner_id != nation_id:
                    enemy_id = neighbor_prov.owner_id
                    if enemy_id not in neighbor_analysis:
                        neighbor_analysis[enemy_id] = {
                            "my_forces": 0, "enemy_forces": 0,
                            "provinces": 0, "enemy_provinces": set()
                        }

                    neighbor_analysis[enemy_id]["my_forces"] += my_forces
                    neighbor_analysis[enemy_id]["provinces"] += 1

                    enemy_forces = neighbor_prov.soldiers + neighbor_prov.aircraft
                    if n_id not in neighbor_analysis[enemy_id]["enemy_provinces"]:
                        neighbor_analysis[enemy_id]["enemy_forces"] += enemy_forces
                        neighbor_analysis[enemy_id]["enemy_provinces"].add(n_id)

        lines = ["## BORDER DEFENSE STATUS"]

        for enemy_id, data in neighbor_analysis.items():
            if enemy_id not in self.world.nations:
                continue
            enemy_name = self.world.nations[enemy_id].name
            my_forces = data["my_forces"]
            enemy_forces = data["enemy_forces"]

            ratio = my_forces / enemy_forces if enemy_forces > 0 else (float('inf') if my_forces > 0 else 1.0)

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

            for n_id in prov.neighbors:
                neighbor_prov = self.world.provinces.get(n_id)
                if neighbor_prov and neighbor_prov.owner_id and neighbor_prov.owner_id != nation_id:
                    enemy_forces = neighbor_prov.soldiers + neighbor_prov.aircraft
                    if enemy_forces > my_defense * 1.5 and enemy_forces >= 50:
                        if neighbor_prov.owner_id not in self.world.nations:
                            continue
                        enemy_name = self.world.nations[neighbor_prov.owner_id].name
                        threats.append({
                            "province_id": p_id, "enemy": enemy_name,
                            "enemy_forces": enemy_forces, "my_defense": my_defense
                        })

        if not threats:
            return ""

        lines = ["## THREAT ASSESSMENT"]
        threats.sort(key=lambda t: t["enemy_forces"] - t["my_defense"], reverse=True)

        for threat in threats[:5]:
            lines.append(
                f"\n**THREAT from {threat['enemy']}:** {threat['enemy_forces']:,} enemy units "
                f"facing only {threat['my_defense']:,} defenders at province {threat['province_id']}"
            )

        if len(threats) > 5:
            lines.append(f"\n... and {len(threats) - 5} additional threat zones")

        return "\n".join(lines)

    def analyze_threats(self, nation_id: str) -> str:
        """Produce a high-level strategic threat analysis."""
        threat_text = self._generate_threat_assessment(nation_id)
        border_text = self._generate_border_defense(nation_id)

        if not threat_text and not border_text:
            return "No immediate external threats detected."

        return f"{threat_text}\n\n{border_text}"

    # -------------------------------------------------------------------------
    # BFS: Find reachable destinations per unit type, respecting terrain/access
    # -------------------------------------------------------------------------

    def _get_reachable_destinations(
        self,
        start_id: int,
        unit_type: UnitType,
        nation_id: str,
    ) -> Dict[str, List[Tuple[int, int]]]:
        """
        BFS from start_id to find all reachable destinations within movement range.

        Returns dict with keys:
          - "ATTACK": [(province_id, from_province_id), ...]  — enemy/neutral border provinces
          - "STATION": [(province_id, from_province_id), ...]  — allied territory
          - "REINFORCE": [(province_id, from_province_id), ...] — own border provinces
          - "EXPAND": [(province_id, from_province_id), ...]   — unowned provinces

        BFS rules (Bug #1 & #2 fixes):
          - VOID terrain is never traversed
          - Unowned provinces (owner_id=None) are not traversable for SOLDIER
          - Allied territory is traversable (MUTUAL_DEFENSE/NON_AGGRESSION)
          - Enemy/neutral territory stops BFS expansion (border only)
        """
        max_range = MOVEMENT_RANGE.get(unit_type, 2)
        results: Dict[str, List[Tuple[int, int]]] = {
            "ATTACK": [], "STATION": [], "REINFORCE": [], "EXPAND": []
        }

        visited: Set[int] = {start_id}
        # Queue: (province_id, distance, last_own_or_allied_province_id)
        queue: deque = deque([(start_id, 0, start_id)])

        border_provinces = set(self.spatial.get_border_provinces(nation_id))

        while queue:
            current_id, dist, last_friendly = queue.popleft()
            if dist >= max_range:
                continue

            prov = self.world.provinces.get(current_id)
            if not prov:
                continue

            for neighbor_id in prov.neighbors:
                if neighbor_id in visited:
                    continue

                n_prov = self.world.provinces.get(neighbor_id)
                if not n_prov:
                    continue

                # Bug #1: Skip VOID terrain for all unit types
                if n_prov.terrain == TerrainType.VOID:
                    visited.add(neighbor_id)
                    continue

                # Terrain constraints per unit type
                if unit_type == UnitType.SOLDIER:
                    if n_prov.terrain == TerrainType.OCEAN:
                        continue  # Soldiers can't cross ocean
                elif unit_type == UnitType.NAVY:
                    if n_prov.terrain != TerrainType.OCEAN:
                        continue  # Navy stays in ocean
                # AIRCRAFT: no terrain restriction

                target_owner = n_prov.owner_id

                # Determine relationship to target territory owner
                rel = self.world.relationship_matrix.get(nation_id, {}).get(target_owner, RelationshipState.PEACE) if target_owner else None
                is_own = target_owner == nation_id
                is_ally = rel in (RelationshipState.MUTUAL_DEFENSE, RelationshipState.NON_AGGRESSION) if rel else False

                if is_own:
                    # Own territory: traverse and categorize
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, dist + 1, neighbor_id))
                    if neighbor_id in border_provinces:
                        results["REINFORCE"].append((neighbor_id, start_id))

                elif is_ally:
                    # Allied territory: can traverse for stationing
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, dist + 1, neighbor_id))
                    results["STATION"].append((neighbor_id, last_friendly))

                elif target_owner is None:
                    # Bug #2: Unowned (neutral, no nation) — expansion target, no traversal for soldiers
                    if unit_type != UnitType.SOLDIER:
                        # Navy/aircraft can skip unowned ocean cells
                        visited.add(neighbor_id)
                        queue.append((neighbor_id, dist + 1, last_friendly))
                    else:
                        # Soldiers can enter unowned land (expansion), but BFS stops here
                        visited.add(neighbor_id)
                        results["EXPAND"].append((neighbor_id, last_friendly))

                else:
                    # Enemy or neutral nation: attack target, BFS stops here
                    visited.add(neighbor_id)
                    results["ATTACK"].append((neighbor_id, last_friendly))

        return results

    # -------------------------------------------------------------------------
    # Intent-Based Strategic Options (Change #8)
    # -------------------------------------------------------------------------

    def _generate_strategic_intentions(self, nation_id: str) -> str:
        """
        Generate intent-based strategic options grouped by purpose:
          ⚔️ Offensive (attack enemies / neutrals)
          🛡️ Support (station in allied territory)
          🏰 Reinforce (strengthen own borders)
          🌍 Expand (claim neutral land)

        Each option includes precomputed JSON parameters to reduce hallucinations.
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return ""

        # Energy check — inform if movement is energy-constrained
        energy_per_soldier_move = MOVEMENT_ENERGY_COST[UnitType.SOLDIER]
        energy_warning = ""
        if nation.total_energy < energy_per_soldier_move * 50:
            energy_warning = (
                f"\n> **LOW ENERGY ({nation.total_energy:.0f}):** "
                f"MOVE_TROOPS costs {energy_per_soldier_move}/unit/province. "
                f"Current energy covers approximately {int(nation.total_energy / max(energy_per_soldier_move, 0.01))} unit-moves.\n"
            )

        # Aggregate options across all provinces with troops
        offensive: Dict[str, List[dict]] = {}   # keyed by enemy nation_id
        support: List[dict] = []
        reinforce: List[dict] = []
        expand: List[dict] = []

        # --- SOLDIER moves (from own land provinces) ---
        for p_id in nation.province_ids:
            prov = self.world.provinces.get(p_id)
            if not prov or prov.soldiers <= 0:
                continue

            available = prov.soldiers
            reachable = self._get_reachable_destinations(p_id, UnitType.SOLDIER, nation_id)

            for target_id, from_id in reachable["ATTACK"]:
                t_prov = self.world.provinces.get(target_id)
                if not t_prov or not t_prov.owner_id:
                    continue
                owner_id = t_prov.owner_id
                if owner_id not in self.world.nations:
                    continue
                defenders = t_prov.soldiers + t_prov.aircraft
                ratio = available / max(1, defenders)
                if owner_id not in offensive:
                    offensive[owner_id] = []
                offensive[owner_id].append({
                    "target_id": target_id,
                    "from_id": p_id,
                    "available": available,
                    "defenders": defenders,
                    "ratio": ratio,
                    "uncontested": defenders == 0,
                })

            for target_id, from_id in reachable["STATION"]:
                t_prov = self.world.provinces.get(target_id)
                if not t_prov:
                    continue
                ally_name = self.world.nations.get(t_prov.owner_id, {})
                ally_name = ally_name.name if hasattr(ally_name, "name") else t_prov.owner_id
                support.append({
                    "target_id": target_id,
                    "from_id": p_id,
                    "available": available,
                    "ally_name": ally_name,
                    "ally_id": t_prov.owner_id,
                    "local_defenders": t_prov.soldiers + t_prov.aircraft,
                })

            for target_id, from_id in reachable["REINFORCE"]:
                t_prov = self.world.provinces.get(target_id)
                if not t_prov:
                    continue
                # Only suggest if target has fewer troops than source
                if t_prov.soldiers + t_prov.aircraft < available:
                    reinforce.append({
                        "target_id": target_id,
                        "from_id": p_id,
                        "available": available,
                        "source_garrison": available, # Note: available is p_prov.soldiers
                        "current_defense": t_prov.soldiers + t_prov.aircraft,
                    })

            for target_id, from_id in reachable["EXPAND"]:
                t_prov = self.world.provinces.get(target_id)
                if not t_prov:
                    continue
                expand.append({
                    "target_id": target_id,
                    "from_id": p_id,
                    "available": available,
                })

        # --- NAVY moves (from territorial water provinces — Bug #3 fix) ---
        navy_options: List[str] = []
        for water_id in nation.territorial_water_ids:
            prov = self.world.provinces.get(water_id)
            if not prov or prov.navy <= 0:
                continue
            reachable = self._get_reachable_destinations(water_id, UnitType.NAVY, nation_id)
            for target_id, from_id in reachable["ATTACK"][:3]:
                t_prov = self.world.provinces.get(target_id)
                if t_prov:
                    navy_options.append(
                        f"  → MOVE_TROOPS source={water_id}, target={target_id}, "
                        f"unit_type=NAVY, quantity={prov.navy}"
                    )

        # --- AIRCRAFT moves ---
        air_options: List[str] = []
        for p_id in nation.province_ids:
            prov = self.world.provinces.get(p_id)
            if not prov or prov.aircraft <= 0:
                continue
            reachable = self._get_reachable_destinations(p_id, UnitType.AIRCRAFT, nation_id)
            for target_id, from_id in reachable["ATTACK"][:3]:
                t_prov = self.world.provinces.get(target_id)
                if not t_prov:
                    continue
                defenders = t_prov.soldiers + t_prov.aircraft
                # Do not suggest air strikes on provinces with no military presence:
                # aircraft cannot conquer territory and a strike on 0 defenders has no effect.
                if defenders == 0:
                    continue
                # Cap suggested aircraft at 50% of available to preserve a reserve.
                suggested_aircraft = max(1, prov.aircraft // 2)
                air_options.append(
                    f"  Province {target_id} ({t_prov.owner_id}, {defenders} defenders)"
                    f" → MOVE_TROOPS source={p_id}, target={target_id}, "
                    f"unit_type=AIRCRAFT, quantity={suggested_aircraft}"
                )

        # ---- Build the prompt sections ----
        lines = [f"## STRATEGIC OPTIONS{energy_warning}"]
        lines.append(
            "_Listed options reflect reachable provinces based on current troop positions and movement range. "
            "Province IDs not listed below are not reachable this turn._"
        )

        # ⚔️ OFFENSIVE
        if offensive:
            lines.append("\n### ⚔️ OFFENSIVE OPTIONS")
            for enemy_id, options in offensive.items():
                if enemy_id not in self.world.nations:
                    continue
                enemy_name = self.world.nations[enemy_id].name
                rel_str = self.world.relationship_matrix.get(nation_id, {}).get(enemy_id, RelationshipState.PEACE)
                rel_label = rel_str.value if hasattr(rel_str, "value") else str(rel_str)

                lines.append(f"\n**{enemy_name} ({enemy_id})** — Relation: {rel_label}")

                options.sort(key=lambda o: (not o["uncontested"], -o["ratio"]))
                for opt in options[:3]:
                    # Bug #4 fix: include available troops in description — neutral factual label
                    if opt["uncontested"]:
                        tag = f"0 defenders"
                    else:
                        tag = f"{opt['defenders']} defenders, force ratio {opt['ratio']:.1f}x"

                    lines.append(
                        f"  - Province {opt['target_id']}: {tag}"
                        f" | {opt['available']} troops at source province {opt['from_id']}\n"
                        f"    → MOVE_TROOPS source={opt['from_id']}, target={opt['target_id']}, "
                        f"unit_type=SOLDIER, quantity={opt['available']}"
                    )
        else:
            lines.append("\n### ⚔️ OFFENSIVE OPTIONS\n  No reachable enemy provinces with available ground forces.")

        # 🛡️ SUPPORT
        if support:
            seen_targets: Set[int] = set()
            lines.append("\n### 🛡️ SUPPORT OPTIONS (Allied Stationing)")
            for opt in support[:4]:
                if opt["target_id"] in seen_targets:
                    continue
                seen_targets.add(opt["target_id"])
                lines.append(
                    f"  - Province {opt['target_id']} ({opt['ally_name']}, {opt['ally_id']}): "
                    f"{opt['local_defenders']} local defenders\n"
                    f"    → MOVE_TROOPS source={opt['from_id']}, target={opt['target_id']}, "
                    f"unit_type=SOLDIER, quantity={min(opt['available'], 100)}"
                )

        # 🏰 REINFORCE
        if reinforce:
            reinforce.sort(key=lambda r: r["current_defense"])
            lines.append("\n### 🏰 REINFORCE OPTIONS (Own Border)")
            seen_reinforce: Set[int] = set()
            for opt in reinforce[:4]:
                if opt["target_id"] in seen_reinforce:
                    continue
                seen_reinforce.add(opt["target_id"])
                lines.append(
                    f"  - Border province {opt['target_id']}: {opt['current_defense']} troops currently\n"
                    f"    → MOVE_TROOPS source={opt['from_id']} (has {opt['source_garrison']} troops), target={opt['target_id']}, "
                    f"unit_type=SOLDIER, quantity={min(opt['available'], 100)}"
                )

        # 🌍 EXPAND
        if expand:
            lines.append("\n### 🌍 EXPANSION OPTIONS (Unowned Territory)")
            seen_expand: Set[int] = set()
            for opt in expand[:3]:
                if opt["target_id"] in seen_expand:
                    continue
                seen_expand.add(opt["target_id"])
                lines.append(
                    f"  - Province {opt['target_id']}: unowned, 0 defenders\n"
                    f"    → MOVE_TROOPS source={opt['from_id']}, target={opt['target_id']}, "
                    f"unit_type=SOLDIER, quantity={min(opt['available'], 50)}"
                )

        # ✈️ AIR
        if air_options:
            lines.append("\n### ✈️ AIR STRIKE OPTIONS")
            for opt in air_options[:3]:
                lines.append(f"  - {opt}")

        # ⚓ NAVAL
        if navy_options:
            lines.append("\n### ⚓ NAVAL OPTIONS")
            for opt in navy_options[:3]:
                lines.append(f"  - {opt}")

        # 🛠️ CREATE UNIT SUGGESTIONS (to prevent accumulation in fortified borders)
        # Find weakest border provinces to suggest for CREATE_UNIT
        weakest_borders = []
        border_list = list(self.spatial.get_border_provinces(nation_id))
        for p_id in border_list:
            prov = self.world.provinces.get(p_id)
            if prov:
                weakest_borders.append((p_id, prov.soldiers + prov.aircraft))
        
        weakest_borders.sort(key=lambda x: x[1])
        if weakest_borders:
            lines.append("\n### 🛠️ CREATE UNIT OPTIONS (Prioritize Weak Borders)")
            for p_id, troops in weakest_borders[:3]:
                lines.append(
                    f"  - Border province {p_id}: {troops} troops currently\n"
                    f"    → CREATE_UNIT target_province_id={p_id}, unit_type=SOLDIER"
                )

        if not any([offensive, support, reinforce, expand, air_options, navy_options, weakest_borders]):
            lines.append("\n_No military moves available this turn._")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Legacy helpers (still used by DefenseInputBuilder._build_strategic_assessment)
    # -------------------------------------------------------------------------

    def _generate_military_options(self, nation_id: str) -> str:
        """
        Legacy method: kept for compatibility.
        Produces a compact attack/reinforce summary used by analyze_threats().
        """
        nation = self.world.nations[nation_id]
        border_provinces = self.spatial.get_border_provinces(nation_id)

        attack_options = []
        reinforce_needs = []

        for p_id in border_provinces:
            prov = self.world.provinces[p_id]
            my_forces = prov.soldiers + prov.aircraft

            for n_id in prov.neighbors:
                neighbor_prov = self.world.provinces.get(n_id)
                # Bug #6 fix: removed dead-code `if neighbor_prov.owner_id is None: continue`
                if not neighbor_prov or not neighbor_prov.owner_id or neighbor_prov.owner_id == nation_id:
                    continue
                if neighbor_prov.owner_id not in self.world.nations:
                    continue

                enemy_forces = neighbor_prov.soldiers + neighbor_prov.aircraft
                enemy_name = self.world.nations[neighbor_prov.owner_id].name

                if my_forces >= enemy_forces * 1.5 and my_forces >= 50:
                    attack_options.append({
                        "target_id": n_id, "enemy": enemy_name,
                        "enemy_forces": enemy_forces, "my_forces": my_forces,
                        "from_province": p_id
                    })

                if enemy_forces > my_forces * 1.5 and my_forces < 100:
                    reinforce_needs.append({
                        "province_id": p_id, "current_forces": my_forces,
                        "enemy_threat": enemy_forces
                    })

        lines = []

        if attack_options:
            lines.append("## ATTACK OPTIONS")
            attack_options.sort(key=lambda a: a["my_forces"] / max(a["enemy_forces"], 1), reverse=True)
            for opt in attack_options[:3]:
                ratio = opt["my_forces"] / max(opt["enemy_forces"], 1)
                lines.append(
                    f"\n**Target {opt['enemy']}** (province {opt['target_id']}): "
                    f"You have {ratio:.1f}x advantage ({opt['my_forces']:,} vs {opt['enemy_forces']:,})"
                )

        if reinforce_needs:
            lines.append("\n## REINFORCEMENT PRIORITIES")
            reinforce_needs.sort(key=lambda r: r["enemy_threat"], reverse=True)
            for need in reinforce_needs[:3]:
                lines.append(
                    f"\n**Province {need['province_id']}** needs reinforcement: "
                    f"only {need['current_forces']:,} troops vs {need['enemy_threat']:,} enemy threat"
                )

        recruit_lines = self._generate_recruitment_advice(nation_id, nation)
        if recruit_lines:
            lines.append(recruit_lines)

        if not lines:
            lines.append("## MILITARY STATUS\n\nNo immediate attack options or reinforcement priorities.")

        return "\n".join(lines)

    def _generate_recruitment_advice(self, nation_id: str, nation) -> str:
        """Suggest unit recruitment when army is weak or lacking specific unit types."""
        lines = []

        total_enemy_force = 0
        neighbors = self.spatial.get_neighboring_nations(nation_id)
        for neighbor_id in neighbors:
            if neighbor_id not in self.world.nations:
                continue
            n = self.world.nations[neighbor_id]
            total_enemy_force += n.total_soldiers + n.total_aircraft + n.total_navy

        my_total = nation.total_soldiers + nation.total_aircraft + nation.total_navy
        needs_troops = my_total < total_enemy_force * 0.8 if total_enemy_force > 0 else my_total < 50
        has_ocean = len(nation.territorial_water_ids) > 0
        needs_navy = has_ocean and nation.total_navy == 0
        needs_aircraft = nation.total_aircraft == 0 and nation.total_budget >= 80

        land_provinces = [
            p_id for p_id in nation.province_ids
            if p_id in self.world.provinces and
            self.world.provinces[p_id].terrain.value != "ocean"
        ]

        if needs_troops or needs_navy or needs_aircraft:
            lines.append("\n## RECRUITMENT ADVICE")
            lines.append("Use **CREATE_UNIT** to build more military strength:")

            if needs_troops:
                spawn_at = land_provinces[0] if land_provinces else "?"
                lines.append(
                    f"- **SOLDIER**: Your army ({my_total:,}) is weak vs. neighbors ({total_enemy_force:,}). "
                    f"Recruit at province {spawn_at}."
                )

            if needs_navy:
                water_ids = list(nation.territorial_water_ids)[:3]
                lines.append(
                    f"- **NAVY**: You have ocean access but 0 ships! "
                    f"Create NAVY at territorial waters: {', '.join(str(w) for w in water_ids)}."
                )

            if needs_aircraft:
                spawn_at = land_provinces[0] if land_provinces else "?"
                lines.append(
                    f"- **AIRCRAFT**: No air force. Aircraft can strike ANY province. "
                    f"Create at province {spawn_at}."
                )

        return "\n".join(lines)
