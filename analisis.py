import pandas as pd
from conexion_sheets import obtener_datos


def validar_dataframe(df):
    """Verifica que el DataFrame sea válido y no esté vacío."""
    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError("Se esperaba un DataFrame de pandas válido.")
    if df.empty:
        raise ValueError("El DataFrame recibido está vacío (0 registros).")


def limpiar_valor_celda(valor):
    """Convierte a texto limpio y detecta errores de fórmula de Google Sheets."""
    if isinstance(valor, (list, dict, tuple, set)):
        raise TypeError(f"Tipo de dato incompatible en celda: {type(valor).__name__}")
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.startswith("#") and texto.endswith("!"):  # Ej. #REF!, #VALUE!, #N/A
        raise ValueError(f"La celda contiene un error de fórmula de Google Sheets: '{texto}'")
    return texto


def contar_registros(df):
    """Cuenta el total de solicitudes válidas recibidas en el laboratorio."""
    try:
        validar_dataframe(df)
        return len(df)
    except (TypeError, ValueError) as e:
        print(f"[Aviso contar_registros]: {e}")
        return 0


def contar_estado(df, columna, valor_buscado):
    """Cuenta coincidencias exactas en una columna controlando claves ausentes y tipos."""
    try:
        validar_dataframe(df)
        if columna not in df.columns:
            raise KeyError(f"La columna '{columna}' no existe en la hoja.")
        if not isinstance(valor_buscado, str):
            raise TypeError("El valor buscado debe ser una cadena de texto.")

        total = 0
        objetivo = valor_buscado.strip().lower()
        for numero, valor in enumerate(df[columna], start=2):
            try:
                texto = limpiar_valor_celda(valor).lower()
                if texto == objetivo:
                    total += 1
            except (ValueError, TypeError) as e:
                print(f"[Fila {numero} - {columna}]: {e}")
        return total

    except KeyError as e:
        print(f"[Error contar_estado]: {e}")
        return 0
    except (TypeError, ValueError) as e:
        print(f"[Aviso contar_estado]: {e}")
        return 0


def contar_ensayos_totales(df, errores_log=None):
    """
    Regla de negocio LQA: Calcula el total de ensayos analíticos individuales
    (una solicitud puede incluir múltiples matrices separadas por coma).
    """
    total_ensayos = 0
    try:
        validar_dataframe(df)
        columna = "Tipo de Muestra"
        if columna not in df.columns:
            raise KeyError(f"Falta la columna obligatoria '{columna}'.")

        for numero, valor in enumerate(df[columna], start=2):
            try:
                texto = limpiar_valor_celda(valor)
                if texto == "":
                    raise ValueError("Solicitud sin matriz de análisis especificada.")
                if texto.replace(".", "").isdigit():
                    raise ValueError(f"Se esperaba nombre de matriz, se recibió número: '{texto}'")

                matrices = [m.strip() for m in texto.split(",") if m.strip()]
                if not matrices:
                    raise ValueError("Lista de matrices vacía tras limpiar separadores.")

                total_ensayos += len(matrices)

            except (ValueError, TypeError) as e:
                msg = f"Fila {numero} ({columna}): {e}"
                print(f"[Regla LQA - Ensayos] {msg}")
                if errores_log is not None:
                    errores_log.append(msg)

        return total_ensayos

    except KeyError as e:
        print(f"[Error contar_ensayos_totales]: {e}")
        return 0
    except (TypeError, ValueError) as e:
        print(f"[Aviso contar_ensayos_totales]: {e}")
        return 0


