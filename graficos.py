import pandas as pd
import plotly.graph_objects as go
from analisis import procesar_datos


def _layout_base(titulo, x_titulo="", y_titulo="N° de registros", altura=320):
    return dict(
        title=dict(
            text=titulo,
            font=dict(size=14, color="#1e293b", family="Segoe UI, Arial, sans-serif"),
            x=0.02,
            y=0.95
        ),
        autosize=True,
        height=altura,
        margin=dict(l=48, r=24, t=48, b=58),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family="Segoe UI, Arial, sans-serif", size=11, color="#475569"),
        xaxis=dict(
            title=x_titulo,
            showgrid=False,
            linecolor="#e2e8f0",
            tickfont=dict(size=10, color="#64748b"),
            automargin=True
        ),
        yaxis=dict(
            title=y_titulo,
            showgrid=True,
            gridcolor="#f1f5f9",
            zeroline=False,
            tickfont=dict(size=10, color="#64748b"),
            automargin=True
        ),
        hoverlabel=dict(bgcolor="#0f172a", font_color="#ffffff", font_size=11)
    )


def _sin_datos(titulo):
    fig = go.Figure()
    fig.update_layout(**_layout_base(titulo))
    fig.add_annotation(text="Sin datos registrados", showarrow=False, font=dict(color="#94a3b8", size=12))
    return fig


# 1. BARRAS: MUESTRAS POR TIPO DE ANÁLISIS
def grafico_barras(df):
    titulo = "Muestras ingresadas por tipo de análisis"
    if df is None or df.empty or "Tipo de Muestra" not in df.columns:
        return _sin_datos(titulo)

    series = df["Tipo de Muestra"].dropna().astype(str).str.split(",").explode().str.strip()
    series = series[(series != "") & (series.str.lower() != "nan")]
    conteo = series.value_counts().head(6)
    if conteo.empty:
        return _sin_datos(titulo)

    etiquetas = [
        e.replace("Análisis de ", "")
         .replace("Análisis ", "")
         .replace("Diagnostico de Emfermedades", "Diag. Enf.")
         .replace("Enmienda Inorgánica", "Enmienda")[:14]
        for e in conteo.index
    ]
    valores = conteo.values.tolist()

    fig = go.Figure(go.Bar(
        x=etiquetas,
        y=valores,
        width=0.5,
        text=valores,
        textposition="inside",
        insidetextanchor="end",
        textfont=dict(color="#ffffff", size=11, family="Segoe UI, sans-serif"),
        marker=dict(color="#0a2e46")
    ))
    layout = _layout_base(titulo, x_titulo="Matriz de análisis", y_titulo="Cantidad")
    layout["xaxis"]["tickangle"] = -20
    fig.update_layout(**layout)
    return fig


# 2. DONA: DISTRIBUCIÓN GLOBAL DE CLIENTES
def grafico_dona(df):
    titulo = "Distribución Global de Clientes"
    if df is None or df.empty or "Tipo de Cliente" not in df.columns:
        return _sin_datos(titulo)

    serie = df["Tipo de Cliente"].dropna().astype(str).str.strip()
    serie = serie[(serie != "") & (serie.str.lower() != "nan")]
    conteo = serie.value_counts()
    colores = ["#16a34a", "#f59e0b", "#64748b", "#ef4444"]

    fig = go.Figure(go.Pie(
        labels=conteo.index.tolist(),
        values=conteo.values.tolist(),
        hole=0.52,
        textinfo="percent",
        textfont=dict(size=11, color="#ffffff"),
        marker=dict(colors=colores[:len(conteo)], line=dict(color="#ffffff", width=2)),
        hovertemplate="<b>%{label}</b><br>Registros: %{value}<br>Porcentaje: %{percent}<extra></extra>"
    ))
    layout = _layout_base(titulo)
    layout["margin"] = dict(l=15, r=15, t=48, b=35)
    layout["legend"] = dict(orientation="h", x=0.5, xanchor="center", y=-0.08, font=dict(size=11, color="#334155"))
    fig.update_layout(**layout)
    return fig


