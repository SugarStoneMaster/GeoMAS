"""
Realistic Token Budget Tests.

Simulates multi-turn gameplay with populated ContextManager to verify
token budget under realistic conditions.
"""

import pytest
from geomas.world import generate_world
from geomas.agents.context.tokens import TokenCounter, validate_prompt_budget
from geomas.agents.context.system import (
    PresidentSystemPrompt,
    DefenseSystemPrompt,
    EconomySystemPrompt,
    ForeignSystemPrompt,
    OpinionSystemPrompt,
)
from geomas.agents.context.input import (
    PresidentInputBuilder,
    DefenseInputBuilder,
    EconomyInputBuilder,
    ForeignInputBuilder,
    OpinionInputBuilder,
)
from geomas.agents.context.events import (
    ContextManager,
    NotableEvent,
    MyAction,
    EventType,
)
from geomas.agents.schemas import GlobalStrategy


class TestRealisticTokenBudget:
    """
    Tests with realistic multi-turn simulation data.
    
    These tests populate the ContextManager with events, actions,
    and relationship changes to simulate a real game state.
    """
    
    TOTAL_BUDGET = 5000
    
    @pytest.fixture
    def counter(self):
        return TokenCounter()
    
    @pytest.fixture
    def world(self):
        return generate_world(seed=42, history_seed=99, n_cells=200, n_nations=6)
    
    @pytest.fixture
    def populated_context_manager(self, world):
        """
        Create a ContextManager populated with 30 turns of simulated history.
        
        This represents a mid-game scenario with:
        - 6 nations with evolving relationships
        - ~25 notable events
        - ~30 actions per nation
        """
        cm = ContextManager()
        cm.initialize_from_world(world)
        
        nation_ids = list(world.nations.keys())
        
        # Simulate 30 turns of events
        events = [
            # Early game - diplomacy
            NotableEvent(turn=3, event_type=EventType.ALLIANCE_FORMED,
                        actors=[nation_ids[0], nation_ids[1]],
                        summary=f"{world.nations[nation_ids[0]].name} and {world.nations[nation_ids[1]].name} formed alliance"),
            NotableEvent(turn=5, event_type=EventType.TRADE_DEAL,
                        actors=[nation_ids[0], nation_ids[2]],
                        summary=f"Trade deal: {world.nations[nation_ids[0]].name} and {world.nations[nation_ids[2]].name}"),
            
            # Mid-game - tensions
            NotableEvent(turn=10, event_type=EventType.WAR_DECLARED,
                        actors=[nation_ids[3], nation_ids[4]],
                        summary=f"{world.nations[nation_ids[3]].name} declared war on {world.nations[nation_ids[4]].name}"),
            NotableEvent(turn=12, event_type=EventType.ATTACK,
                        actors=[nation_ids[3], nation_ids[4]],
                        summary=f"{world.nations[nation_ids[3]].name} attacked {world.nations[nation_ids[4]].name}'s border"),
            NotableEvent(turn=15, event_type=EventType.TERRITORY_GAINED,
                        actors=[nation_ids[3], nation_ids[4]],
                        summary=f"{world.nations[nation_ids[3]].name} captured province from {world.nations[nation_ids[4]].name}"),
            
            # War spreading
            NotableEvent(turn=18, event_type=EventType.WAR_DECLARED,
                        actors=[nation_ids[0], nation_ids[3]],
                        summary=f"{world.nations[nation_ids[0]].name} declared war on {world.nations[nation_ids[3]].name}"),
            NotableEvent(turn=20, event_type=EventType.ALLIANCE_FORMED,
                        actors=[nation_ids[4], nation_ids[5]],
                        summary=f"Defensive alliance: {world.nations[nation_ids[4]].name} and {world.nations[nation_ids[5]].name}"),
            
            # Recent events
            NotableEvent(turn=25, event_type=EventType.ATTACK,
                        actors=[nation_ids[0], nation_ids[3]],
                        summary=f"Major offensive by {world.nations[nation_ids[0]].name}"),
            NotableEvent(turn=27, event_type=EventType.TERRITORY_LOST,
                        actors=[nation_ids[3]],
                        summary=f"{world.nations[nation_ids[3]].name} lost 2 provinces",
                        relevance_to=[nation_ids[3]]),
            NotableEvent(turn=28, event_type=EventType.ECONOMIC_CRISIS,
                        actors=[nation_ids[4]],
                        summary=f"Economic crisis in {world.nations[nation_ids[4]].name}",
                        relevance_to=[nation_ids[4]]),
            NotableEvent(turn=30, event_type=EventType.PEACE_SIGNED,
                        actors=[nation_ids[3], nation_ids[4]],
                        summary=f"Peace treaty: {world.nations[nation_ids[3]].name} and {world.nations[nation_ids[4]].name}"),
        ]
        cm.global_events = events
        
        # Add actions for each nation
        for nation_id in nation_ids:
            cm.nation_actions[nation_id] = []
            
            # Defense actions
            for t in range(5, 30, 3):
                cm.nation_actions[nation_id].append(MyAction(
                    turn=t, domain="Defense", action_type="MOVE_TROOPS",
                    action_summary=f"Reinforced northern border with 500 soldiers",
                    outcome=None
                ))
            
            # Economy actions
            for t in range(4, 30, 5):
                cm.nation_actions[nation_id].append(MyAction(
                    turn=t, domain="Economy", action_type="INVEST_IN_WELFARE",
                    action_summary=f"Invested 200 in public welfare programs",
                    outcome="Satisfaction +5"
                ))
            
            # Foreign actions
            for t in range(6, 30, 7):
                cm.nation_actions[nation_id].append(MyAction(
                    turn=t, domain="Foreign", action_type="PROPOSE_TRADE",
                    action_summary=f"Proposed trade deal with neighbor",
                    outcome="Accepted" if t % 2 == 0 else "Rejected"
                ))
        
        # Update some relationships to reflect the history
        for nation_id in nation_ids[:3]:
            for other_id in nation_ids[3:]:
                if nation_id in cm.relationship_summaries:
                    if other_id in cm.relationship_summaries[nation_id]:
                        summary = cm.relationship_summaries[nation_id][other_id]
                        summary.trust = 25.0  # Low trust
                        summary.trust_trend = "↓"
                        summary.notable_events = [
                            "T10: War declared nearby",
                            "T18: Hostile actions observed",
                            "T25: Border tensions"
                        ]
        
        return cm
    
    def _build_full_agent_context(
        self,
        agent_type: str,
        world,
        nation_id: str,
        context_manager: ContextManager
    ) -> tuple[str, str]:
        """Build complete system + input prompt for an agent."""
        nation = world.nations[nation_id]
        strategy = GlobalStrategy.COALITION_BUILDER
        
        # Get events data from ContextManager
        relationships = context_manager.get_relationships_for(nation_id)
        events = context_manager.get_events_for(nation_id, current_turn=world.turn, max_events=15)
        
        # Format events sections
        relationships_text = "\n".join(f"- {r}" for r in relationships) if relationships else "No data"
        events_text = "\n".join(events) if events else "No recent events"
        
        if agent_type == "President":
            system = PresidentSystemPrompt.generate(nation.name, strategy)
            
            # Get minister summaries from other input builders
            defense_input = DefenseInputBuilder(world).build(nation_id, turn=30)
            economy_input = EconomyInputBuilder(world).build(nation_id, turn=30)
            foreign_input = ForeignInputBuilder(world).build(nation_id, turn=30)
            
            # Create summarized versions (first 200 chars each as "briefing")
            defense_summary = defense_input[:200] + "..."
            economy_summary = economy_input[:200] + "..."
            foreign_summary = foreign_input[:200] + "..."
            
            base_input = PresidentInputBuilder(world).build(
                nation_id,
                turn=30,
                defense_summary=defense_summary,
                economy_summary=economy_summary,
                foreign_summary=foreign_summary
            )
            
            actions = context_manager.get_actions_for(nation_id, max_actions=10)
            actions_text = "\n".join(actions) if actions else "No recent actions"
            
            user = f"""{base_input}

== RELATIONSHIPS ==
{relationships_text}

== RECENT WORLD EVENTS ==
{events_text}

== YOUR RECENT ACTIONS ==
{actions_text}"""
            
        elif agent_type == "Defense":
            system = DefenseSystemPrompt.generate(nation.name, strategy)
            base_input = DefenseInputBuilder(world).build(nation_id, turn=30)
            
            actions = context_manager.get_actions_for(nation_id, domain="Defense", max_actions=10)
            actions_text = "\n".join(actions) if actions else "No recent defense actions"
            
            # Filter military-relevant events
            military_events = [e for e in events if any(x in e.lower() for x in ["attack", "war", "territory", "offensive"])]
            military_events_text = "\n".join(military_events[:10]) if military_events else "No military events"
            
            user = f"""{base_input}

== RECENT MILITARY EVENTS ==
{military_events_text}

== YOUR RECENT DEFENSE ACTIONS ==
{actions_text}"""
            
        elif agent_type == "Economy":
            system = EconomySystemPrompt.generate(nation.name, strategy)
            base_input = EconomyInputBuilder(world).build(nation_id, turn=30)
            
            actions = context_manager.get_actions_for(nation_id, domain="Economy", max_actions=10)
            actions_text = "\n".join(actions) if actions else "No recent economy actions"
            
            user = f"""{base_input}

== TRADE RELATIONSHIPS ==
{relationships_text}

== YOUR RECENT ECONOMY ACTIONS ==
{actions_text}"""
            
        elif agent_type == "Foreign":
            system = ForeignSystemPrompt.generate(nation.name, strategy)
            base_input = ForeignInputBuilder(world).build(nation_id, turn=30)
            
            actions = context_manager.get_actions_for(nation_id, domain="Foreign", max_actions=10)
            actions_text = "\n".join(actions) if actions else "No recent foreign actions"
            
            user = f"""{base_input}

== FULL RELATIONSHIP STATUS ==
{relationships_text}

== RECENT DIPLOMATIC EVENTS ==
{events_text}

== YOUR RECENT FOREIGN ACTIONS ==
{actions_text}"""
            
        else:  # Opinion
            system = OpinionSystemPrompt.generate(nation.name)
            base_input = OpinionInputBuilder(world).build(nation_id, turn=30)
            
            user = f"""{base_input}

== WHAT THE PEOPLE KNOW ==
{events_text}"""
        
        return system, user
    
    def test_president_realistic_mid_game(self, counter, world, populated_context_manager):
        """President prompt at turn 30 with full context stays under budget."""
        nation_id = list(world.nations.keys())[0]
        
        system, user = self._build_full_agent_context(
            "President", world, nation_id, populated_context_manager
        )
        
        is_valid, details = counter.validate_budget(system, user, self.TOTAL_BUDGET)
        
        print(f"\nPresident (Turn 30 realistic):")
        print(f"  System: {details['system_tokens']} tokens")
        print(f"  User: {details['user_tokens']} tokens")
        print(f"  Total: {details['total_tokens']} tokens ({details['utilization_percent']:.0f}%)")
        
        assert is_valid, f"President prompt exceeds budget: {details['total_tokens']}"
    
    def test_defense_realistic_mid_game(self, counter, world, populated_context_manager):
        """Defense prompt at turn 30 with full context stays under budget."""
        nation_id = list(world.nations.keys())[0]
        
        system, user = self._build_full_agent_context(
            "Defense", world, nation_id, populated_context_manager
        )
        
        is_valid, details = counter.validate_budget(system, user, self.TOTAL_BUDGET)
        
        print(f"\nDefense (Turn 30 realistic):")
        print(f"  System: {details['system_tokens']} tokens")
        print(f"  User: {details['user_tokens']} tokens")
        print(f"  Total: {details['total_tokens']} tokens ({details['utilization_percent']:.0f}%)")
        
        assert is_valid, f"Defense prompt exceeds budget: {details['total_tokens']}"
    
    def test_economy_realistic_mid_game(self, counter, world, populated_context_manager):
        """Economy prompt at turn 30 with full context stays under budget."""
        nation_id = list(world.nations.keys())[0]
        
        system, user = self._build_full_agent_context(
            "Economy", world, nation_id, populated_context_manager
        )
        
        is_valid, details = counter.validate_budget(system, user, self.TOTAL_BUDGET)
        
        print(f"\nEconomy (Turn 30 realistic):")
        print(f"  System: {details['system_tokens']} tokens")
        print(f"  User: {details['user_tokens']} tokens")
        print(f"  Total: {details['total_tokens']} tokens ({details['utilization_percent']:.0f}%)")
        
        assert is_valid, f"Economy prompt exceeds budget: {details['total_tokens']}"
    
    def test_foreign_realistic_mid_game(self, counter, world, populated_context_manager):
        """Foreign prompt at turn 30 with full context stays under budget."""
        nation_id = list(world.nations.keys())[0]
        
        system, user = self._build_full_agent_context(
            "Foreign", world, nation_id, populated_context_manager
        )
        
        is_valid, details = counter.validate_budget(system, user, self.TOTAL_BUDGET)
        
        print(f"\nForeign (Turn 30 realistic):")
        print(f"  System: {details['system_tokens']} tokens")
        print(f"  User: {details['user_tokens']} tokens")
        print(f"  Total: {details['total_tokens']} tokens ({details['utilization_percent']:.0f}%)")
        
        assert is_valid, f"Foreign prompt exceeds budget: {details['total_tokens']}"
    
    def test_opinion_realistic_mid_game(self, counter, world, populated_context_manager):
        """Opinion prompt at turn 30 with full context stays under budget."""
        nation_id = list(world.nations.keys())[0]
        
        system, user = self._build_full_agent_context(
            "Opinion", world, nation_id, populated_context_manager
        )
        
        is_valid, details = counter.validate_budget(system, user, self.TOTAL_BUDGET)
        
        print(f"\nOpinion (Turn 30 realistic):")
        print(f"  System: {details['system_tokens']} tokens")
        print(f"  User: {details['user_tokens']} tokens")
        print(f"  Total: {details['total_tokens']} tokens ({details['utilization_percent']:.0f}%)")
        
        assert is_valid, f"Opinion prompt exceeds budget: {details['total_tokens']}"
    
    def test_all_agents_all_nations_realistic(self, counter, world, populated_context_manager):
        """All agents for all nations stay under budget."""
        agents = ["President", "Defense", "Economy", "Foreign", "Opinion"]
        results = []
        max_seen = 0
        max_agent = ""
        max_nation = ""
        
        for nation_id in list(world.nations.keys())[:4]:  # Test first 4 nations
            nation_name = world.nations[nation_id].name
            for agent in agents:
                system, user = self._build_full_agent_context(
                    agent, world, nation_id, populated_context_manager
                )
                is_valid, details = counter.validate_budget(system, user, self.TOTAL_BUDGET)
                
                results.append({
                    "nation": nation_name,
                    "agent": agent,
                    "tokens": details['total_tokens'],
                    "valid": is_valid
                })
                
                if details['total_tokens'] > max_seen:
                    max_seen = details['total_tokens']
                    max_agent = agent
                    max_nation = nation_name
        
        print(f"\n=== ALL AGENTS REALISTIC TEST ===")
        print(f"Tested: {len(results)} agent/nation combinations")
        print(f"Max tokens: {max_seen} ({max_agent} for {max_nation})")
        print(f"All valid: {all(r['valid'] for r in results)}")
        
        # Show distribution
        token_ranges = {
            "< 1000": len([r for r in results if r['tokens'] < 1000]),
            "1000-2000": len([r for r in results if 1000 <= r['tokens'] < 2000]),
            "2000-3000": len([r for r in results if 2000 <= r['tokens'] < 3000]),
            "3000-4000": len([r for r in results if 3000 <= r['tokens'] < 4000]),
            "4000-5000": len([r for r in results if 4000 <= r['tokens'] < 5000]),
        }
        print(f"Distribution: {token_ranges}")
        
        assert all(r['valid'] for r in results), "Some agents exceeded budget"
    
    def test_print_sample_prompt(self, world, populated_context_manager):
        """Print a sample prompt for manual inspection."""
        nation_id = list(world.nations.keys())[0]
        
        system, user = self._build_full_agent_context(
            "Defense", world, nation_id, populated_context_manager
        )
        
        print("\n" + "="*60)
        print("SAMPLE DEFENSE MINISTER PROMPT")
        print("="*60)
        print("\n--- SYSTEM PROMPT ---")
        print(system[:500] + "..." if len(system) > 500 else system)
        print("\n--- USER PROMPT ---")
        print(user[:1500] + "..." if len(user) > 1500 else user)
        print("="*60)
