"""
Tests for GovernmentType Feature.

Covers:
- GovernmentType enum schema
- Governance-specific intent types (EXPORT_DEMOCRACY, HOLY_WAR, DIVINE_MANDATE)
- System prompt injection (governance context appears, no nudging language)
- Dynamic schema intent restriction per government type
- Engine deterministic assignment
- NationAgent / OpinionAgent constructor wiring
"""

import pytest
from geomas.agents.schemas.protocol import (
    GovernmentType,
    DefenseIntentType,
    ForeignIntentType,
)
from geomas.agents.schemas import GlobalStrategy
from geomas.agents.context.system import (
    DefenseSystemPrompt,
    ForeignSystemPrompt,
    EconomySystemPrompt,
    PresidentSystemPrompt,
)
from geomas.agents.context.system.opinion import OpinionSystemPrompt
from geomas.agents.schemas.dynamic import (
    get_dynamic_proposal_model,
    DEFENSE_INTENTS_BY_GOV,
    FOREIGN_INTENTS_BY_GOV,
)
from geomas.agents.schemas import DefenseProposal, ForeignProposal


# ─────────────────────────────────────────────────────────────────────────────
# 1. Schema Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestGovernmentTypeEnum:
    """GovernmentType enum is correctly defined."""

    def test_three_values_exist(self):
        """Exactly three government types are defined."""
        values = {g.value for g in GovernmentType}
        assert values == {"DEMOCRACY", "AUTHORITARIAN", "THEOCRACY"}

    def test_is_string_enum(self):
        """GovernmentType values are strings (for JSON serialization)."""
        assert isinstance(GovernmentType.DEMOCRACY.value, str)

    def test_governance_intents_in_defense_enum(self):
        """EXPORT_DEMOCRACY and HOLY_WAR are present in DefenseIntentType."""
        assert DefenseIntentType.EXPORT_DEMOCRACY in DefenseIntentType
        assert DefenseIntentType.HOLY_WAR in DefenseIntentType

    def test_governance_intents_in_foreign_enum(self):
        """EXPORT_DEMOCRACY and DIVINE_MANDATE are present in ForeignIntentType."""
        assert ForeignIntentType.EXPORT_DEMOCRACY in ForeignIntentType
        assert ForeignIntentType.DIVINE_MANDATE in ForeignIntentType

    def test_country_envelope_accepts_government_type(self):
        """CountryEnvelope can be created with government_type field."""
        from conftest import create_test_envelope
        env = create_test_envelope("TEST")
        # Default is None
        assert env.government_type is None

    def test_country_envelope_stores_government_type_string(self):
        """CountryEnvelope stores government_type as a string value."""
        from conftest import create_test_envelope
        env = create_test_envelope("TEST")
        env.government_type = GovernmentType.DEMOCRACY.value
        assert env.government_type == "DEMOCRACY"


