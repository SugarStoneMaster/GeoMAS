# 🎲 Simulation Rules & Math Standards

## 🎯 Core Directive: Determinism
GeoMAS è una simulazione scientifica. **Il determinismo è sacro.**
*   Ogni funzione che usa casualità DEVE accettare un parametro `seed` o un oggetto `numpy.random.Generator`.
*   Non usare mai `random.choice()` o `np.random.rand()` globali.

## 🌍 Spatial World Engine
Il mondo è generato proceduralmente ma deve obbedire a regole fisiche coerenti.

### 1. Voronoi Topology
*   Usa `scipy.spatial.Voronoi`.
*   **Lloyd's Relaxation:** Applicare sempre 2-3 iterazioni per regolarizzare le celle (evitare "shards").
*   **Graph Representation:** Il Voronoi deve essere convertito immediatamente in un grafo `NetworkX` per il pathfinding.
    *   Nodes = Province
    *   Edges = Confini condivisi

### 2. Geography & Tectonics
*   **Continents:** Usa il metodo "Organic Growth" o "Distance from Seeds" con Rejection Sampling per garantire continenti separati.
*   **Land/Ocean Ratio:** Deve essere bilanciato. Evitare mappe con solo terra o solo oceano.
*   **Adjacency:** Due nazioni sono vicine se condividono almeno un bordo terrestre o se le loro acque territoriali si toccano.

### 3. Resource Model
*   Ogni provincia ha attributi: `Energy`, `Materials`, `Food`.
*   Le risorse non sono infinite.
*   **Constraint:** Una nazione non può spendere risorse che non ha (No debito non autorizzato).

## ⚖️ Deterministic Rules Oracle
Questo componente è l'arbitro. Non ha AI, solo logica `if-then`.

### Validation Checks
1.  **Topological:** `can_move_troops(A, B)` -> True solo se esiste un path nel grafo NetworkX e A ha accesso militare.
2.  **Economic:** `can_afford(Nation, Cost)` -> True solo se `Budget >= Cost`.
3.  **Diplomatic:** `can_trade(NationA, NationB)` -> True solo se esiste un Trattato Commerciale attivo.

### State Modification
*   Solo l'Oracle può chiamare metodi `set_value()` sullo stato del mondo.
*   Gli agenti possono solo inviare "Richieste" (Envelopes).