# 3. LÍNEAS MÚLTIPLES: TENDENCIA POR FECHA Y ESTADO
def grafico_categorias(df, registros=None):
    titulo = "Muestras recibidas por fecha y estado"
    if not registros:
        return _sin_datos(titulo)

    filas = []
    for r in registros:
        dt = pd.to_datetime(r.get("fecha"), dayfirst=True, errors="coerce")
        if pd.isna(dt):
            continue
        est = str(r.get("estado", "En Proceso"))
        if "Aprobado" in est or "Finalizado" in est:
            cat = "Aprobados"
        elif "Rechazado" in est:
            cat = "Rechazados"
        elif "Observado" in est:
            cat = "Observados"
        else:
            cat = "En Proceso"
        filas.append({"dt": dt.date(), "cat": cat})

    if not filas:
        return _sin_datos(titulo)

    df_f = pd.DataFrame(filas)
    fechas_ord = sorted(df_f["dt"].unique())
    etiquetas_x = [f.strftime("%d/%m") for f in fechas_ord]

    series_cfg = [
        ("Aprobados", "#16a34a"),
        ("Rechazados", "#ef4444"),
        ("Observados", "#64748b"),
        ("En Proceso", "#f59e0b")
    ]

    fig = go.Figure()
    for nombre_cat, color in series_cfg:
        sub = df_f[df_f["cat"] == nombre_cat].groupby("dt").size()
        y_vals = [int(sub.get(f, 0)) for f in fechas_ord]
        fig.add_trace(go.Scatter(
            x=etiquetas_x,
            y=y_vals,
            mode="lines+markers",
            name=nombre_cat,
            line=dict(color=color, width=2),
            marker=dict(size=6, color=color)
        ))

    layout = _layout_base(titulo, x_titulo="Fecha", y_titulo="N° de registros")
    layout["margin"] = dict(l=45, r=15, t=48, b=55)
    layout["xaxis"]["type"] = "category"
    layout["xaxis"]["tickangle"] = -30
    layout["legend"] = dict(orientation="h", x=0.5, xanchor="center", y=-0.25, font=dict(size=10, color="#334155"))
    fig.update_layout(**layout)
    return fig


# 4. BARRAS: PROCEDENCIA POR PROVINCIA
def grafico_vendedores(df):
    titulo = "Muestras por Provincia de Origen"
    if df is None or df.empty or "Provincia" not in df.columns:
        return _sin_datos(titulo)

    conteo = df["Provincia"].dropna().astype(str).str.strip().str.title()
    conteo = conteo[(conteo != "") & (conteo.str.lower() != "nan")].value_counts().head(6)
    if conteo.empty:
        return _sin_datos(titulo)

    fig = go.Figure(go.Bar(
        x=conteo.index.tolist(),
        y=conteo.values.tolist(),
        width=0.45,
        text=conteo.values.tolist(),
        textposition="inside",
        insidetextanchor="end",
        textfont=dict(color="#ffffff", size=11),
        marker=dict(color="#0a2e46")
    ))
    fig.update_layout(**_layout_base(titulo, x_titulo="Provincia", y_titulo="Cantidad"))
    return fig


# 5. DONA: TIPO DE DOCUMENTO (DNI VS RUC)
def grafico_documentos(df):
    titulo = "Distribución por Tipo de Documento"
    if df is None or df.empty or "Tipo de Cliente" not in df.columns:
        return _sin_datos(titulo)

    serie = df["Tipo de Cliente"].dropna().astype(str).str.strip()
    serie = serie[(serie != "") & (serie.str.lower() != "nan")]
    mapeo = serie.map(lambda x: "RUC (Empresa)" if "Empresa" in x else "DNI (Persona)")
    conteo = mapeo.value_counts()

    fig = go.Figure(go.Pie(
        labels=conteo.index.tolist(),
        values=conteo.values.tolist(),
        hole=0.52,
        textinfo="percent",
        textfont=dict(size=11, color="#ffffff"),
        marker=dict(colors=["#0a2e46", "#f59e0b"], line=dict(color="#ffffff", width=2))
    ))
    layout = _layout_base(titulo)
    layout["margin"] = dict(l=15, r=15, t=48, b=35)
    layout["legend"] = dict(orientation="h", x=0.5, xanchor="center", y=-0.08, font=dict(size=11, color="#334155"))
    fig.update_layout(**layout)
    return fig


# 6. BARRAS: TOP DISTRITOS CON MAYOR MUESTREO
def grafico_dominios(df):
    titulo = "Muestras por Distrito"
    col_dist = None
    if df is not None and not df.empty:
        for c in df.columns:
            if "Distrito" in str(c):
                col_dist = c
                break

    if not col_dist:
        return _sin_datos(titulo)

    conteo = df[col_dist].dropna().astype(str).str.strip().str.title()
    conteo = conteo[(conteo != "") & (conteo.str.lower() != "nan")].value_counts().head(6)
    if conteo.empty:
        return _sin_datos(titulo)

    fig = go.Figure(go.Bar(
        x=conteo.index.tolist(),
        y=conteo.values.tolist(),
        width=0.45,
        text=conteo.values.tolist(),
        textposition="inside",
        insidetextanchor="end",
        textfont=dict(color="#ffffff", size=11),
        marker=dict(color="#0a2e46")
    ))
    fig.update_layout(**_layout_base(titulo, x_titulo="Distrito", y_titulo="Cantidad"))
    return fig


if __name__ == "__main__":
    df, resumen = procesar_datos()
    grafico_barras(df).show()
    grafico_dona(df).show()
    grafico_vendedores(df).show()
    grafico_categorias(df).show()
    grafico_documentos(df).show()
    grafico_dominios(df).show()