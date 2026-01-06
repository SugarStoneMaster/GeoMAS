# 🖥️ Frontend Guidelines (Streamlit)

## ⚡ Performance & Caching
Streamlit ricalcola l'intero script a ogni interazione. Questo è letale per la generazione procedurale.

### Rules
1.  **Cache Heavy Computation:** Usa `@st.cache_data` per la generazione della mappa Voronoi. Non rigenerare il mondo se il seed non cambia.
2.  **Cache Resources:** Usa `@st.cache_resource` per caricare modelli LLM o connessioni DB.
3.  **Session State:** Usa `st.session_state` per mantenere il numero del turno e lo storico dei log tra i refresh.

## 🎨 Visualization
*   **Map Rendering:** Usa `matplotlib` per statico o `plotly` per interattivo.
*   **Graph Visualization:** Non disegnare nodi a caso. Usa le coordinate reali dei centroidi Voronoi.
*   **Feedback Loop:** La UI deve mostrare chiaramente lo stato "Thinking" degli agenti.

## 🛠 Debugging Tools
*   Includi sempre una tab "Inspector" per vedere il JSON grezzo dello stato del mondo.
*   Visualizza i log di errore del `Deterministic Rules Oracle` in rosso.