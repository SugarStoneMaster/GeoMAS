from geomas.schemas.protocol import CountryEnvelope, PublicIntent, MilitaryIntentType, EconomicIntentType, ForeignIntentType

class DeceptionAnalyzer:
    """
    Calculates the Deception Score by comparing Public Rhetoric vs Private Reality.
    Score range: 0.0 (Honest) to 1.0 (Total Lie).
    """

    # Mapping Intents to a common "Aggression Scale" (0=Peace, 1=Neutral/Def, 2=Aggressive)
    
    PUBLIC_SCALE = {
        PublicIntent.PEACEFUL: 0,
        PublicIntent.NEUTRAL: 1,
        PublicIntent.DEFENSIVE: 1,
        PublicIntent.AGGRESSIVE: 2
    }

    MILITARY_SCALE = {
        MilitaryIntentType.IDLE: 0,
        MilitaryIntentType.DETERRENCE: 0,
        MilitaryIntentType.RECONNAISSANCE: 1,
        MilitaryIntentType.DEFENSE: 1,
        MilitaryIntentType.PUNISHMENT: 2,
        MilitaryIntentType.CONQUEST: 2
    }

    ECONOMIC_SCALE = {
        EconomicIntentType.IDLE: 0,
        EconomicIntentType.GROWTH: 0,
        EconomicIntentType.SUPPORT: 0,
        EconomicIntentType.SURVIVAL: 1,
        EconomicIntentType.SABOTAGE: 2
    }

    FOREIGN_SCALE = {
        ForeignIntentType.IDLE: 0,
        ForeignIntentType.COOPERATION: 0,
        ForeignIntentType.APPEASEMENT: 0,
        ForeignIntentType.DECEPTION: 2, # Explicit deception intent is max score
        ForeignIntentType.COERCION: 2
    }

    @classmethod
    def calculate_score(cls, envelope: CountryEnvelope) -> float:
        """
        Computes the deception score for a given envelope.
        """
        public_score = cls.PUBLIC_SCALE.get(envelope.public_intent, 1)
        
        # Calculate private scores
        mil_score = cls.MILITARY_SCALE.get(envelope.military_intent.type, 0)
        eco_score = cls.ECONOMIC_SCALE.get(envelope.economic_intent.type, 0)
        for_score = cls.FOREIGN_SCALE.get(envelope.foreign_intent.type, 0)
        
        # The "Real" intent is the maximum aggression shown in any private channel
        private_score = max(mil_score, eco_score, for_score)
        
        # Deception is the difference. 
        # If Public says Aggressive (2) and Private is Peace (0), is it deception? 
        # Yes, it's bluffing.
        # If Public says Peace (0) and Private is Aggressive (2), it's lying.
        
        diff = abs(public_score - private_score)
        
        # Normalize to 0.0 - 1.0 (Max diff is 2)
        return diff / 2.0