def agrupar_por_columna(df, columna, etiqueta_vacio="No especificado", errores_log=None):
    """Agrupa y cuenta valores válidos de una columna controlando errores de Sheets."""
    conteo = {}
    try:
        validar_dataframe(df)
        if columna not in df.columns:
            raise KeyError(f"Falta la columna obligatoria '{columna}'.")

        for numero, valor in enumerate(df[columna], start=2):
            try:
                texto = limpiar_valor_celda(valor)
                if texto == "":
                    texto = etiqueta_vacio
                conteo[texto] = conteo.get(texto, 0) + 1
            except (ValueError, TypeError) as e:
                msg = f"Fila {numero} ({columna}): {e}"
                print(f"[Validación Columna] {msg}")
                if errores_log is not None:
                    errores_log.append(msg)
                conteo["Dato Inválido"] = conteo.get("Dato Inválido", 0) + 1

        return conteo

    except KeyError as e:
        print(f"[Error agrupar_por_columna]: {e}")
        return {}
    except (TypeError, ValueError) as e:
        print(f"[Aviso agrupar_por_columna]: {e}")
        return {}


def agrupar_por_dominio_correo(df, errores_log=None):
    """Valida el formato de correo electrónico de clientes y agrupa por dominio."""
    try:
        validar_dataframe(df)
        columna = "Correo Electrónico"
        if columna not in df.columns:
            raise KeyError(f"Falta la columna '{columna}'.")

        dominios_validos = []
        for numero, valor in enumerate(df[columna], start=2):
            try:
                correo = limpiar_valor_celda(valor).lower()
                if correo == "":
                    dominios_validos.append("Sin Correo")
                    continue

                # Regla de negocio: formato básico de correo electrónico
                if "@" not in correo or "." not in correo.split("@")[-1]:
                    raise ValueError(f"Formato de correo inválido: '{correo}'")

                dominio = correo.split("@")[-1]
                dominios_validos.append(dominio)

            except (ValueError, TypeError) as e:
                msg = f"Fila {numero} (Correo): {e}"
                print(f"[Validación Correo] {msg}")
                if errores_log is not None:
                    errores_log.append(msg)
                dominios_validos.append("Correo Inválido")

        return pd.Series(dominios_validos).value_counts().head(5).to_dict()

    except KeyError as e:
        print(f"[Error agrupar_por_dominio_correo]: {e}")
        return {}
    except (TypeError, ValueError) as e:
        print(f"[Aviso agrupar_por_dominio_correo]: {e}")
        return {}


def conteo_documentos(df, errores_log=None):
    """Valida DNI (8 dígitos) y RUC peruano (11 dígitos iniciando en 10, 15, 17 o 20)."""
    resultado = {"Con DNI": 0, "Con RUC": 0, "Documentos Inválidos": 0}
    try:
        validar_dataframe(df)

        col_dni = next((col for col in df.columns if "dni" in col.lower()), None)
        col_ruc = next((col for col in df.columns if "ruc" in col.lower()), None)

        if not col_dni and not col_ruc:
            raise KeyError(f"No se encontraron columnas de DNI ni RUC. Disponibles: {list(df.columns)}")

        for col, longitud, clave in [(col_dni, 8, "Con DNI"), (col_ruc, 11, "Con RUC")]:
            if not col:
                continue

            for numero, valor in enumerate(df[col], start=2):
                try:
                    doc_limpio = limpiar_valor_celda(valor)
                    if doc_limpio == "":
                        continue

                    if doc_limpio.endswith(".0"):
                        doc_limpio = doc_limpio[:-2]
                    doc_limpio = doc_limpio.rstrip(".")

                    if not doc_limpio.isdigit():
                        raise ValueError(f"Contiene letras o símbolos no permitidos: '{doc_limpio}'")
                    if len(doc_limpio) != longitud:
                        raise ValueError(
                            f"Debe tener {longitud} dígitos, tiene {len(doc_limpio)}: '{doc_limpio}'"
                        )
                    if longitud == 11 and not doc_limpio.startswith(("10", "15", "17", "20")):
                        raise ValueError(f"Prefijo de RUC peruano inválido: '{doc_limpio}'")

                    resultado[clave] += 1

                except (ValueError, TypeError) as e:
                    msg = f"Fila {numero} ({col}): {e}"
                    print(f"[Validación Documento] {msg}")
                    if errores_log is not None:
                        errores_log.append(msg)
                    resultado["Documentos Inválidos"] += 1

    except KeyError as e:
        print(f"[Error conteo_documentos]: {e}")
    except (TypeError, ValueError) as e:
        print(f"[Aviso conteo_documentos]: {e}")

    return resultado


