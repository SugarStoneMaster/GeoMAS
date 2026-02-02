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


def serialize_world_snapshot(world) -> Dict[str, str]:
    """
    Serialize full WorldState to JSON strings for DB storage.
    
    Args:
        world: WorldState instance
        
    Returns:
        Dict with provinces_json, nations_json, trust_matrix_json, relationship_matrix_json
    """
    return {
        'provinces_json': serialize_provinces(world.provinces),
        'nations_json': serialize_nations(world.nations),
        'trust_matrix_json': serialize_trust_matrix(world.trust_matrix),
        'relationship_matrix_json': serialize_relationship_matrix(world.relationship_matrix)
    }
