import pandas as pd
from conexion_sheets import obtener_datos


def validar_dataframe(df):
    """Verifica que el DataFrame sea válido y no esté vacío."""
    if df is None or not isinstance(df, pd.DataFrame):
        raise TypeError("Se esperaba un DataFrame de pandas válido.")
    if df.empty:
        raise ValueError("El DataFrame recibido está vacío (0 registros).")


def contar_registros(df):
    try:
        validar_dataframe(df)
        return len(df)
    except (TypeError, ValueError) as e:
        print(f"[Aviso contar_registros]: {e}")
        return 0


def contar_estado(df, columna, valor_buscado):
    try:
        validar_dataframe(df)
        if columna not in df.columns:
            raise KeyError(f"La columna '{columna}' no existe en la hoja.")

        # Normalizamos a texto, quitamos espacios y comparamos sin importar mayúsculas
        serie_limpia = df[columna].fillna("").astype(str).str.strip().str.lower()
        return int((serie_limpia == str(valor_buscado).strip().lower()).sum())

    except KeyError as e:
        print(f"[Error contar_estado]: {e}")
        return 0
    except (TypeError, ValueError) as e:
        print(f"[Aviso contar_estado]: {e}")
        return 0


def agrupar_por_tipo(df):
    try:
        validar_dataframe(df)
        columna = "Tipo de Cliente"
        if columna not in df.columns:
            raise KeyError(f"Falta la columna obligatoria '{columna}'.")

        tipos = df[columna].fillna("").astype(str).str.strip()
        # Reemplazamos celdas vacías para hacerlas visibles en el reporte
        tipos = tipos.replace("", "No especificado")
        return tipos.value_counts().to_dict()

    except KeyError as e:
        print(f"[Error agrupar_por_tipo]: {e}")
        return {}
    except (TypeError, ValueError) as e:
        print(f"[Aviso agrupar_por_tipo]: {e}")
        return {}


def agrupar_por_dominio_correo(df):
    try:
        validar_dataframe(df)
        columna = "Correo Electrónico"
        if columna not in df.columns:
            raise KeyError(f"Falta la columna '{columna}'.")

        dominios_validos = []
        for numero, valor in enumerate(df[columna], start=2):  # start=2 por fila de Google Sheets
            try:
                if pd.isna(valor) or str(valor).strip() == "":
                    dominios_validos.append("Sin Correo")
                    continue

                correo = str(valor).strip().lower()
                # Regla de negocio: debe tener '@' y un punto después del '@'
                if "@" not in correo or "." not in correo.split("@")[-1]:
                    raise ValueError(f"Formato de correo inválido: '{correo}'")

                dominio = correo.split("@")[-1]
                dominios_validos.append(dominio)

            except ValueError as e:
                print(f"[Fila {numero} - Correo]: {e}")
                dominios_validos.append("Correo Inválido")

        return pd.Series(dominios_validos).value_counts().head(5).to_dict()

    except KeyError as e:
        print(f"[Error agrupar_por_dominio_correo]: {e}")
        return {}
    except (TypeError, ValueError) as e:
        print(f"[Aviso agrupar_por_dominio_correo]: {e}")
        return {}


def validar_documento_serie(serie, longitud_esperada, nombre_doc):
    """Valida fila por fila que un documento (DNI/RUC) sea numérico y tenga la longitud exacta."""
    validos = 0
    for numero, valor in enumerate(serie, start=2):
        try:
            if pd.isna(valor) or str(valor).strip() == "":
                continue  # Celda vacía, simplemente no se cuenta

            doc_limpio = str(valor).strip()
            # Si Sheets leyó un número como float (ej. '12345678.0'), quitamos el '.0'
            if doc_limpio.endswith(".0"):
                doc_limpio = doc_limpio[:-2]

            if not doc_limpio.isdigit():
                raise ValueError(f"{nombre_doc} contiene letras o símbolos ('{doc_limpio}').")
            if len(doc_limpio) != longitud_esperada:
                raise ValueError(f"{nombre_doc} debe tener {longitud_esperada} dígitos, tiene {len(doc_limpio)} ('{doc_limpio}').")

            validos += 1

        except ValueError as e:
            print(f"[Fila {numero} - {nombre_doc}]: {e}")

    return validos