# ─────────────────────────────────────────────────────────────────────────────
# 2. System Prompt Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestGovernanceSystemPrompts:
    """Governance context is injected into system prompts correctly."""

    # ── President ──────────────────────────────────────────────────────────

    def test_president_without_government_type(self):
        """President prompt works without government_type (backward compat)."""
        prompt = PresidentSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.COALITION_BUILDER
        )
        assert "President" in prompt
        assert "Governance Persona" not in prompt

    def test_president_with_democracy(self):
        """President prompt includes governance persona for DEMOCRACY."""
        prompt = PresidentSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.COALITION_BUILDER,
            government_type=GovernmentType.DEMOCRACY
        )
        assert "Governance Persona" in prompt
        assert "democratic" in prompt.lower() or "freedom" in prompt.lower() or "liberty" in prompt.lower()

    def test_president_with_theocracy(self):
        """President prompt includes governance persona for THEOCRACY."""
        prompt = PresidentSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.COALITION_BUILDER,
            government_type=GovernmentType.THEOCRACY
        )
        assert "Governance Persona" in prompt
        assert "theocratic" in prompt.lower() or "divine" in prompt.lower() or "faith" in prompt.lower()

    def test_president_with_authoritarian(self):
        """President prompt includes governance persona for AUTHORITARIAN."""
        prompt = PresidentSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.TOTAL_EXPANSIONISM,
            government_type=GovernmentType.AUTHORITARIAN
        )
        assert "Governance Persona" in prompt
        assert "authoritarian" in prompt.lower() or "strength" in prompt.lower() or "order" in prompt.lower()

    # ── Defense ────────────────────────────────────────────────────────────

    def test_defense_without_government_type(self):
        """Defense prompt works without government_type (backward compat)."""
        prompt = DefenseSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.ARMED_ISOLATIONISM
        )
        assert "Defense Minister" in prompt
        assert "EXPORT_DEMOCRACY" not in prompt
        assert "HOLY_WAR" not in prompt

    def test_defense_democracy_includes_export_democracy(self):
        """Democracy defense prompt lists EXPORT_DEMOCRACY intent."""
        prompt = DefenseSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.TOTAL_EXPANSIONISM,
            government_type=GovernmentType.DEMOCRACY
        )
        assert "EXPORT_DEMOCRACY" in prompt
        assert "HOLY_WAR" not in prompt

    def test_defense_theocracy_includes_holy_war(self):
        """Theocracy defense prompt lists HOLY_WAR intent."""
        prompt = DefenseSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.TOTAL_EXPANSIONISM,
            government_type=GovernmentType.THEOCRACY
        )
        assert "HOLY_WAR" in prompt
        assert "EXPORT_DEMOCRACY" not in prompt

    def test_defense_authoritarian_has_no_extra_intents(self):
        """Authoritarian defense prompt does NOT list governance-specific intents."""
        prompt = DefenseSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.TOTAL_EXPANSIONISM,
            government_type=GovernmentType.AUTHORITARIAN
        )
        assert "EXPORT_DEMOCRACY" not in prompt
        assert "HOLY_WAR" not in prompt

    def test_defense_governance_context_section_present(self):
        """Defense prompt includes Governance Context section when gov type is set."""
        prompt = DefenseSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.COALITION_BUILDER,
            government_type=GovernmentType.DEMOCRACY
        )
        assert "Governance Context" in prompt

    def test_defense_no_nudging_language(self):
        """Defense prompt does NOT contain prescriptive nudging toward moral washing."""
        for gov in GovernmentType:
            prompt = DefenseSystemPrompt.generate(
                nation_name="Testland",
                strategy=GlobalStrategy.TOTAL_EXPANSIONISM,
                government_type=gov
            )
            # These phrases explicitly instruct moral washing — must not be present
            assert "Use this when the reality is CONQUEST" not in prompt
            assert "but you need democratic legitimacy" not in prompt
            assert "but you need religious legitimacy" not in prompt

    # ── Foreign ────────────────────────────────────────────────────────────

    def test_foreign_without_government_type(self):
        """Foreign prompt works without government_type (backward compat)."""
        prompt = ForeignSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.COALITION_BUILDER
        )
        assert "Foreign Minister" in prompt
        assert "EXPORT_DEMOCRACY" not in prompt
        assert "DIVINE_MANDATE" not in prompt

    def test_foreign_democracy_includes_export_democracy(self):
        """Democracy foreign prompt lists EXPORT_DEMOCRACY intent."""
        prompt = ForeignSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.COALITION_BUILDER,
            government_type=GovernmentType.DEMOCRACY
        )
        assert "EXPORT_DEMOCRACY" in prompt
        assert "DIVINE_MANDATE" not in prompt

    def test_foreign_theocracy_includes_divine_mandate(self):
        """Theocracy foreign prompt lists DIVINE_MANDATE intent."""
        prompt = ForeignSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.COALITION_BUILDER,
            government_type=GovernmentType.THEOCRACY
        )
        assert "DIVINE_MANDATE" in prompt
        assert "EXPORT_DEMOCRACY" not in prompt

    def test_foreign_authoritarian_has_no_extra_intents(self):
        """Authoritarian foreign prompt does NOT list governance-specific intents."""
        prompt = ForeignSystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.COALITION_BUILDER,
            government_type=GovernmentType.AUTHORITARIAN
        )
        assert "EXPORT_DEMOCRACY" not in prompt
        assert "DIVINE_MANDATE" not in prompt

    def test_foreign_no_nudging_language(self):
        """Foreign prompt does NOT contain prescriptive nudging toward moral washing."""
        for gov in GovernmentType:
            prompt = ForeignSystemPrompt.generate(
                nation_name="Testland",
                strategy=GlobalStrategy.COALITION_BUILDER,
                government_type=gov
            )
            assert "Use this when the reality is COERCION" not in prompt
            assert "but you need democratic legitimacy" not in prompt
            assert "but you need religious legitimacy" not in prompt

    # ── Economy & Opinion ──────────────────────────────────────────────────

    def test_economy_includes_governance_context(self):
        """Economy prompt includes Governance Context section when gov type is set."""
        prompt = EconomySystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.COALITION_BUILDER,
            government_type=GovernmentType.DEMOCRACY
        )
        assert "Governance Context" in prompt

    def test_economy_without_government_type(self):
        """Economy prompt works without government_type (backward compat)."""
        prompt = EconomySystemPrompt.generate(
            nation_name="Testland",
            strategy=GlobalStrategy.COALITION_BUILDER
        )
        assert "Economy Minister" in prompt
        assert "Governance Context" not in prompt

    def test_opinion_includes_governance_expectations(self):
        """Opinion prompt includes Governance Expectations when gov type is set."""
        prompt = OpinionSystemPrompt.generate(
            nation_name="Testland",
            government_type=GovernmentType.THEOCRACY
        )
        assert "Governance Expectations" in prompt

    def test_opinion_without_government_type(self):
        """Opinion prompt works without government_type (backward compat)."""
        prompt = OpinionSystemPrompt.generate(nation_name="Testland")
        assert "Governance Expectations" not in prompt


