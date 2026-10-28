import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
from io import StringIO

st.set_page_config(page_title="Optimalidad y Sink Tree", page_icon="🌐", layout="wide")

# Enlaces y valores iniciales basados en los ejemplos de la guía.
# Los valores no especificados explícitamente por la guía son datos ilustrativos.
DATOS_INICIALES = [
    {"Origen": "H", "Destino": "D", "Retardo_ms": 8.0,  "Banda_Mbps": 100.0, "Disponible": True},
    {"Origen": "D", "Destino": "A", "Retardo_ms": 9.0,  "Banda_Mbps": 100.0, "Disponible": True},
    {"Origen": "A", "Destino": "B", "Retardo_ms": 7.0,  "Banda_Mbps": 100.0, "Disponible": True},
    {"Origen": "H", "Destino": "E", "Retardo_ms": 5.0,  "Banda_Mbps": 50.0,  "Disponible": True},
    {"Origen": "E", "Destino": "J", "Retardo_ms": 10.0, "Banda_Mbps": 50.0,  "Disponible": True},
    {"Origen": "J", "Destino": "C", "Retardo_ms": 8.0,  "Banda_Mbps": 100.0, "Disponible": True},
    {"Origen": "C", "Destino": "B", "Retardo_ms": 6.0,  "Banda_Mbps": 100.0, "Disponible": True},
    {"Origen": "H", "Destino": "O", "Retardo_ms": 7.0,  "Banda_Mbps": 50.0,  "Disponible": True},
    {"Origen": "O", "Destino": "N", "Retardo_ms": 9.0,  "Banda_Mbps": 50.0,  "Disponible": True},
    {"Origen": "N", "Destino": "J", "Retardo_ms": 9.0,  "Banda_Mbps": 50.0,  "Disponible": True},
]
RUTAS_JOHAL = {
    "PSRC": ["H", "D", "A", "B"],
    "SSRC": ["H", "E", "J", "C", "B"],
    "TSRC": ["H", "O", "N", "J", "C", "B"],
}

def ruta_texto(nodos):
    return "–".join(nodos) if nodos else "Sin ruta"

def construir_grafo(tabla):
    """Construye el grafo no dirigido usando solo enlaces activos."""
    G = nx.Graph()
    # Añadimos todos los nodos, incluso si algún enlace queda desactivado.
    for _, fila in tabla.iterrows():
        G.add_node(fila["Origen"])
        G.add_node(fila["Destino"])
        if bool(fila["Disponible"]):
            retardo = max(float(fila["Retardo_ms"]), 0.0)
            banda = float(fila["Banda_Mbps"])
            if banda <= 0:
                # Un enlace sin capacidad positiva no se puede usar en la función multicriterio.
                continue
            G.add_edge(
                fila["Origen"], fila["Destino"],
                Retardo_ms=retardo,
                Banda_Mbps=banda,
                Saltos=1
            )
    return G

def asignar_costos(G, objetivo, alpha, beta, gamma):
    """Asigna un costo no negativo a cada arista para poder usar Dijkstra."""
    retardos = [d["Retardo_ms"] for _, _, d in G.edges(data=True) if d["Retardo_ms"] > 0]
    bandas = [d["Banda_Mbps"] for _, _, d in G.edges(data=True) if d["Banda_Mbps"] > 0]
    d_ref = max(retardos) if retardos else 1.0
    b_ref = max(bandas) if bandas else 1.0

    suma = alpha + beta + gamma
    if suma <= 0:
        alpha, beta, gamma = 1/3, 1/3, 1/3
    else:
        alpha, beta, gamma = alpha/suma, beta/suma, gamma/suma

    for _, _, datos in G.edges(data=True):
        if objetivo == "Mínimo de saltos":
            costo = 1.0
        elif objetivo == "Mínimo retardo":
            costo = datos["Retardo_ms"]
        else:
            costo = (
                alpha
                + beta * (datos["Retardo_ms"] / d_ref)
                + gamma * (b_ref / datos["Banda_Mbps"])
            )
        datos["costo"] = float(costo)

    return (alpha, beta, gamma, d_ref, b_ref)

def metricas_ruta(nodos, tabla):
    if not nodos or len(nodos) < 2:
        return None
    indices = {(r["Origen"], r["Destino"]): r for r in tabla.to_dict("records")}
    indices.update({(r["Destino"], r["Origen"]): r for r in tabla.to_dict("records")})
    retardos, bandas = [], []
    for a, b in zip(nodos[:-1], nodos[1:]):
        fila = indices.get((a, b))
        if fila is None or not bool(fila["Disponible"]) or float(fila["Banda_Mbps"]) <= 0:
            return None
        retardos.append(float(fila["Retardo_ms"]))
        bandas.append(float(fila["Banda_Mbps"]))
    return {
        "Ruta": ruta_texto(nodos),
        "Saltos": len(nodos) - 1,
        "Retardo_total_ms": sum(retardos),
        "Banda_minima_Mbps": min(bandas),
    }