def conteo_documentos(df):
    resultado = {"Con DNI": 0, "Con RUC": 0}
    try:
        validar_dataframe(df)

        # Busca automáticamente la columna que contenga 'dni' y la que contenga 'ruc'
        col_dni = next((col for col in df.columns if "dni" in col.lower()), None)
        col_ruc = next((col for col in df.columns if "ruc" in col.lower()), None)

        if col_dni:
            resultado["Con DNI"] = validar_documento_serie(df[col_dni], 8, "DNI")
        else:
            print(f"[Error conteo_documentos]: No se encontró columna de DNI. Columnas disponibles: {list(df.columns)}")

        if col_ruc:
            resultado["Con RUC"] = validar_documento_serie(df[col_ruc], 11, "RUC")
        else:
            print(f"[Error conteo_documentos]: No se encontró columna de RUC. Columnas disponibles: {list(df.columns)}")

    except (TypeError, ValueError) as e:
        print(f"[Aviso conteo_documentos]: {e}")

    return resultado


def procesar_datos():
    resumen_vacio = {
        "total_registros": 0,
        "total_personas": 0,
        "total_empresas": 0,
        "porcentaje_empresas": 0,
        "por_tipo": {},
        "dominios_correo": {},
        "documentos": {"Con DNI": 0, "Con RUC": 0},
        "columnas": []
    }

    try:
        datos = obtener_datos()

        if datos is None:
            raise ValueError("La conexión no devolvió datos (None).")
        if not isinstance(datos, list) or len(datos) < 2:
            raise ValueError("La hoja no tiene suficientes filas (se requieren encabezados y al menos 1 registro).")

        # Limpiamos espacios ocultos en los encabezados de Google Sheets
        encabezados = [str(col).strip() for col in datos[0]]
        filas = datos[1:]

        df = pd.DataFrame(filas, columns=encabezados)
        
        # Eliminamos columnas vacías o basura si las hubiera
        df = df.loc[:, df.columns != ""]

        total = contar_registros(df)
        total_personas = contar_estado(df, "Tipo de Cliente", "Persona")
        total_empresas = contar_estado(df, "Tipo de Cliente", "Empresa")

        porcentaje_empresas = round((total_empresas / total) * 100, 1) if total > 0 else 0

        resumen = {
            "total_registros": total,
            "total_personas": total_personas,
            "total_empresas": total_empresas,
            "porcentaje_empresas": porcentaje_empresas,
            "por_tipo": agrupar_por_tipo(df),
            "dominios_correo": agrupar_por_dominio_correo(df),
            "documentos": conteo_documentos(df),
            "columnas": list(df.columns)
        }

        return df, resumen

    except ValueError as e:
        print(f"[Error crítico de datos en procesar_datos]: {e}")
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
    print(f"👤 Total de Personas:  {resumen['total_personas']}")
    print(f"🏢 Total de Empresas:  {resumen['total_empresas']}")
    print(f"📈 % Corporativo:     {resumen['porcentaje_empresas']}%")
    print("------------------------------------------")
    print("📊 Distribución por Tipo de Cliente:")
    for tipo, cantidad in resumen['por_tipo'].items():
        print(f"   - {tipo}: {cantidad}")
    print("------------------------------------------")
    print("🆔 Documentos Ingresados:")
    for doc, cantidad in resumen['documentos'].items():
        print(f"   - {doc}: {cantidad}")
    print("==========================================")
    
    print("\n==========================================")
    print("        VISTA PREVIA DE LA TABLA          ")
    print("==========================================")
    if df is not None:
        print(df.head())
    print("==========================================")