def procesar_datos():
    errores_detectados = []
    resumen_vacio = {
        "total_registros": 0,
        "total_ensayos": 0,
        "total_personas": 0,
        "total_empresas": 0,
        "porcentaje_empresas": 0,
        "por_tipo": {},
        "por_muestra": {},
        "dominios_correo": {},
        "documentos": {"Con DNI": 0, "Con RUC": 0, "Documentos Inválidos": 0},
        "errores_detectados": errores_detectados,
        "columnas": []
    }

    try:
        datos = obtener_datos()

        if datos is None:
            raise ValueError("La conexión no devolvió datos (None).")
        if not isinstance(datos, list) or len(datos) < 2:
            raise ValueError("La hoja no tiene suficientes filas (se requieren encabezados y al menos 1 registro).")

        encabezados = [str(col).strip() for col in datos[0]]
        filas = [f for f in datos[1:] if any(str(celda).strip() != "" for celda in f)]

        if not filas:
            raise ValueError("Todas las filas recuperadas están vacías.")

        df = pd.DataFrame(filas, columns=encabezados)
        df = df.loc[:, df.columns != ""]

        total = contar_registros(df)
        total_ensayos = contar_ensayos_totales(df, errores_detectados)
        total_personas = contar_estado(df, "Tipo de Cliente", "Persona")
        total_empresas = contar_estado(df, "Tipo de Cliente", "Empresa")

        porcentaje_empresas = round((total_empresas / total) * 100, 1) if total > 0 else 0

        resumen = {
            "total_registros": total,
            "total_ensayos": total_ensayos,
            "total_personas": total_personas,
            "total_empresas": total_empresas,
            "porcentaje_empresas": porcentaje_empresas,
            "por_tipo": agrupar_por_columna(df, "Tipo de Cliente", errores_log=errores_detectados),
            "por_muestra": agrupar_por_columna(df, "Tipo de Muestra", errores_log=errores_detectados),
            "dominios_correo": agrupar_por_dominio_correo(df, errores_log=errores_detectados),
            "documentos": conteo_documentos(df, errores_log=errores_detectados),
            "errores_detectados": errores_detectados,
            "columnas": list(df.columns)
        }

        return df, resumen

    except KeyError as e:
        print(f"[Error de columna en procesar_datos]: {e}")
        return None, resumen_vacio
    except ValueError as e:
        print(f"[Error crítico de datos en procesar_datos]: {e}")
        return None, resumen_vacio
    except TypeError as e:
        print(f"[Error de tipo de dato en procesar_datos]: {e}")
        return None, resumen_vacio
    except Exception as e:
        print(f"[Error inesperado en procesar_datos]: {type(e).__name__} - {e}")
        return None, resumen_vacio


if __name__ == "__main__":
    df, resumen = procesar_datos()

    print("==========================================")
    print("      REPORTE DE ANÁLISIS DE DATOS        ")
    print("==========================================")
    print(f"📌 Total de Registros: {resumen['total_registros']}")
    print(f"🧪 Total de Ensayos:   {resumen['total_ensayos']}")
    print(f"👤 Total de Personas:  {resumen['total_personas']}")
    print(f"🏢 Total de Empresas:  {resumen['total_empresas']}")
    print(f"📈 % Corporativo:     {resumen['porcentaje_empresas']}%")
    print("------------------------------------------")
    print("📊 Distribución por Tipo de Cliente:")
    for tipo, cantidad in resumen["por_tipo"].items():
        print(f"   - {tipo}: {cantidad}")
    print("------------------------------------------")
    print("🆔 Documentos Ingresados:")
    for doc, cantidad in resumen["documentos"].items():
        print(f"   - {doc}: {cantidad}")
    print("------------------------------------------")
    print(f"⚠️  Alertas / Excepciones controladas: {len(resumen['errores_detectados'])}")
    for err in resumen["errores_detectados"]:
        print(f"   * {err}")
    print("==========================================")