# ─────────────────────────────────────────────────────────────────────────────
# 3. Dynamic Schema Intent Restriction Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestGovernanceIntentPools:
    """Intent pools are correctly defined per government type."""

    def test_democracy_defense_includes_export_democracy(self):
        """Democracy defense pool includes EXPORT_DEMOCRACY."""
        pool = DEFENSE_INTENTS_BY_GOV[GovernmentType.DEMOCRACY]
        assert DefenseIntentType.EXPORT_DEMOCRACY in pool

    def test_democracy_defense_excludes_holy_war(self):
        """Democracy defense pool does NOT include HOLY_WAR."""
        pool = DEFENSE_INTENTS_BY_GOV[GovernmentType.DEMOCRACY]
        assert DefenseIntentType.HOLY_WAR not in pool

    def test_theocracy_defense_includes_holy_war(self):
        """Theocracy defense pool includes HOLY_WAR."""
        pool = DEFENSE_INTENTS_BY_GOV[GovernmentType.THEOCRACY]
        assert DefenseIntentType.HOLY_WAR in pool

    def test_theocracy_defense_excludes_export_democracy(self):
        """Theocracy defense pool does NOT include EXPORT_DEMOCRACY."""
        pool = DEFENSE_INTENTS_BY_GOV[GovernmentType.THEOCRACY]
        assert DefenseIntentType.EXPORT_DEMOCRACY not in pool

    def test_authoritarian_defense_has_only_base_intents(self):
        """Authoritarian defense pool has only base intents (no governance extras)."""
        pool = DEFENSE_INTENTS_BY_GOV[GovernmentType.AUTHORITARIAN]
        assert DefenseIntentType.EXPORT_DEMOCRACY not in pool
        assert DefenseIntentType.HOLY_WAR not in pool
        # Base intents must still be present
        assert DefenseIntentType.CONQUEST in pool
        assert DefenseIntentType.DEFENSE in pool

    def test_democracy_foreign_includes_export_democracy(self):
        """Democracy foreign pool includes EXPORT_DEMOCRACY."""
        pool = FOREIGN_INTENTS_BY_GOV[GovernmentType.DEMOCRACY]
        assert ForeignIntentType.EXPORT_DEMOCRACY in pool

    def test_theocracy_foreign_includes_divine_mandate(self):
        """Theocracy foreign pool includes DIVINE_MANDATE."""
        pool = FOREIGN_INTENTS_BY_GOV[GovernmentType.THEOCRACY]
        assert ForeignIntentType.DIVINE_MANDATE in pool

    def test_authoritarian_foreign_has_only_base_intents(self):
        """Authoritarian foreign pool has only base intents."""
        pool = FOREIGN_INTENTS_BY_GOV[GovernmentType.AUTHORITARIAN]
        assert ForeignIntentType.EXPORT_DEMOCRACY not in pool
        assert ForeignIntentType.DIVINE_MANDATE not in pool
        assert ForeignIntentType.COOPERATION in pool
        assert ForeignIntentType.COERCION in pool

    def test_all_government_types_covered_in_defense(self):
        """All GovernmentType values have a defense intent pool."""
        for gov in GovernmentType:
            assert gov in DEFENSE_INTENTS_BY_GOV

    def test_all_government_types_covered_in_foreign(self):
        """All GovernmentType values have a foreign intent pool."""
        for gov in GovernmentType:
            assert gov in FOREIGN_INTENTS_BY_GOV


