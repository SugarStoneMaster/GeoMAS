"""
Serialization Helpers.

Utilities for converting Pydantic models to JSON-safe dictionaries,
handling numpy types and enums properly.
"""

import json
from typing import Any, Dict, List
import numpy as np


def convert_numpy(obj: Any) -> Any:
    """
    Recursively convert numpy types to Python native types.
    
    Handles numpy integers, floats, arrays, and nested structures.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_numpy(v) for v in obj]
    if isinstance(obj, tuple):
        return [convert_numpy(v) for v in obj]
    return obj


def serialize_provinces(provinces: Dict) -> str:
    """
    Serialize provinces dict to JSON string.
    
    Args:
        provinces: Dict of province_id -> ProvinceState
        
    Returns:
        JSON string
    """
    data = [convert_numpy(p.model_dump()) for p in provinces.values()]
    return json.dumps(data)


def serialize_nations(nations: Dict) -> str:
    """
    Serialize nations dict to JSON string.
    
    Args:
        nations: Dict of nation_id -> NationState
        
    Returns:
        JSON string
    """
    data = [convert_numpy(n.model_dump()) for n in nations.values()]
    return json.dumps(data)


def serialize_trust_matrix(trust_matrix: Dict) -> str:
    """
    Serialize trust matrix to JSON string.
    
    Args:
        trust_matrix: Dict of "nation1:nation2" -> trust_value
        
    Returns:
        JSON string
    """
    return json.dumps(convert_numpy(trust_matrix))


def serialize_relationship_matrix(relationship_matrix: Dict) -> str:
    """
    Serialize relationship matrix to JSON string.
    
    Args:
        relationship_matrix: Dict of "nation1:nation2" -> RelationshipState
        
    Returns:
        JSON string (enum values as strings)
    """
    data = {k: v.value if hasattr(v, 'value') else v 
            for k, v in relationship_matrix.items()}
    return json.dumps(data)


def serialize_envelope(envelope) -> str:
    """
    Serialize CountryEnvelope to JSON string.
    
    Args:
        envelope: CountryEnvelope instance
        
    Returns:
        JSON string
    """
    data = envelope.model_dump(mode='json')
    return json.dumps(convert_numpy(data))


def serialize_world_snapshot(world, memory=None) -> Dict[str, str]:
    """
    Serialize full WorldState and optional ContextManager to JSON strings.
    
    Args:
        world: WorldState instance
        memory: Optional ContextManager instance
        
    Returns:
        Dict with provinces_json, nations_json, trust_matrix_json, 
        relationship_matrix_json, and memory_json
    """
    data = {
        'provinces_json': serialize_provinces(world.provinces),
        'nations_json': serialize_nations(world.nations),
        'trust_matrix_json': serialize_trust_matrix(world.trust_matrix),
        'relationship_matrix_json': serialize_relationship_matrix(world.relationship_matrix),
        'world_events_json': json.dumps(convert_numpy(world.global_events))
    }
    if memory:
        data['memory_json'] = serialize_memory(memory)
    else:
        data['memory_json'] = json.dumps({})
        
    return data


def serialize_memory(memory) -> str:
    """
    Serialize ContextManager state to JSON string.
    """
    data = {
        "relationship_summaries": {
            n_id: {o_id: summary.model_dump() for o_id, summary in rels.items()}
            for n_id, rels in memory.relationship_summaries.items()
        },
        "global_events": [e.model_dump() for e in memory.global_events],
        "nation_actions": {
            n_id: [a.model_dump() for a in actions]
            for n_id, actions in memory.nation_actions.items()
        },
        "trust_history": memory._trust_history
    }
    return json.dumps(convert_numpy(data))


# --- DESERIALIZATION ---

def deserialize_provinces(json_data) -> Dict[int, Any]:
    """
    Deserialize provinces JSON back to dict of ProvinceState.
    
    Args:
        json_data: JSON string or parsed list of province dicts
        
    Returns:
        Dict of province_id -> ProvinceState
    """
    from geomas.schemas.world import ProvinceState
    
    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data
    
    provinces = {}
    for p_dict in data:
        province = ProvinceState(**p_dict)
        provinces[province.id] = province
    
    return provinces


def deserialize_nations(json_data) -> Dict[str, Any]:
    """
    Deserialize nations JSON back to dict of NationState.
    
    Args:
        json_data: JSON string or parsed list of nation dicts
        
    Returns:
        Dict of nation_id -> NationState
    """
    from geomas.schemas.world import NationState
    
    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data
    
    nations = {}
    for n_dict in data:
        nation = NationState(**n_dict)
        nations[nation.id] = nation
    
    return nations


def deserialize_trust_matrix(json_data) -> Dict[str, Dict[str, float]]:
    """
    Deserialize trust matrix JSON.
    
    Args:
        json_data: JSON string or parsed dict
        
    Returns:
        Trust matrix dict
    """
    if isinstance(json_data, str):
        return json.loads(json_data)
    return json_data


def deserialize_relationship_matrix(json_data) -> Dict[str, Dict[str, str]]:
    """
    Deserialize relationship matrix JSON.
    
    Args:
        json_data: JSON string or parsed dict
        
    Returns:
        Relationship matrix dict (values are RelationshipState string values)
    """
    if isinstance(json_data, str):
        return json.loads(json_data)
    return json_data


def deserialize_world_snapshot(
    provinces_json,
    nations_json,
    trust_matrix_json,
    relationship_matrix_json,
    turn: int = 0,
    global_events: List[str] = None
):
    """
    Reconstruct a WorldState from DB snapshot data.
    
    Args:
        provinces_json: Provinces JSON data
        nations_json: Nations JSON data
        trust_matrix_json: Trust matrix JSON data
        relationship_matrix_json: Relationship matrix JSON data
        turn: Turn number
        global_events: Optional list of global events
        
    Returns:
        Reconstructed WorldState instance
    """
    from geomas.schemas.world import WorldState
    
    return WorldState(
        turn=turn,
        provinces=deserialize_provinces(provinces_json),
        nations=deserialize_nations(nations_json),
        trust_matrix=deserialize_trust_matrix(trust_matrix_json),
        relationship_matrix=deserialize_relationship_matrix(relationship_matrix_json),
        global_events=global_events or []
    )


def deserialize_memory_state(json_data: str) -> Dict[str, Any]:
    """
    Deserialize ContextManager JSON back to object state.
    """
    from geomas.agents.context.memory.schemas import RelationshipSummary, NotableEvent, MyAction
    
    data = json.loads(json_data)
    if not data:
        return {}
        
    state = {
        "relationship_summaries": {
            n_id: {o_id: RelationshipSummary(**summary_dict) for o_id, summary_dict in rels.items()}
            for n_id, rels in data.get("relationship_summaries", {}).items()
        },
        "global_events": [NotableEvent(**e_dict) for e_dict in data.get("global_events", [])],
        "nation_actions": {
            n_id: [MyAction(**a_dict) for a_dict in actions]
            for n_id, actions in data.get("nation_actions", {}).items()
        },
        "trust_history": data.get("trust_history", {})
    }
    return state