def costo_ruta(nodos, G):
    if not nodos or len(nodos) < 2:
        return None
    try:
        return sum(G[a][b]["costo"] for a, b in zip(nodos[:-1], nodos[1:]))
    except KeyError:
        return None

def dibujar_grafo(G, ruta_optima=None, arbol=None):
    pos = nx.spring_layout(G, seed=14)
    fig = go.Figure()

    # Enlaces: dibujamos también los que están caídos con línea discontinua.
    # Las aristas activas están en G; los enlaces caídos se añaden después desde la tabla.
    for a, b, datos in G.edges(data=True):
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        en_ruta = ruta_optima and any(
            (a == u and b == v) or (a == v and b == u)
            for u, v in zip(ruta_optima[:-1], ruta_optima[1:])
        )
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1], mode="lines",
            line=dict(width=4 if en_ruta else 1.5),
            hoverinfo="text",
            text=f"{a}–{b} | {datos['Retardo_ms']} ms | {datos['Banda_Mbps']} Mbps",
            showlegend=False
        ))

    # Nodos
    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in G.nodes()],
        y=[pos[n][1] for n in G.nodes()],
        mode="markers+text",
        text=list(G.nodes()),
        textposition="top center",
        marker=dict(size=25),
        hovertext=[f"Router {n}" for n in G.nodes()],
        hoverinfo="text",
        showlegend=False
    ))
    fig.update_layout(
        height=500, margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        plot_bgcolor="white"
    )
    return fig

st.title("🌐 Laboratorio de Redes: Optimalidad y Sink Tree")
st.caption("Modelo didáctico basado en la guía del laboratorio de Johal (2008). Los valores de red son ejemplos para experimentar.")

with st.sidebar:
    st.header("Configuración")
    objetivo = st.selectbox(
        "Función objetivo",
        ["Mínimo de saltos", "Mínimo retardo", "Multicriterio"]
    )
    st.write("Pesos de la función multicriterio")
    alpha = st.slider("α — saltos", 0.0, 1.0, 0.50, 0.05)
    beta = st.slider("β — retardo", 0.0, 1.0, 0.35, 0.05)
    gamma = st.slider("γ — baja capacidad", 0.0, 1.0, 0.15, 0.05)
    if alpha + beta + gamma == 0:
        st.warning("Los tres pesos son cero; se usarán pesos iguales.")
    if st.button("Restablecer valores iniciales"):
        st.session_state["tabla_enlaces"] = pd.DataFrame(DATOS_INICIALES)
        st.rerun()

st.subheader("1. Tabla de enlaces")
st.write("Edita el retardo, la capacidad o la disponibilidad. Los cambios se usan inmediatamente en los cálculos.")
if "tabla_enlaces" not in st.session_state:
    st.session_state["tabla_enlaces"] = pd.DataFrame(DATOS_INICIALES)

tabla_editada = st.data_editor(
    st.session_state["tabla_enlaces"],
    key="editor_enlaces",
    use_container_width=True,
    hide_index=True,
    disabled=["Origen", "Destino"],
    column_config={
        "Retardo_ms": st.column_config.NumberColumn("Retardo (ms)", min_value=0.0, step=1.0),
        "Banda_Mbps": st.column_config.NumberColumn("Banda (Mbps)", min_value=0.0, step=5.0),
        "Disponible": st.column_config.CheckboxColumn("Disponible", default=True),
    }
)
st.session_state["tabla_enlaces"] = tabla_editada.copy()

if (tabla_editada["Retardo_ms"] < 0).any():
    st.error("El retardo no puede ser negativo.")
    st.stop()
if (tabla_editada["Banda_Mbps"] < 0).any():
    st.error("La capacidad no puede ser negativa.")
    st.stop()

G = construir_grafo(tabla_editada)
alpha_n, beta_n, gamma_n, d_ref, b_ref = asignar_costos(G, objetivo, alpha, beta, gamma)

st.subheader("2. Ruta óptima recalculada")
st.markdown(
    f"**Función seleccionada:** {objetivo}. "
    f"**Normalización actual:** d_ref = {d_ref:g} ms, b_ref = {b_ref:g} Mbps. "
    f"**Pesos normalizados:** α = {alpha_n:.2f}, β = {beta_n:.2f}, γ = {gamma_n:.2f}."
)
try:
    ruta_optima = nx.shortest_path(G, source="H", target="B", weight="costo")
    costo_optimo = nx.shortest_path_length(G, source="H", target="B", weight="costo")
    met = metricas_ruta(ruta_optima, tabla_editada)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ruta óptima", ruta_texto(ruta_optima))
    col2.metric("Saltos", met["Saltos"])
    col3.metric("Retardo total", f'{met["Retardo_total_ms"]:g} ms')
    col4.metric("Banda mínima", f'{met["Banda_minima_Mbps"]:g} Mbps')
    st.write(f"Costo acumulado de la función seleccionada: **{costo_optimo:.4f}**.")
except (nx.NetworkXNoPath, nx.NodeNotFound):
    ruta_optima = []
    st.error("No existe una ruta disponible entre H y B con la configuración actual.")

