import socket
from collections import Counter
import plotly.graph_objects as go
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from analisis import procesar_datos
from conexion_sheets import (
    obtener_seguimiento,
    actualizar_seguimiento,
    exportar_a_hoja_calculo,
    rellenar_cadena_custodia
)
from graficos import (
    grafico_barras,
    grafico_dona,
    grafico_vendedores,
    grafico_categorias,
    grafico_documentos,
    grafico_dominios
)

app = Flask(__name__)
app.secret_key = "lqa_vallegrande_t07_clave_secreta"

ENCARGADOS_LQA = {
    "jean.chulluncuy@vallegrande.edu.pe": "LQA2026",
    "gregory.guzman@vallegrande.edu.pe": "LQA2026",
    "admin.lqa@vallegrande.edu.pe": "ValleGrande2026"
}


def obtener_ip_red():
    """Obtiene la IP local de la PC en la red Wi-Fi para que otros dispositivos puedan conectarse."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def fig_a_html(fig):
    if isinstance(fig, str):
        return fig
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"responsive": True, "displayModeBar": False}
    )


def descomponer_matrices(lista_registros):
    """Separa los paquetes combinados por coma y genera tarjetas y gráficos corporativos limpios."""
    conteo_individual = Counter()
    estado_por_matriz = {}
    totales_estado = {"Aprobados": 0, "En Proceso": 0, "Observados": 0, "Rechazados": 0}

    for r in lista_registros:
        raw = str(r.get("muestra", "")).strip()
        if not raw or raw == "-":
            continue
        est = str(r.get("estado", "En Proceso"))

        if "Aprobado" in est or "Finalizado" in est:
            totales_estado["Aprobados"] += 1
        elif "Rechazado" in est:
            totales_estado["Rechazados"] += 1
        elif "Observado" in est:
            totales_estado["Observados"] += 1
        else:
            totales_estado["En Proceso"] += 1

        partes = [p.strip() for p in raw.split(",") if p.strip()]
        for p in partes:
            nombre = p.replace("Diagnostico de Emfermedades", "Diagnóstico de Enfermedades")
            conteo_individual[nombre] += 1
            if nombre not in estado_por_matriz:
                estado_por_matriz[nombre] = {"aprobados": 0, "proceso": 0, "observados": 0, "rechazados": 0}
            if "Aprobado" in est or "Finalizado" in est:
                estado_por_matriz[nombre]["aprobados"] += 1
            elif "Rechazado" in est:
                estado_por_matriz[nombre]["rechazados"] += 1
            elif "Observado" in est:
                estado_por_matriz[nombre]["observados"] += 1
            else:
                estado_por_matriz[nombre]["proceso"] += 1

    ranking = conteo_individual.most_common()
    total_ensayos = sum(conteo_individual.values())

    paleta = [
        "#16a34a", "#f59e0b", "#64748b", "#ef4444",
        "#0a2e46", "#0284c7", "#7c3aed", "#0d9488", "#ea580c"
    ]

    tarjetas_matrices = []
    for idx, (nombre, cant) in enumerate(ranking):
        porcentaje = round((cant / total_ensayos) * 100, 1) if total_ensayos else 0
        desglose_est = estado_por_matriz.get(nombre, {"aprobados": 0, "proceso": 0, "rechazados": 0})
        tarjetas_matrices.append({
            "nombre": nombre,
            "cantidad": cant,
            "porcentaje": porcentaje,
            "color": paleta[idx % len(paleta)],
            "aprobados": desglose_est["aprobados"],
            "proceso": desglose_est["proceso"],
            "rechazados": desglose_est["rechazados"]
        })

    if ranking:
        labels_dona = [k for k, v in totales_estado.items() if v > 0]
        vals_dona = [v for v in totales_estado.values() if v > 0]
        mapa_colores = {
            "Aprobados": "#16a34a",
            "En Proceso": "#f59e0b",
            "Observados": "#64748b",
            "Rechazados": "#ef4444"
        }

        fig_izq = go.Figure(go.Pie(
            labels=labels_dona,
            values=vals_dona,
            hole=0.52,
            textinfo="percent",
            textfont=dict(size=11, color="#ffffff"),
            marker=dict(colors=[mapa_colores[k] for k in labels_dona], line=dict(color="#ffffff", width=2)),
            hovertemplate="<b>%{label}</b><br>Muestras: %{value}<br>Porcentaje: %{percent}<extra></extra>"
        ))
        fig_izq.update_layout(
            autosize=True,
            title=dict(text="Distribución Global de Muestras", font=dict(size=14, color="#1e293b"), x=0.02, y=0.95),
            height=330,
            margin=dict(l=20, r=20, t=48, b=25),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            legend=dict(orientation="v", x=0.80, y=0.78, font=dict(size=11, color="#334155"))
        )

        nombres_cortos = [
            x[0].replace("Análisis de ", "").replace("Diagnóstico de ", "Diag. ")[:14]
            for x in ranking
        ]
        aprob_vals = [estado_por_matriz[x[0]]["aprobados"] for x in ranking]
        rech_vals = [estado_por_matriz[x[0]]["rechazados"] for x in ranking]
        proc_vals = [estado_por_matriz[x[0]]["proceso"] for x in ranking]

        fig_der = go.Figure(data=[
            go.Bar(name="Aprobados", x=nombres_cortos, y=aprob_vals, marker_color="#16a34a"),
            go.Bar(name="Rechazados", x=nombres_cortos, y=rech_vals, marker_color="#ef4444"),
            go.Bar(name="En Proceso", x=nombres_cortos, y=proc_vals, marker_color="#f59e0b")
        ])
        fig_der.update_layout(
            autosize=True,
            barmode="group",
            title=dict(text="Muestras por Tipo de Matriz", font=dict(size=14, color="#1e293b"), x=0.02, y=0.95),
            height=330,
            margin=dict(l=48, r=110, t=48, b=60),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            legend=dict(orientation="v", x=1.02, y=0.88, font=dict(size=11, color="#334155")),
            xaxis=dict(showgrid=False, linecolor="#e2e8f0", tickangle=30, tickfont=dict(size=10, color="#64748b")),
            yaxis=dict(title="N° de registros", showgrid=True, gridcolor="#f1f5f9", zeroline=False, tickfont=dict(size=10, color="#64748b"))
        )
    else:
        fig_izq = "<p style='text-align:center;color:#64748b;padding:2rem;'>Sin datos de matrices</p>"
        fig_der = "<p style='text-align:center;color:#64748b;padding:2rem;'>Sin datos de matrices</p>"

    return tarjetas_matrices, total_ensayos, fig_a_html(fig_izq), fig_a_html(fig_der)


def construir_registros():
    """Procesa y cruza Respuestas de Formulario con Panel_Seguimiento."""
    df, resumen = procesar_datos()
    datos_seg = obtener_seguimiento()
    mapa_seg = {}

    if len(datos_seg) > 1:
        for fila in datos_seg[1:]:
            if len(fila) >= 7:
                clave_fecha = str(fila[0]).strip()
                estado = str(fila[6]).strip() if len(fila) > 6 else ""
                obs = str(fila[7]).strip() if len(fila) > 7 else ""
                notif = str(fila[8]).strip() if len(fila) > 8 else ""
                mapa_seg[clave_fecha] = {
                    "estado": estado,
                    "observacion": obs,
                    "notificacion": notif
                }

    ip_pc = obtener_ip_red()
    registros = []
    if df is not None and not df.empty:
        for idx, row in df.iterrows():
            tipo = str(row.get("Tipo de Cliente", "Persona")).strip()
            fecha = str(row.get("Marca temporal", "-")).strip()
            correo = str(row.get("Correo Electrónico", "") or row.get("Dirección de correo electrónico", "")).strip()
            celular = str(row.get("Teléfono", "") or row.get("Celular", "") or row.get("Número de Celular", "")).strip()
            doc = "-"
            distrito = ""

            for col_name, val in row.items():
                valor = str(val).strip()
                if not valor or valor.lower() == "nan":
                    continue
                if "Distrito" in str(col_name) and not distrito:
                    distrito = valor
                elif tipo == "Empresa" and "RUC" in str(col_name) and doc == "-":
                    doc = valor
                elif tipo != "Empresa" and "DNI" in str(col_name) and doc == "-":
                    doc = valor
                elif ("Celular" in str(col_name) or "Teléfono" in str(col_name)) and not celular:
                    celular = valor
                elif "@" in valor and not correo:
                    correo = valor

            nombres = str(row.get("Nombres Completos", "")).strip()
            apellidos = str(row.get("Apellidos Completos", "")).strip()
            if tipo == "Empresa":
                cliente = str(row.get("Nombre de la Empresa", "") or row.get("Razón Social", "-")).strip()
            else:
                cliente = f"{nombres} {apellidos}".strip()

            prov = str(row.get("Provincia", "")).strip()
            procedencia = f"{prov} · {distrito}".strip(" ·") if (prov or distrito) else "-"

            seg = mapa_seg.get(fecha, {})
            estado = seg.get("estado") or "En Proceso"
            observacion = seg.get("observacion") or "Sin observaciones"
            notificacion = seg.get("notificacion") or "Pendiente"
            reg_id = idx + 1

            registros.append({
                "id": reg_id,
                "codigo_cert": f"LQA-2026-{reg_id:04d}",
                "url_publica": f"http://{ip_pc}:5000/verificar/{reg_id}",
                "fecha": fecha,
                "tipo": tipo,
                "cliente": cliente or "-",
                "nombres": nombres or cliente or "-",
                "apellidos": apellidos,
                "documento": doc,
                "celular": celular,
                "correo": correo,
                "provincia": prov,
                "distrito": distrito,
                "procedencia": procedencia,
                "fundo": str(row.get("Fundo o lugar de origen", "-") or "-").strip(),
                "muestra": str(row.get("Tipo de Muestra", "-") or "-").strip(),
                "estado": estado,
                "observacion": observacion,
                "notificacion": notificacion
            })

    return df, resumen, registros


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("modo_google") == "1":
            session["usuario"] = "Encargado LQA (@vallegrande.edu.pe)"
            return redirect(url_for("dashboard"))

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if email in ENCARGADOS_LQA and ENCARGADOS_LQA[email] == password:
            session["usuario"] = email
            return redirect(url_for("dashboard"))
        else:
            error = "Correo institucional o contraseña incorrectos."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))


@app.route("/actualizar_muestra", methods=["POST"])
def actualizar_muestra():
    if "usuario" not in session:
        return redirect(url_for("login"))

    fecha = request.form.get("fecha", "").strip()
    estado = request.form.get("estado", "En Proceso").strip()
    observacion = request.form.get("observacion", "").strip()

    actualizar_seguimiento(fecha, estado, observacion)
    return redirect(url_for("dashboard"))


@app.route("/exportar_sheets", methods=["POST"])
def exportar_sheets():
    if "usuario" not in session:
        return jsonify({"ok": False}), 401

    datos = request.get_json(silent=True) or {}
    filas = datos.get("filas", [])
    if not filas:
        return jsonify({"ok": False, "mensaje": "No hay filas para exportar"})

    url_hoja = exportar_a_hoja_calculo(filas)
    return jsonify({"ok": True, "url": url_hoja})


@app.route("/")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))

    df, resumen, registros = construir_registros()

    total_registros = resumen.get("total_registros", 0)
    total_personas = resumen.get("total_personas", 0)
    total_empresas = resumen.get("total_empresas", 0)

    tarjetas_matrices, total_ensayos, graf_mat_barras, graf_mat_dona = descomponer_matrices(registros)

    matriz_top = "Suelo"
    if tarjetas_matrices:
        matriz_top = tarjetas_matrices[0]["nombre"].replace("Análisis de ", "").replace("Análisis ", "")

    analizados = [r for r in registros if "Finalizado" in r["estado"] or "Aprobado" in r["estado"]]
    en_proceso = [r for r in registros if "Proceso" in r["estado"]]
    rechazados = [r for r in registros if "Rechazado" in r["estado"]]

    return render_template(
        "dashboard.html",
        usuario=session.get("usuario", "Encargado LQA"),
        total_registros=total_registros,
        total_personas=total_personas,
        total_empresas=total_empresas,
        matriz_top=matriz_top,
        grafico_barras=fig_a_html(grafico_barras(df)),
        grafico_dona=fig_a_html(grafico_dona(df)),
        grafico_categorias=fig_a_html(grafico_categorias(df, registros)),
        grafico_vendedores=fig_a_html(grafico_vendedores(df)),
        grafico_documentos=fig_a_html(grafico_documentos(df)),
        grafico_dominios=fig_a_html(grafico_dominios(df)),
        registros=registros,
        analizados=analizados,
        en_proceso=en_proceso,
        rechazados=rechazados,
        tarjetas_matrices=tarjetas_matrices,
        total_ensayos=total_ensayos,
        graf_mat_barras=graf_mat_barras,
        graf_mat_dona=graf_mat_dona
    )


@app.route("/cadena_custodia/<int:reg_id>")
def generar_cadena_custodia(reg_id):
    """Genera y abre el documento de Cadena de Custodia en Google Sheets autorrellenado completo."""
    if "usuario" not in session:
        return redirect(url_for("login"))

    _, _, registros = construir_registros()
    muestra = next((r for r in registros if r["id"] == reg_id), None)
    if not muestra:
        return "Registro no encontrado", 404

    partes_fecha = str(muestra["fecha"]).split(" ")
    solo_fecha = partes_fecha[0] if len(partes_fecha) > 0 else ""
    solo_hora = partes_fecha[1] if len(partes_fecha) > 1 else ""

    estado_raw = str(muestra["estado"]).strip()
    if "Rechazado" in estado_raw:
        estado_texto = "RECHAZADO (No Conforme)"
    elif "Finalizado" in estado_raw or "Aprobado" in estado_raw:
        estado_texto = f"ANALIZADO / {estado_raw.upper()}"
    else:
        estado_texto = estado_raw.upper()

    datos = {
        "ID": muestra["codigo_cert"],
        "CON": "",
        "FEC": solo_fecha,
        "Razon_Social": muestra["cliente"],
        "RUC": muestra["documento"],
        "Celular": muestra["celular"],
        "Fundo": muestra["fundo"],
        "Distrito": muestra["distrito"],
        "Provincia": muestra["provincia"],
        "Nombres": muestra["nombres"],
        "Apellidos": muestra["apellidos"],
        "HENT": solo_hora,
        "FENT": solo_fecha,
        "ESTADO": estado_texto,
        "OBSERVACIONES": muestra["observacion"],
        "CORREO": muestra["correo"],
        "MUESTRAS": muestra["muestra"],
        "RECEPTOR": session.get("usuario", "Encargado LQA"),
    }

    url_documento = rellenar_cadena_custodia(datos)
    return redirect(url_documento)


@app.route("/certificado/<int:reg_id>")
def ver_certificado(reg_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    _, _, registros = construir_registros()
    muestra = next((r for r in registros if r["id"] == reg_id), None)
    if not muestra:
        return "Certificado no encontrado", 404

    url_verificacion = muestra["url_publica"]
    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=100x100&data={url_verificacion}"

    es_rechazado = "Rechazado" in muestra["estado"]
    es_finalizado = "Finalizado" in muestra["estado"]

    if es_rechazado:
        color_borde = "#991b1b"
        color_bg_cod = "#fee2e2"
        titulo_doc = "CONSTANCIA TÉCNICA DE RECHAZO DE MUESTRA"
        titulo_obs = "Motivo Técnico del Rechazo / No Conformidad:"
    elif es_finalizado:
        color_borde = "#065f46"
        color_bg_cod = "#ecfdf5"
        titulo_doc = "CERTIFICADO DE ANÁLISIS FINALIZADO DE MUESTRA"
        titulo_obs = "Resultados y Dictamen Técnico del Laboratorio:"
    else:
        color_borde = "#047857"
        color_bg_cod = "#d1fae5"
        titulo_doc = "CERTIFICADO DE APROBACIÓN Y CONTROL DE MUESTRA"
        titulo_obs = "Dictamen de Aprobación / Observaciones Técnicas:"

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>{titulo_doc} {muestra['codigo_cert']} - LQA Valle Grande</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #e2e8f0; padding: 2rem; }}
            .hoja {{ max-width: 760px; margin: 0 auto; background: #fff; padding: 2.5rem 3rem; border-radius: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); border-top: 8px solid {color_borde}; }}
            .top {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid {color_borde}; padding-bottom: 1rem; margin-bottom: 1.5rem; gap: 1rem; }}
            h1 {{ font-size: 1.25rem; color: {color_borde}; margin: 0; }}
            .sub {{ font-size: 0.84rem; color: #475569; }}
            .codigo {{ background: {color_bg_cod}; color: {color_borde}; padding: 0.35rem 0.75rem; border-radius: 6px; font-weight: bold; font-size: 0.88rem; margin-bottom: 0.4rem; display: inline-block; }}
            table {{ width: 100%; border-collapse: collapse; margin: 1.2rem 0; font-size: 0.9rem; }}
            td {{ padding: 0.6rem 0.8rem; border: 1px solid #cbd5e1; }}
            td.lbl {{ background: #f8fafc; font-weight: 700; width: 32%; color: #334155; }}
            .obs-box {{ background: #f8fafc; border-left: 4px solid {color_borde}; padding: 1rem; margin-top: 1rem; font-size: 0.9rem; }}
            .firmas {{ display: flex; justify-content: space-between; margin-top: 3.5rem; text-align: center; font-size: 0.82rem; color: #475569; }}
            .linea {{ border-top: 1px solid #64748b; width: 220px; padding-top: 0.4rem; }}
            .acciones {{ text-align: center; margin-bottom: 1rem; }}
            button {{ background: {color_borde}; color: #fff; border: none; padding: 0.6rem 1.2rem; border-radius: 6px; cursor: pointer; font-weight: bold; }}
            @media print {{ .acciones {{ display: none; }} body {{ background: #fff; padding: 0; }} .hoja {{ box-shadow: none; }} }}
        </style>
    </head>
    <body>
        <div class="acciones">
            <button onclick="window.print()">🖨️ Imprimir / Guardar Documento PDF</button>
        </div>
        <div class="hoja">
            <div class="top">
                <div>
                    <h1>LABORATORIO DE QUÍMICA AGRÍCOLA (LQA)</h1>
                    <div class="sub">Instituto de Educación Superior Valle Grande · Cañete, Perú</div>
                </div>
                <div style="text-align:right;">
                    <div class="codigo">N° {muestra['codigo_cert']}</div><br>
                    <img src="{qr_api}" alt="QR Validación" style="border:1px solid #cbd5e1; padding:3px; border-radius:4px;">
                    <div style="font-size:0.65rem; color:#64748b; margin-top:2px;">Escanea para verificar</div>
                </div>
            </div>
            <h2 style="text-align:center; font-size:1.1rem; color:#0f172a; margin-bottom:1rem;">{titulo_doc}</h2>
            <table>
                <tr><td class="lbl">Solicitante / Empresa:</td><td>{muestra['cliente']}</td></tr>
                <tr><td class="lbl">DNI / RUC:</td><td>{muestra['documento']}</td></tr>
                <tr><td class="lbl">Procedencia:</td><td>{muestra['procedencia']} ({muestra['fundo']})</td></tr>
                <tr><td class="lbl">Tipo de Análisis:</td><td><strong>{muestra['muestra']}</strong></td></tr>
                <tr><td class="lbl">Fecha de Recepción:</td><td>{muestra['fecha']}</td></tr>
                <tr><td class="lbl">Estado de Control:</td><td style="color:{color_borde};"><strong>{muestra['estado']}</strong></td></tr>
            </table>
            <div class="obs-box">
                <strong>{titulo_obs}</strong><br>
                {muestra['observacion']}
            </div>
            <div class="firmas">
                <div class="linea">Responsable Técnico LQA<br>{session.get('usuario')}</div>
                <div class="linea">Jefatura de Laboratorio<br>Instituto Valle Grande</div>
            </div>
        </div>
    </body>
    </html>
    """


