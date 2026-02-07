"""
Stress Tests for Token Budget.

Tests that verify token budget remains within limits under extreme conditions:
- Maximum number of nations (20)
- Maximum events (50, pruned)
- Maximum actions (30 per nation)
- Full relationship history
"""

import pytest
from geomas.world import generate_world
from geomas.agents.context.tokens import TokenCounter
from geomas.agents.context.memory import ContextManager, NotableEvent, MyAction, EventType
from geomas.agents.context.system import ForeignSystemPrompt, DefenseSystemPrompt
from geomas.agents.context.input import ForeignInputBuilder, DefenseInputBuilder
from geomas.agents.schemas import GlobalStrategy


class TestStressBudget:
    """Stress tests for token budget under extreme simulation conditions."""
    
    TOTAL_BUDGET = 5000
    
    @pytest.fixture
    def counter(self):
        return TokenCounter()
    
    def _populate_context_manager(self, world, cm):
        """Populate ContextManager with maximum simulation data."""
        nation_ids = list(world.nations.keys())
        nation_id = nation_ids[0]
        
        # Populate ALL relationships with full history
        for other_id in nation_ids[1:]:
            if other_id in cm.relationship_summaries[nation_id]:
                summary = cm.relationship_summaries[nation_id][other_id]
                summary.trust = 25
                summary.trust_trend = "↓"
                summary.last_interaction_turn = 95
                summary.last_interaction_summary = "Recent military conflict with casualties"
                summary.notable_events = [
                    "T20: Broke non-aggression pact",
                    "T50: Major battle with territory loss",
                    "T90: Continued hostilities"
                ]
        
        # Add maximum events (50 = CM.MAX_EVENTS)
        for i in range(60):  # More than max to test pruning
            cm.global_events.append(NotableEvent(
                turn=i*2,
                event_type=EventType.WAR_DECLARED if i < 10 else EventType.ATTACK,
                actors=[nation_ids[i % len(nation_ids)], nation_ids[(i+1) % len(nation_ids)]],
                summary=f"{world.nations[nation_ids[i % len(nation_ids)]].name} launched offensive"
            ))
        
        # Add maximum actions per nation (10 per domain = 30 total)
        for n_id in nation_ids:
            cm.nation_actions[n_id] = []
            for domain in ["Defense", "Economy", "Foreign"]:
                for t in range(15):  # More than max to test pruning
                    cm.nation_actions[n_id].append(MyAction(
                        turn=t*5,
                        domain=domain,
                        action_type=f"{domain.upper()}_ACTION",
                        action_summary=f"Major {domain.lower()} operation at border",
                        outcome="Success" if t % 2 == 0 else "Failed"
                    ))
        
        # Trigger pruning
        cm._prune_if_needed()
        
        return nation_id
    
    def _build_full_context(self, world, cm, nation_id, agent_type="Foreign"):
        """Build complete context with all memory data."""
        relationships = cm.get_relationships_for(nation_id)
        events = cm.get_events_for(nation_id, max_events=25)
        actions = cm.get_actions_for(nation_id, max_actions=30)
        
        rel_text = "\n".join(f"- {r}" for r in relationships)
        evt_text = "\n".join(events)
        act_text = "\n".join(actions)
        
        if agent_type == "Foreign":
            system = ForeignSystemPrompt.generate(
                world.nations[nation_id].name, 
                GlobalStrategy.TOTAL_EXPANSIONISM
            )
            base = ForeignInputBuilder(world).build(nation_id, turn=0)
        else:
            system = DefenseSystemPrompt.generate(
                world.nations[nation_id].name,
                GlobalStrategy.TOTAL_EXPANSIONISM
            )
            base = DefenseInputBuilder(world).build(nation_id, turn=0)
        
        user = f"""{base}

== RELATIONSHIPS ({len(relationships)} nations) ==
{rel_text}

== RECENT EVENTS ({len(events)} events) ==
{evt_text}

== RECENT ACTIONS ({len(actions)} actions) ==
{act_text}"""
        
        return system, user
    
    @pytest.mark.parametrize("n_nations", [6, 10, 15, 20])
    def test_scaling_by_nation_count(self, counter, n_nations):
        """Token budget scales safely with nation count."""
        world = generate_world(
            seed=42, history_seed=99, 
            n_cells=n_nations*30, n_nations=n_nations
        )
        
        cm = ContextManager()
        cm.initialize_from_world(world)
        nation_id = self._populate_context_manager(world, cm)
        
        system, user = self._build_full_context(world, cm, nation_id)
        
        is_valid, details = counter.validate_budget(system, user, self.TOTAL_BUDGET)
        
        print(f"\n{n_nations} nations: {details['total_tokens']} tokens ({details['utilization_percent']:.0f}%)")
        
        assert is_valid, f"Budget exceeded with {n_nations} nations: {details['total_tokens']}"
        assert details['utilization_percent'] < 80, f"Too high utilization: {details['utilization_percent']:.0f}%"
    
    def test_worst_case_20_nations(self, counter):
        """Worst case with 20 nations stays well under budget."""
        world = generate_world(seed=42, history_seed=99, n_cells=600, n_nations=20)
        
        cm = ContextManager()
        cm.initialize_from_world(world)
        nation_id = self._populate_context_manager(world, cm)
        
        system, user = self._build_full_context(world, cm, nation_id)
        
        is_valid, details = counter.validate_budget(system, user, self.TOTAL_BUDGET)
        
        print(f"\nWorst case (20 nations):")
        print(f"  System: {details['system_tokens']} tokens")
        print(f"  User: {details['user_tokens']} tokens")
        print(f"  Total: {details['total_tokens']} tokens ({details['utilization_percent']:.0f}%)")
        print(f"  Remaining: {details['tokens_remaining']} tokens")
        
        assert is_valid, f"Budget exceeded: {details['total_tokens']}"
        # Should be around 50% or less
        assert details['utilization_percent'] <= 60, f"Utilization too high: {details['utilization_percent']:.0f}%"
    
    def test_pruning_works_correctly(self):
        """Pruning keeps data within limits."""
        world = generate_world(seed=42, history_seed=99, n_cells=180, n_nations=6)
        
        cm = ContextManager()
        cm.initialize_from_world(world)
        nation_id = list(world.nations.keys())[0]
        
        # Add way more than max
        for i in range(100):
            cm.global_events.append(NotableEvent(
                turn=i, event_type=EventType.TRADE_DEAL,
                actors=[nation_id], summary=f"Event {i}"
            ))
        
        cm.nation_actions[nation_id] = []
        for t in range(50):
            cm.nation_actions[nation_id].append(MyAction(
                turn=t, domain="Defense", action_type="TEST",
                action_summary=f"Action {t}", outcome=None
            ))
        
        cm._prune_if_needed()
        
        assert len(cm.global_events) <= cm.MAX_EVENTS
        # Actions pruned per domain (10 per domain)
        defense_actions = [a for a in cm.nation_actions[nation_id] if a.domain == "Defense"]
        assert len(defense_actions) <= cm.MAX_ACTIONS_PER_DOMAIN
    
    def test_token_per_component(self, counter):
        """Verify token counts per component match expectations."""
        # Sample relationship line
        rel_line = "- Valdoria: WAR, Trust 15 (falling). Last: attacked us T24. History: T15: broke treaty; T20: war"
        rel_tokens = counter.count(rel_line)
        assert rel_tokens < 50, f"Relationship line too long: {rel_tokens} tokens"
        
        # Sample event line
        evt_line = "Turn 45: Valdoria launched major offensive against Aquilonia capturing strategic positions"
        evt_tokens = counter.count(evt_line)
        assert evt_tokens < 25, f"Event line too long: {evt_tokens} tokens"
        
        # Sample action line
        act_line = "Turn 24 [Defense]: Reinforced Province 12 border with 500 soldiers → Success"
        act_tokens = counter.count(act_line)
        assert act_tokens < 25, f"Action line too long: {act_tokens} tokens"
        
        print(f"\nComponent token sizes:")
        print(f"  Relationship: {rel_tokens} tokens")
        print(f"  Event: {evt_tokens} tokens")
        print(f"  Action: {act_tokens} tokens")