col_grafo, col_tabla = st.columns([1.15, 1])
with col_grafo:
    st.markdown("**Grafo de la red**")
    st.plotly_chart(dibujar_grafo(G, ruta_optima), use_container_width=True)
with col_tabla:
    st.markdown("**Comparación con las rutas preconfiguradas**")
    resultados = []
    for nombre, nodos in RUTAS_JOHAL.items():
        m = metricas_ruta(nodos, tabla_editada)
        if m is None:
            resultados.append({
                "Prioridad": nombre, "Recorrido": ruta_texto(nodos),
                "Saltos": len(nodos)-1, "Retardo (ms)": "No disponible",
                "Banda mínima (Mbps)": "—", "Costo": "—"
            })
        else:
            resultados.append({
                "Prioridad": nombre, "Recorrido": m["Ruta"],
                "Saltos": m["Saltos"], "Retardo (ms)": m["Retardo_total_ms"],
                "Banda mínima (Mbps)": m["Banda_minima_Mbps"],
                "Costo": round(costo_ruta(nodos, G), 4) if costo_ruta(nodos, G) is not None else "—"
            })
    st.dataframe(pd.DataFrame(resultados), hide_index=True, use_container_width=True)
    st.caption("Las rutas PSRC, SSRC y TSRC son las tres configuraciones de la guía; no representan todas las rutas posibles del grafo.")

st.subheader("3. Sink Tree con destino B")
st.write("Para cada router, se calcula el siguiente salto que conduce a B con el mismo costo seleccionado en la barra lateral.")
filas_sink = []
try:
    distancias, caminos = nx.single_source_dijkstra(G, source="B", weight="costo")
    for nodo in sorted(G.nodes()):
        if nodo == "B":
            filas_sink.append({"Router": "B", "Siguiente salto hacia B": "Destino", "Costo hasta B": 0.0, "Camino hasta B": "B"})
        elif nodo in caminos:
            camino = caminos[nodo]
            # caminos se calculan desde B; para ir desde el nodo hacia B, el siguiente es el segundo elemento en la ruta invertida.
            camino_hacia_b = list(reversed(camino))
            filas_sink.append({
                "Router": nodo,
                "Siguiente salto hacia B": camino_hacia_b[1] if len(camino_hacia_b) > 1 else "B",
                "Costo hasta B": round(distancias[nodo], 4),
                "Camino hasta B": ruta_texto(camino_hacia_b)
            })
        else:
            filas_sink.append({"Router": nodo, "Siguiente salto hacia B": "Sin ruta", "Costo hasta B": "—", "Camino hasta B": "Sin ruta"})
except Exception as e:
    st.warning(f"No se pudo construir el Sink Tree: {e}")
st.dataframe(pd.DataFrame(filas_sink), hide_index=True, use_container_width=True)

st.subheader("4. Fórmulas del modelo")
st.markdown("""
- **Saltos:** `H(P) = Σ 1`
- **Retardo:** `D(P) = Σ dᵢⱼ`
- **Banda mínima del camino:** `B(P) = min(bᵢⱼ)`
- **Costo multicriterio:** `C(P) = Σ [α + β(dᵢⱼ/d_ref) + γ(b_ref/bᵢⱼ)]`
- **Condición de pesos:** `α + β + γ = 1` después de normalizarlos.

La penalización `b_ref / bᵢⱼ` representa capacidad baja dentro de un costo aditivo; no es el ancho de banda extremo a extremo. El ancho de banda del camino se calcula aparte como el mínimo de las capacidades de sus enlaces.
""")

st.subheader("5. Exportar resultados")
csv_rutas = pd.DataFrame(resultados).to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "Descargar comparación de rutas (CSV)",
    data=csv_rutas,
    file_name="comparacion_rutas.csv",
    mime="text/csv"
)
csv_enlaces = tabla_editada.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "Descargar tabla actual de enlaces (CSV)",
    data=csv_enlaces,
    file_name="enlaces_red.csv",
    mime="text/csv"
)

with st.expander("Notas para el informe"):
    st.markdown("""
    1. En la prueba A, selecciona **Mínimo de saltos** y comprueba 3, 4 y 5 saltos para PSRC, SSRC y TSRC.
    2. En la prueba B, cambia H–D a 40 ms y selecciona **Mínimo retardo**. P1 debe sumar 56 ms; P2, 29 ms; P3, 39 ms. El óptimo del grafo completo podría ser otra ruta.
    3. En la prueba C, desactiva H–D y comprueba que PSRC queda no disponible.
    4. En la prueba D, desactiva también H–E y verifica si TSRC sigue conectada.
    5. En la prueba E, restablece los valores y cambia E–J a 5 Mbps. La banda mínima de P2 pasa a 5 Mbps.
    6. En la prueba F, prueba los pesos (1,0,0), (0,1,0), (0,0,1) y (0.5,0.35,0.15).

    Los valores de retardo, capacidad y la función multicriterio son construcciones didácticas del laboratorio, no resultados experimentales atribuidos al artículo de Johal.
    """)

st.divider()
st.caption("Python · NetworkX · Streamlit · Plotly")