@app.route("/verificar/<int:reg_id>")
def verificar_publico(reg_id):
    """Vista pública sin contraseña para verificar certificados o constancias escaneadas o abiertas desde el correo."""
    _, _, registros = construir_registros()
    muestra = next((r for r in registros if r["id"] == reg_id), None)
    if not muestra:
        return "<h2 style='font-family:sans-serif;text-align:center;margin-top:3rem;'>❌ Documento no encontrado o inválido</h2>", 404

    es_rechazado = "Rechazado" in muestra["estado"]
    banner_bg = "#991b1b" if es_rechazado else "#065f46"
    icono = "⚠️" if es_rechazado else "✅"
    titulo_verif = (
        "CONSTANCIA DE RECHAZO (VERIFICADA)"
        if es_rechazado else
        f"CERTIFICADO OFICIAL ({muestra['estado'].upper()})"
    )
    badge_bg = "#fee2e2" if es_rechazado else "#dcfce7"
    badge_col = "#991b1b" if es_rechazado else "#166534"

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Certificado Oficial {muestra['codigo_cert']} · LQA</title>
        <style>
            body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #f1f5f9; padding: 1.2rem; margin: 0; }}
            .card {{ max-width: 520px; margin: 1rem auto; background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 8px 20px rgba(0,0,0,0.08); }}
            .banner {{ background: {banner_bg}; color: #fff; padding: 1.4rem; text-align: center; }}
            .check {{ font-size: 2.2rem; display: block; margin-bottom: 0.3rem; }}
            .banner h1 {{ font-size: 1.1rem; margin: 0; }}
            .banner p {{ font-size: 0.8rem; color: rgba(255,255,255,0.85); margin: 0.25rem 0 0; }}
            .body {{ padding: 1.4rem; font-size: 0.9rem; color: #1e293b; }}
            .dato {{ border-bottom: 1px solid #f1f5f9; padding: 0.65rem 0; }}
            .dato span {{ display: block; font-size: 0.72rem; text-transform: uppercase; color: #64748b; font-weight: 700; }}
            .badge {{ display: inline-block; background: {badge_bg}; color: {badge_col}; padding: 0.25rem 0.65rem; border-radius: 999px; font-weight: 700; font-size: 0.82rem; margin-top: 0.2rem; }}
            .btn-print {{ display: block; width: 100%; margin-top: 1rem; padding: 0.7rem; background: {banner_bg}; color: #fff; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }}
            @media print {{ .btn-print {{ display: none; }} }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="banner">
                <span class="check">{icono}</span>
                <h1>{titulo_verif}</h1>
                <p>Laboratorio de Química Agrícola · Instituto Valle Grande</p>
            </div>
            <div class="body">
                <div class="dato"><span>Código Oficial</span><strong>{muestra['codigo_cert']}</strong></div>
                <div class="dato"><span>Cliente / Empresa</span><strong>{muestra['cliente']}</strong></div>
                <div class="dato"><span>DNI / RUC</span>{muestra['documento']}</div>
                <div class="dato"><span>Tipo de Análisis</span><strong>{muestra['muestra']}</strong></div>
                <div class="dato"><span>Procedencia</span>{muestra['procedencia']} ({muestra['fundo']})</div>
                <div class="dato"><span>Fecha de Recepción</span>{muestra['fecha']}</div>
                <div class="dato"><span>Estado</span><div class="badge">{muestra['estado']}</div></div>
                <div class="dato" style="border:none;"><span>Dictamen / Observaciones</span>{muestra['observacion']}</div>
                <button class="btn-print" onclick="window.print()">🖨️ Descargar / Imprimir Constancia PDF</button>
            </div>
        </div>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)