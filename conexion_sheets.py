import os
import re
from datetime import datetime
import gspread

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credenciales.json")
SPREADSHEET_ID = "1YVxma65TsdnAhKuGHIm9tZBi8b7qD0fJ91n9r87NDHw"
CERTIFICADO_SHEET_ID = "1JYYtoGBitAeXGl9cjB2KX5vuTqfQrcjtgmJjOVKnHPw"

# Opcional: pega el ID de una carpeta compartida de Google Drive para crear archivos separados
CARPETA_CADENAS_ID = ""


def _normalizar_fecha(fecha):
    """Limpia espacios y ceros iniciales en día/mes para evitar fallos de coincidencia."""
    return str(fecha).strip().lstrip("0").replace("/0", "/")


def obtener_datos():
    """Conecta a Google Sheets (hoja principal: Respuestas de formulario 2)."""
    if os.path.exists(CREDENTIALS_PATH) and os.path.getsize(CREDENTIALS_PATH) > 10:
        try:
            cliente = gspread.service_account(filename=CREDENTIALS_PATH)
            archivo = cliente.open_by_key(SPREADSHEET_ID)
            return archivo.sheet1.get_all_values()
        except Exception as e:
            print(f"[Aviso API Google - Hoja 1] {e}")
    return []


def obtener_seguimiento():
    """Lee la hoja principal (Respuestas de formulario 2) donde están las columnas W, X, Y."""
    if os.path.exists(CREDENTIALS_PATH) and os.path.getsize(CREDENTIALS_PATH) > 10:
        try:
            cliente = gspread.service_account(filename=CREDENTIALS_PATH)
            archivo = cliente.open_by_key(SPREADSHEET_ID)
            return archivo.sheet1.get_all_values()
        except Exception as e:
            print(f"[Aviso Seguimiento] {e}")
    return []


def actualizar_seguimiento(fecha_registro, nuevo_estado, nueva_observacion):
    """Busca la fila por Marca Temporal en la hoja principal y actualiza Estado (W), Observación (X) y Fecha (Y)."""
    if os.path.exists(CREDENTIALS_PATH) and os.path.getsize(CREDENTIALS_PATH) > 10:
        try:
            cliente = gspread.service_account(filename=CREDENTIALS_PATH)
            archivo = cliente.open_by_key(SPREADSHEET_ID)
            hoja = archivo.sheet1
            filas = hoja.get_all_values()

            fecha_buscada = _normalizar_fecha(fecha_registro)
            ahora = datetime.now().strftime("%d/%m/%Y %H:%M")

            for idx, fila in enumerate(filas[1:], start=2):
                if fila and _normalizar_fecha(fila[0]) == fecha_buscada:
                    hoja.update(
                        range_name=f"W{idx}:Y{idx}",
                        values=[[nuevo_estado, nueva_observacion, f"Actualizado: {ahora}"]]
                    )
                    return True
        except Exception as e:
            print(f"[Error al actualizar Seguimiento] {e}")
    return False


def exportar_a_hoja_calculo(filas_datos):
    """Crea una pestaña de reporte en Google Sheets con los registros filtrados y devuelve su URL en PDF."""
    if os.path.exists(CREDENTIALS_PATH) and os.path.getsize(CREDENTIALS_PATH) > 10:
        try:
            cliente = gspread.service_account(filename=CREDENTIALS_PATH)
            archivo = cliente.open_by_key(SPREADSHEET_ID)
            nombre_pestana = f"Reporte_LQA_{datetime.now().strftime('%d%m_%H%M%S')}"
            nueva_hoja = archivo.add_worksheet(title=nombre_pestana, rows=len(filas_datos) + 5, cols=10)
            nueva_hoja.update(range_name="A1", values=filas_datos)
            return f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=pdf&gid={nueva_hoja.id}&portrait=false&fitw=true"
        except Exception as e:
            print(f"[Error exportando a Google Sheets] {e}")
    return f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=pdf&portrait=false&fitw=true"


def _codigo_matriz(nombre_muestra):
    """Convierte el tipo de muestra en la sigla oficial de la leyenda T07 y su ensayo."""
    txt = str(nombre_muestra).lower()
    if "suelo" in txt:
        return "SUE", "F.Q"
    if "agua" in txt:
        return "AGU", "F.Q"
    if "savia" in txt:
        return "SVG", "NUTRI."
    if "foliar" in txt:
        return "FOL", "NUTRI."
    if "salin" in txt:
        return "SAL", "SALINID."
    if "enfermedad" in txt or "emfermedad" in txt or "especial" in txt:
        return "OTROS", "ESPECIAL"
    return "OTROS", "CARACT."


