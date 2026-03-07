import pytest
from geomas.agents.schemas.protocol import EconomicProposal, EconomicIntent, EconomicDecree, PresidentialDecision, CountryEnvelope
from geomas.actions.economy.schemas import EconomicProposalPayload, EconomicActionType, EconomicPayload
from geomas.actions.common import Decision

def test_economy_proposal_schema():
    """Verify that EconomicProposal now requires an intent with reasoning."""
    payload = EconomicProposalPayload(action_type=EconomicActionType.INVEST_WELFARE, amount=1000)
    
    # This should fail if intent is missing
    with pytest.raises(Exception):
        EconomicProposal(payload=payload)
    
    # This should pass
    intent = EconomicIntent(reasoning="Test reasoning")
    prop = EconomicProposal(intent=intent, payload=payload)
    assert prop.intent.reasoning == "Test reasoning"

def test_economy_decree_schema():
    """Verify that EconomicDecree now requires reasoning."""
    # This should fail if reasoning is missing
    with pytest.raises(Exception):
        EconomicDecree(action=PresidentialDecision.APPROVE)
    
    # This should pass
    decree = EconomicDecree(action=PresidentialDecision.APPROVE, reasoning="Presidential logic")
    assert decree.reasoning == "Presidential logic"

def test_country_envelope_economy_reasoning():
    """Verify that CountryEnvelope can store economic reasoning."""
    # Build a minimal envelope
    from geomas.agents.schemas.protocol import GlobalStrategy, DefensePayload, ForeignPayload, DefenseIntentType, ForeignIntentType
    
    envelope = CountryEnvelope(
        turn=1,
        sender_id="NAT_A",
        global_strategy=GlobalStrategy.TOTAL_EXPANSIONISM,
        public_statement="Public message",
        defense_payload=DefensePayload(decision=Decision.APPROVE, moves=[]),
        defense_public_intent=DefenseIntentType.IDLE,
        defense_private_intent=DefenseIntentType.IDLE,
        defense_private_reasoning="Def reasoning",
        economic_payload=EconomicPayload(decision=Decision.APPROVE, action_type=EconomicActionType.IDLE),
        economic_private_reasoning="Eco reasoning",
        foreign_payload=ForeignPayload(decision=Decision.APPROVE, action_type=EconomicActionType.IDLE),
        foreign_public_intent=ForeignIntentType.IDLE,
        foreign_private_intent=ForeignIntentType.IDLE,
        foreign_private_reasoning="For reasoning"
    )
    assert envelope.economic_private_reasoning == "Eco reasoning"
