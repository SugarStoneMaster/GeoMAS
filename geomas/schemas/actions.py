from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class ActionType(str, Enum):
    # --- DEFENSE ACTIONS ---
    MOBILIZE_UNIT = "MOBILIZE_UNIT"
    """
    Crea una nuova unità militare (Fanteria/Carri/Marina) in una provincia specifica.
    Costo: Alto costo iniziale + Mantenimento per turno.
    Rischio: Toglie risorse al Welfare (abbassa stabilità).
    """
    
    FORTIFY_PROVINCE = "FORTIFY_PROVINCE"
    """
    Costruisce difese statiche (bunker) su una provincia di confine, aumentando il bonus difensivo.
    Costo: Medio (Materiali).
    Rischio: Può essere visto come provocazione dai vicini.
    """
    
    DEPLOY_TROOPS = "DEPLOY_TROOPS"
    """
    Sposta unità da A a B. Se B è nemica, innesca una Battaglia.
    Costo: Carburante/Risorse.
    Rischio: Innesca guerra se non dichiarata. Perdita truppe.
    """
    
    NUCLEAR_OPTION = "NUCLEAR_OPTION"
    """
    Distrugge permanentemente una provincia (risorse = 0).
    Costo: Paria internazionale (Tutti rompono le relazioni).
    Rischio: Game Over diplomatico.
    """
    
    COVERT_ESPIONAGE = "COVERT_ESPIONAGE"
    """
    Invia spie per rivelare la "Fog of War" di una provincia nemica (vedere truppe nascoste).
    Costo: Basso (Budget).
    Rischio: Se fallisce, peggiora la reputazione diplomatica.
    """

    # --- ECONOMIC ACTIONS ---
    INVEST_WELFARE = "INVEST_WELFARE"
    """
    Spende budget per servizi civili. Aumenta direttamente la Satisfaction dell'Opinione Pubblica.
    Costo: Alto (Budget).
    Rischio: Meno soldi per l'esercito (vulnerabilità).
    """
    
    TRADE_PROPOSAL = "TRADE_PROPOSAL"
    """
    Invia una proposta formale a un'altra nazione: "Ti do X Risorse per Y Gold a turno".
    Costo: Nessuno immediato.
    Rischio: Rende dipendenti da partner esteri.
    """
    
    IMPOSE_SANCTIONS = "IMPOSE_SANCTIONS"
    """
    Blocca il commercio con una nazione target e aumenta i costi delle sue importazioni globali.
    Costo: Perdita di introiti commerciali propri.
    Rischio: Rappresaglia economica.
    """
    
    RAISE_WAR_TAX = "RAISE_WAR_TAX"
    """
    Tassa straordinaria per ottenere liquidità immediata (Budget Boost).
    Costo: Crollo immediato della Satisfaction (Rischio Sciopero).
    """
    
    DEVELOP_TECH = "DEVELOP_TECH"
    """
    Investe per sbloccare capacità passive (es. "Marina", "Raffinazione migliore").
    Costo: Molto alto (Investimento a lungo termine).
    """

    # --- FOREIGN AFFAIRS ACTIONS ---
    SEND_DIPLOMATIC_MESSAGE = "SEND_DIPLOMATIC_MESSAGE"
    """
    Target, Content (Text), Intent (Friendly/Hostile).
    Per migliorare relazioni, bluffare o minacciare senza spendere soldi.
    """
    
    PROPOSE_ALLIANCE = "PROPOSE_ALLIANCE"
    """
    Target_Nation.
    Se il Trust è alto (>0.8) e serve protezione comune.
    """
    
    FORMAL_DECLARATION_OF_WAR = "FORMAL_DECLARATION_OF_WAR"
    """
    Target_Nation.
    Per legalizzare un conflitto imminente e ridurre penalità diplomatiche future.
    """
    
    BREAK_TREATY = "BREAK_TREATY"
    """
    Target_Nation, Treaty_ID.
    Se l'alleanza non è più conveniente o il partner ha violato i patti.
    """
    
    REQUEST_PEACE = "REQUEST_PEACE"
    """
    Target_Nation.
    Se la guerra sta andando male e serve fermare le ostilità.
    """
    
    FUND_INSURGENCY = "FUND_INSURGENCY"
    """
    Finanzia segretamente gruppi ribelli in una nazione nemica. Abbassa la Satisfaction del target senza invadere.
    Costo: Budget (Soldi neri).
    Rischio: Se scoperto (Intelligence fallita), genera un Casus Belli immediato e crollo della reputazione globale.
    """

    # --- PUBLIC OPINION EVENTS (Triggers) ---
    GENERAL_STRIKE = "GENERAL_STRIKE"
    """
    Se Satisfaction < 30%.
    Produzione Risorse = 0 per questo turno. Il Presidente non ha budget per agire.
    """
    
    CIVIL_UNREST = "CIVIL_UNREST"
    """
    Se Satisfaction < 15%.
    Le truppe disertano (perdita unità) o il Governo cade (Game Over).
    """
    
    RALLY_EFFECT = "RALLY_EFFECT"
    """
    Se Attaccati da Nemico.
    Bonus temporaneo alla Satisfaction e alla produzione militare.
    """

class ActionPayload(BaseModel):
    """
    Generic container for action parameters.
    The 'parameters' dict structure depends on the action_type.
    """
    action_type: ActionType
    target_nation_id: Optional[str] = None
    target_province_id: Optional[int] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