def _buscar_col_checkbox(fila, col_inicio):
    """Busca la primera columna con valor booleano (TRUE/FALSE) a la derecha de col_inicio."""
    for c in range(col_inicio + 1, len(fila) + 1):
        val = str(fila[c - 1]).strip().upper()
        if val in ("TRUE", "FALSE"):
            return c
    return None


def rellenar_cadena_custodia(datos):
    """Genera la Cadena de Custodia en Google Sheets con todos los campos, checkboxes y devuelve su URL en PDF."""
    if not (os.path.exists(CREDENTIALS_PATH) and os.path.getsize(CREDENTIALS_PATH) > 10):
        return f"https://docs.google.com/spreadsheets/d/{CERTIFICADO_SHEET_ID}/export?format=pdf&portrait=true&fitw=true"

    try:
        cliente = gspread.service_account(filename=CREDENTIALS_PATH)
        nombre_doc = f"Cadena_Custodia_{datos.get('ID', 'LQA')}_{datetime.now().strftime('%d%m_%H%M%S')}"
        es_archivo_aparte = False

        # 1. Intentar crear en archivo aparte si se configuró CARPETA_CADENAS_ID
        if CARPETA_CADENAS_ID.strip():
            try:
                nuevo_libro = cliente.copy(
                    CERTIFICADO_SHEET_ID,
                    title=nombre_doc,
                    copy_permissions=True,
                    folder_id=CARPETA_CADENAS_ID.strip()
                )
                try:
                    nuevo_libro.share("", perm_type="anyone", role="writer")
                except Exception:
                    pass
                hoja_trabajo = nuevo_libro.sheet1
                url_final = f"https://docs.google.com/spreadsheets/d/{nuevo_libro.id}/export?format=pdf&portrait=true&fitw=true"
                es_archivo_aparte = True
            except Exception as e_carpeta:
                print(f"[Aviso carpeta aparte] {e_carpeta}")

        # 2. Crear pestaña limpia dentro del libro principal
        if not es_archivo_aparte:
            archivo_plantilla = cliente.open_by_key(CERTIFICADO_SHEET_ID)
            archivo_principal = cliente.open_by_key(SPREADSHEET_ID)
            res_copia = archivo_plantilla.sheet1.copy_to(SPREADSHEET_ID)
            hoja_trabajo = archivo_principal.get_worksheet_by_id(res_copia["sheetId"])
            hoja_trabajo.update_title(f"Cadena_{datos.get('ID', 'LQA')}_{datetime.now().strftime('%H%M%S')}")
            url_final = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=pdf&gid={hoja_trabajo.id}&portrait=true&fitw=true"

        # 3. Reemplazar marcadores {{...}}
        reemplazos = {
            "{{ID}}": str(datos.get("ID", "")),
            "{{CON}}": str(datos.get("CON", "")),
            "{{FEC}}": str(datos.get("FEC", "")),
            "{{Razon_Social}}": str(datos.get("Razon_Social", "")),
            "{{RUC}}": str(datos.get("RUC", "")),
            "{{Celular}}": str(datos.get("Celular", "")),
            "{{Fundo}}": str(datos.get("Fundo", "")),
            "{{Distrito}}": str(datos.get("Distrito", "")),
            "{{Provincia}}": str(datos.get("Provincia", "")),
            "{{Nombres}}": str(datos.get("Nombres", "")),
            "{{Apellidos}}": str(datos.get("Apellidos", "")),
            "{{HENT}}": str(datos.get("HENT", "")),
            "{{FENT}}": str(datos.get("FENT", "")),
            "{{ESTADO}}": str(datos.get("ESTADO", "")),
            "{{OBSERVACIONES}}": str(datos.get("OBSERVACIONES", "")),
            "{{CORREO}}": str(datos.get("CORREO", "")),
        }

        patron = re.compile(r"\{\{.*?\}\}")
        for celda in hoja_trabajo.findall(patron):
            texto = celda.value
            for etiqueta, valor_real in reemplazos.items():
                if etiqueta in texto:
                    texto = texto.replace(etiqueta, valor_real)
            if texto != celda.value:
                hoja_trabajo.update_cell(celda.row, celda.col, texto)

        # 4. Rellenar tabla, celdas combinadas (OBSERVACIONES / RECIBIDO POR) y checkboxes
        valores = hoja_trabajo.get_all_values()
        muestreador = f"{datos.get('Nombres', '')} {datos.get('Apellidos', '')}".strip()
        correo = str(datos.get("CORREO", "")).strip()
        estado_txt = str(datos.get("ESTADO", "")).strip()
        obs_txt = str(datos.get("OBSERVACIONES", "")).strip()
        receptor = str(datos.get("RECEPTOR", "Encargado LQA")).strip()
        lista_muestras = [m.strip() for m in str(datos.get("MUESTRAS", "")).split(",") if m.strip()]

        es_rechazado = "RECHAZADO" in estado_txt.upper()
        es_analizado = "ANALIZADO" in estado_txt.upper() or "APROBADO" in estado_txt.upper() or "FINALIZADO" in estado_txt.upper()
        estado_corto = "RECHAZADO" if es_rechazado else ("APROBADO" if es_analizado else "EN PROCESO")

        updates = []
        formatos = []

        for r_idx, fila in enumerate(valores, start=1):
            for c_idx, val in enumerate(fila, start=1):
                celda_limpia = str(val).strip().upper()

                # E-MAIL
                if "E-MAIL" in celda_limpia and correo:
                    celda_a1 = gspread.utils.rowcol_to_a1(r_idx, c_idx + 2)
                    updates.append({"range": celda_a1, "values": [[correo]]})

                # MUESTREADO POR
                elif "MUESTREADO POR" in celda_limpia and muestreador:
                    celda_a1 = gspread.utils.rowcol_to_a1(r_idx, c_idx + 2)
                    updates.append({"range": celda_a1, "values": [[muestreador]]})

                # TABLA DE MUESTRAS
                elif "COD.LBRTO" in celda_limpia:
                    col_lbrto = c_idx
                    col_campo = c_idx + 1
                    col_hora = c_idx + 2
                    col_fecha = c_idx + 3
                    col_matriz = c_idx + 5
                    col_obs = c_idx + 11
                    cols_ensayo = {}

                    for offset_cab in (0, 1):
                        if r_idx - 1 + offset_cab < len(valores):
                            fila_cab = valores[r_idx - 1 + offset_cab]
                            for cc, h_val in enumerate(fila_cab, start=1):
                                h_up = str(h_val).strip().upper()
                                if "COD. CAMPO" in h_up:
                                    col_campo = cc
                                elif "MATRIZ" in h_up:
                                    col_matriz = cc
                                elif "SALINID" in h_up:
                                    cols_ensayo["SALINID."] = cc
                                elif "CARACT" in h_up:
                                    cols_ensayo["CARACT."] = cc
                                elif "NUTRI" in h_up:
                                    cols_ensayo["NUTRI."] = cc
                                elif "F.Q" in h_up:
                                    cols_ensayo["F.Q"] = cc
                                elif "ESPECIAL" in h_up:
                                    cols_ensayo["ESPECIAL"] = cc
                                elif "OBSERVACIONES" in h_up:
                                    col_obs = cc

                    fila_inicio_datos = r_idx + 2
                    for probe_r in range(r_idx + 1, min(r_idx + 5, len(valores) + 1)):
                        if any(str(x).strip().upper() in ("TRUE", "FALSE") for x in valores[probe_r - 1]):
                            fila_inicio_datos = probe_r
                            break

                    for i, m_nombre in enumerate(lista_muestras[:13]):
                        fila_dest = fila_inicio_datos + i
                        sigla_mat, tipo_ensayo = _codigo_matriz(m_nombre)
                        nombre_limpio = m_nombre.replace("Diagnostico de Emfermedades", "Diag. Enfermedades")

                        a1_lbrto = gspread.utils.rowcol_to_a1(fila_dest, col_lbrto)
                        a1_campo = gspread.utils.rowcol_to_a1(fila_dest, col_campo)
                        a1_hora = gspread.utils.rowcol_to_a1(fila_dest, col_hora)
                        a1_fecha = gspread.utils.rowcol_to_a1(fila_dest, col_fecha)
                        a1_mat = gspread.utils.rowcol_to_a1(fila_dest, col_matriz)
                        a1_obs = gspread.utils.rowcol_to_a1(fila_dest, col_obs)

                        updates.extend([
                            {"range": a1_lbrto, "values": [[f"{datos.get('ID', '')}-{i+1}"]]},
                            {"range": a1_campo, "values": [[f"M-{i+1:02d}"]]},
                            {"range": a1_hora, "values": [[str(datos.get("HENT", ""))]]},
                            {"range": a1_fecha, "values": [[str(datos.get("FEC", ""))]]},
                            {"range": a1_mat, "values": [[sigla_mat]]},
                            {"range": a1_obs, "values": [[f"{nombre_limpio} ({estado_corto})"]]},
                        ])

                        formatos.append({
                            "range": f"{a1_lbrto}:{a1_mat}",
                            "format": {"horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE", "textFormat": {"fontSize": 9}}
                        })
                        formatos.append({
                            "range": f"{a1_obs}:{gspread.utils.rowcol_to_a1(fila_dest, col_obs + 1)}",
                            "format": {"wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE", "textFormat": {"fontSize": 8}}
                        })

                        for nombre_ensayo, col_chk in cols_ensayo.items():
                            updates.append({"range": gspread.utils.rowcol_to_a1(fila_dest, col_chk), "values": [[nombre_ensayo == tipo_ensayo]]})

                # BLOQUE GRANDE OBSERVACIONES: (celda combinada B43:N44)
                elif celda_limpia.startswith("OBSERVACIONES:"):
                    celda_obs_gral = gspread.utils.rowcol_to_a1(r_idx, c_idx)
                    dictamen = (
                        f"OBSERVACIONES:   {estado_txt}  —  {obs_txt}"
                        if obs_txt and obs_txt.lower() != "sin observaciones"
                        else f"OBSERVACIONES:   {estado_txt}  —  Muestra verificada y registrada conforme al protocolo LQA."
                    )
                    updates.append({"range": celda_obs_gral, "values": [[dictamen]]})
                    formatos.append({
                        "range": celda_obs_gral,
                        "format": {"wrapStrategy": "WRAP", "verticalAlignment": "TOP", "textFormat": {"fontSize": 9}}
                    })

                # RECIBIDO POR: (celda combinada B47:F48)
                elif celda_limpia.startswith("RECIBIDO POR:"):
                    celda_rec = gspread.utils.rowcol_to_a1(r_idx, c_idx)
                    updates.append({"range": celda_rec, "values": [[f"RECIBIDO POR:  {receptor}"]]})

                # CHECKBOXES INFERIORES: CONDICIÓN DE LA MUESTRA EN LA RECEPCIÓN (SÍ / NO)
                elif celda_limpia in ("SÍ", "SI"):
                    col_chk_si = _buscar_col_checkbox(fila, c_idx)
                    if col_chk_si:
                        updates.append({"range": gspread.utils.rowcol_to_a1(r_idx, col_chk_si), "values": [[not es_rechazado]]})

                elif celda_limpia == "NO":
                    col_chk_no = _buscar_col_checkbox(fila, c_idx)
                    if col_chk_no:
                        updates.append({"range": gspread.utils.rowcol_to_a1(r_idx, col_chk_no), "values": [[es_rechazado]]})

                # CHECKBOXES INFERIORES: COTIZADO / FACTURADO / PAGO / ENVIADO
                elif any(k in celda_limpia for k in ("COTIZADO", "FACTURADO", "PAGO")):
                    col_chk_adm = _buscar_col_checkbox(fila, c_idx)
                    if col_chk_adm:
                        updates.append({"range": gspread.utils.rowcol_to_a1(r_idx, col_chk_adm), "values": [[es_analizado]]})

                elif "ENVIADO" in celda_limpia:
                    col_chk_env = _buscar_col_checkbox(fila, c_idx)
                    if col_chk_env:
                        updates.append({"range": gspread.utils.rowcol_to_a1(r_idx, col_chk_env), "values": [[es_analizado or es_rechazado]]})

        if updates:
            hoja_trabajo.batch_update(updates, value_input_option="USER_ENTERED")
        if formatos:
            hoja_trabajo.batch_format(formatos)

        print(f"[OK] Cadena de custodia perfeccionada en PDF: {nombre_doc}")
        return url_final

    except Exception as e:
        print(f"[ERROR CRÍTICO al rellenar Plantilla_T07]: {e}")
        return f"https://docs.google.com/spreadsheets/d/{CERTIFICADO_SHEET_ID}/export?format=pdf&portrait=true&fitw=true"


if __name__ == "__main__":
    print("Probando conexión con Google Sheets...")
    obtener_datos()
    obtener_seguimiento()