class TestDynamicSchemaIntentRestriction:
    """get_dynamic_proposal_model restricts intents correctly per government type."""

    VALID_NATIONS = ["OSTER", "ZENTORA", "KRELL"]

    def test_defense_without_gov_type_no_restriction(self):
        """Without government_type, no intent restriction is applied."""
        model = get_dynamic_proposal_model(DefenseProposal, self.VALID_NATIONS, None)
        # Model should be generated without intent restriction
        assert model is not None

    def test_defense_democracy_model_created(self):
        """Dynamic defense model is created for DEMOCRACY without error."""
        model = get_dynamic_proposal_model(
            DefenseProposal, self.VALID_NATIONS, GovernmentType.DEMOCRACY
        )
        assert model is not None

    def test_defense_theocracy_model_created(self):
        """Dynamic defense model is created for THEOCRACY without error."""
        model = get_dynamic_proposal_model(
            DefenseProposal, self.VALID_NATIONS, GovernmentType.THEOCRACY
        )
        assert model is not None

    def test_defense_authoritarian_model_created(self):
        """Dynamic defense model is created for AUTHORITARIAN without error."""
        model = get_dynamic_proposal_model(
            DefenseProposal, self.VALID_NATIONS, GovernmentType.AUTHORITARIAN
        )
        assert model is not None

    def test_foreign_democracy_model_created(self):
        """Dynamic foreign model is created for DEMOCRACY without error."""
        model = get_dynamic_proposal_model(
            ForeignProposal, self.VALID_NATIONS, GovernmentType.DEMOCRACY
        )
        assert model is not None

    def test_foreign_theocracy_model_created(self):
        """Dynamic foreign model is created for THEOCRACY without error."""
        model = get_dynamic_proposal_model(
            ForeignProposal, self.VALID_NATIONS, GovernmentType.THEOCRACY
        )
        assert model is not None

    def test_democracy_defense_intent_field_includes_export_democracy(self):
        """Democracy dynamic defense model intent field includes EXPORT_DEMOCRACY."""
        model = get_dynamic_proposal_model(
            DefenseProposal, self.VALID_NATIONS, GovernmentType.DEMOCRACY
        )
        # Check the intent field annotation includes EXPORT_DEMOCRACY
        intent_field = model.model_fields.get("intent")
        assert intent_field is not None
        # The annotation should be a DynamicDefenseIntent submodel
        intent_model = intent_field.annotation
        pub_field = intent_model.model_fields.get("public_intent")
        assert pub_field is not None
        # The Literal annotation should include EXPORT_DEMOCRACY
        import typing
        args = typing.get_args(pub_field.annotation)
        assert "EXPORT_DEMOCRACY" in args

    def test_authoritarian_defense_intent_field_excludes_export_democracy(self):
        """Authoritarian dynamic defense model does NOT include EXPORT_DEMOCRACY."""
        model = get_dynamic_proposal_model(
            DefenseProposal, self.VALID_NATIONS, GovernmentType.AUTHORITARIAN
        )
        intent_field = model.model_fields.get("intent")
        intent_model = intent_field.annotation
        pub_field = intent_model.model_fields.get("public_intent")
        import typing
        args = typing.get_args(pub_field.annotation)
        assert "EXPORT_DEMOCRACY" not in args
        assert "HOLY_WAR" not in args


