import networkx as nx
from typing import List, Optional, Set, Dict
from geomas.schemas.world import WorldState, TerrainType # Updated import

class SpatialManager:
    """
    The GPS and Topological Analyzer of GeoMAS.
    Wraps a NetworkX graph to provide pathfinding and border analysis.
    """

    def __init__(self, world: WorldState):
        self.world = world
        self.graph = nx.Graph()
        self._build_graph()

    def _build_graph(self):
        """Constructs the NetworkX graph from the WorldState."""
        valid_province_ids = set(self.world.provinces.keys())
        
        for p_id, province in self.world.provinces.items():
            # Add Node with metadata
            self.graph.add_node(
                p_id, 
                owner=province.owner_id, 
                terrain=province.terrain
            )
            
            # Add Edges
            for n_id in province.neighbors:
                if n_id in valid_province_ids:
                    self.graph.add_edge(p_id, n_id)

    def get_shortest_path(self, start_id: int, end_id: int) -> Optional[List[int]]:
        """
        Returns the sequence of province IDs for the shortest path.
        Returns None if no path exists.
        """
        try:
            return nx.shortest_path(self.graph, source=start_id, target=end_id)
        except nx.NetworkXNoPath:
            return None
        except nx.NodeNotFound:
            return None

    def get_path_length(self, start_id: int, end_id: int) -> int:
        """Returns the number of hops between two provinces."""
        try:
            return nx.shortest_path_length(self.graph, source=start_id, target=end_id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return -1

    def get_border_provinces(self, nation_id: str) -> List[int]:
        """
        Returns a list of province IDs belonging to nation_id that share
        a border with a DIFFERENT nation (or are coastal).
        """
        nation = self.world.nations.get(nation_id)
        if not nation:
            return []

        border_provinces = []
        
        for p_id in nation.province_ids:
            province = self.world.provinces[p_id]
            is_border = False
            
            for n_id in province.neighbors:
                neighbor = self.world.provinces.get(n_id)
                if not neighbor:
                    continue
                
                # Check if neighbor has different owner
                if neighbor.owner_id != nation_id:
                    is_border = True
                    break
            
            if is_border:
                border_provinces.append(p_id)
                
        return border_provinces

    def get_neighboring_nations(self, nation_id: str) -> Set[str]:
        """
        Returns a set of Nation IDs that share a land border with the given nation.
        """
        neighbors = set()
        border_provinces = self.get_border_provinces(nation_id)
        
        for p_id in border_provinces:
            province = self.world.provinces[p_id]
            for n_id in province.neighbors:
                neighbor_prov = self.world.provinces.get(n_id)
                if neighbor_prov and neighbor_prov.owner_id:
                    if neighbor_prov.owner_id != nation_id:
                        neighbors.add(neighbor_prov.owner_id)
                        
        return neighbors

    def get_coastal_provinces(self, nation_id: str) -> List[int]:
        """Returns all provinces of a nation that touch the Ocean."""
        nation = self.world.nations.get(nation_id)
        if not nation:
            return []
            
        coastal = []
        for p_id in nation.province_ids:
            if self.world.provinces[p_id].terrain == TerrainType.COASTAL:
                coastal.append(p_id)
        return coastal

    def is_contiguous(self, nation_id: str) -> bool:
        """
        Checks if the nation's territory is a single connected component.
        Useful for stability checks (split nations are unstable).
        """
        nation = self.world.nations.get(nation_id)
        if not nation or not nation.province_ids:
            return True # Empty is technically contiguous or irrelevant
            
        # Create a subgraph of only this nation's provinces
        subgraph = self.graph.subgraph(nation.province_ids)
        return nx.is_connected(subgraph)
