# 🎲 Simulation Rules & Math Standards

## 🎯 Core Directive: Determinism
GeoMAS è una simulazione scientifica. **Il determinismo è sacro.**
*   Ogni funzione che usa casualità DEVE accettare un parametro `seed` o un oggetto `numpy.random.Generator`.
*   Non usare mai `random.choice()` o `np.random.rand()` globali.

## 🌍 Spatial World Engine
Il mondo è generato proceduralmente ma deve obbedire a regole fisiche coerenti.

### 1. Voronoi Topology
*   Usa `scipy.spatial.Voronoi`.
*   **Lloyd's Relaxation:** Applicare sempre 2-3 iterazioni per regolarizzare le celle.
*   **Graph Representation:** Il Voronoi deve essere convertito immediatamente in un grafo `NetworkX`.

### 2. Geography & Tectonics
*   **Continents:** Usa Rejection Sampling per garantire continenti separati.
*   **Terrain:** Include `LAND`, `OCEAN`, `COASTAL`, `MOUNTAIN`.
*   **Capitals:** Assegnate alla provincia con area maggiore (Shapely).

### 3. Resource Model
*   Ogni provincia ha attributi: `Energy`, `Materials`, `Food`.
*   Le risorse non sono infinite.

## ⚖️ Deterministic Rules Oracle
Questo componente è l'arbitro. Non ha AI, solo logica `if-then`.

### Validation Checks
1.  **Topological:** `can_move_troops(A, B)` -> True solo se esiste un path nel grafo NetworkX.
2.  **Economic:** `can_afford(Nation, Cost)` -> True solo se `Budget >= Cost`.
3.  **Diplomatic:** `can_trade(NationA, NationB)` -> True solo se esiste un Trattato Commerciale attivo.

### Execution Logic: Waterfall Priority
Per il **Military Payload**, l'Oracle applica una logica a cascata:
1.  Prende la lista di azioni ordinata per priorità.
2.  Esegue Azione 1 -> Deduce Costo.
3.  Se Budget > Costo Azione 2 -> Esegue Azione 2.
4.  Se Budget < Costo Azione 3 -> Scarta Azione 3 e notifica "Insufficient Funds".

### State Modification
*   Solo l'Oracle può chiamare metodi `set_value()` sullo stato del mondo.
*   Gli agenti possono solo inviare "Richieste" (Envelopes).