# ─────────────────────────────────────────────────────────────────────────────
# 4. Engine Assignment Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEngineGovernmentTypeAssignment:
    """SimulationEngine assigns GovernmentType deterministically."""

    def _make_engine(self, n_nations: int = 3, seed: int = 42):
        """Helper to create a minimal engine with N nations."""
        from unittest.mock import MagicMock, patch
        from geomas.simulation.engine import SimulationEngine

        # Build a minimal world with N nations
        world = MagicMock()
        nation_ids = [f"N{i}" for i in range(n_nations)]
        nations = {}
        for nid in nation_ids:
            nation = MagicMock()
            nation.name = nid
            nation.cultural_traits = []
            nations[nid] = nation
        world.nations = nations

        engine = SimulationEngine.__new__(SimulationEngine)
        engine.world = world
        engine.map_seed = seed
        engine.client = MagicMock()
        engine.context_manager = None
        engine.agents = {}
        engine.opinion_agents = {}
        engine.simulation_id = 1
        engine.db = None
        
        # Patch calculators to return real numbers, otherwise sorted() fails on MagicMocks
        from unittest.mock import patch
        self.calc_patch = patch("geomas.calculators.analytics.calculate_power_projection", side_effect=lambda n: float(n.name[1:]))
        self.aggr_patch = patch("geomas.calculators.analytics.calculate_nation_aggregates", return_value={
            "total_population": 0, "total_workers": 0, "total_soldiers": 0, 
            "total_aircraft": 0, "total_navy": 0, "total_food_production": 0,
            "total_energy_production": 0, "total_materials_production": 0
        })
        self.calc_patch.start()
        self.aggr_patch.start()

        return engine, nation_ids

    def teardown_method(self, method):
        """Stop patches if they exist."""
        if hasattr(self, 'calc_patch'):
            self.calc_patch.stop()
        if hasattr(self, 'aggr_patch'):
            self.aggr_patch.stop()

    def test_all_nations_get_government_type(self):
        """Every nation gets a government_type after _init_agents."""
        engine, nation_ids = self._make_engine(n_nations=3)

        with pytest.MonkeyPatch().context() as mp:
            # Patch NationAgent to avoid real LLM setup
            from unittest.mock import MagicMock
            mp.setattr(
                "geomas.simulation.engine.NationAgent",
                lambda **kwargs: MagicMock()
            )
            engine._init_agents()

        for nid in nation_ids:
            gov = engine.world.nations[nid].government_type
            assert gov is not None
            assert gov in {g.value for g in GovernmentType}

    def test_assignment_is_deterministic(self):
        """Same seed produces same government type assignment."""
        results = []
        for _ in range(2):
            engine, nation_ids = self._make_engine(n_nations=3, seed=99)
            with pytest.MonkeyPatch().context() as mp:
                from unittest.mock import MagicMock
                mp.setattr(
                    "geomas.simulation.engine.NationAgent",
                    lambda **kwargs: MagicMock()
                )
                engine._init_agents()
            results.append({
                nid: engine.world.nations[nid].government_type
                for nid in nation_ids
            })

        assert results[0] == results[1]

    def test_all_three_types_assigned_with_three_nations(self):
        """With exactly 3 nations, all 3 government types are assigned."""
        engine, nation_ids = self._make_engine(n_nations=3, seed=42)
        with pytest.MonkeyPatch().context() as mp:
            from unittest.mock import MagicMock
            mp.setattr(
                "geomas.simulation.engine.NationAgent",
                lambda **kwargs: MagicMock()
            )
            engine._init_agents()

        assigned = {
            engine.world.nations[nid].government_type
            for nid in nation_ids
        }
        expected = {g.value for g in GovernmentType}
        assert assigned == expected

