#!/usr/bin/env python3
"""
extract_camelot_consolidado.py
Extrae tablas con Camelot y consolida en un solo Excel:
- Movimientos en pesos
- Movimientos en dólares
- Detalle impositivo

Comportamiento adicional:
- Saltea líneas que comienzan con "Cuenta Corriente Nº "
- Si en una página aparece "Legales", se ignora todo lo posterior en ese PDF
- Si en una página aparece "Tasas de Acuerdos y Descubierto", se ignora todo lo posterior en ese PDF
"""

from pathlib import Path
import re
import camelot
import pdfplumber
import pandas as pd

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_XLSX = OUTPUT_DIR / "consolidado_movimientos_camelot.xlsx"

# Patrones
HEADER_MOVS_PATTERN = re.compile(r"fecha.*comprobante.*movimiento.*d[eé]bito.*cr[eé]dito.*saldo", re.IGNORECASE)
HEADER_IMP_PATTERN = re.compile(r"tipo.*de.*impuesto.*importe", re.IGNORECASE)
LEGALS_KEY = "legales"
LEGALS_KEY2 ="Tasas de Acuerdos y Descubierto"
SKIP_LINE_PREFIX = "Cuenta Corriente Nº"
SKIP_LINE_PREFIX2 = "Tasas de Acuerdos y Descubierto"
SKIP_LINE_PREFIX3 = "Cuenta Corriente en pesos Nº"

# Normalizar espacios invisibles
INVISIBLE = {
    "\u00A0": " ", "\u2009": " ", "\u202F": " ", "\u2003": " ", "\u2002": " ", "\t": " "
}
def normalizar(s: str) -> str:
    if s is None:
        return ""
    for k, v in INVISIBLE.items():
        s = s.replace(k, v)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def header_from_df(df):
    if df.shape[0] == 0:
        return ""
    row0 = " ".join([normalizar(str(x)) for x in df.iloc[0].tolist()]).strip()
    row1 = ""
    if df.shape[0] > 1:
        row1 = " ".join([normalizar(str(x)) for x in df.iloc[1].tolist()]).strip()
    candidate = (row0 + " " + row1).strip()
    return candidate.lower()

def detect_section_by_page_text(page_text):
    t = normalizar(page_text).lower()
    if "movimientos en pesos" in t:
        return "pesos"
    if "movimientos en d" in t and "dolares" in t or "movimientos en dólares" in t or "movimientos en u$s" in t:
        return "dolares"
    if "detalle impositivo" in t or "tipo de impuesto" in t:
        return "impositivo"
    return None

def extract_tables_from_pdf(pdf_path: Path):
    pesos_tables = []
    dolares_tables = []
    impositivo_tables = []

    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        stop_processing = False

        for page_no in range(1, n_pages + 1):
            if stop_processing:
                break

            page = pdf.pages[page_no - 1]
            page_text = page.extract_text() or ""
            page_text_norm = normalizar(page_text).lower()

            # Si aparece "Legales" en la página, dejamos de procesar este PDF
            if LEGALS_KEY in page_text_norm:
                # cortar todo lo posterior
                break

            if LEGALS_KEY2 in page_text_norm:
                # cortar todo lo posterior
                break

            page_section_hint = detect_section_by_page_text(page_text)

            # Intentar extraer tablas con Camelot stream, fallback lattice
            tables = []
            try:
                tables = camelot.read_pdf(str(pdf_path), pages=str(page_no), flavor="stream", strip_text='\n')
            except Exception:
                tables = []
            if not tables:
                try:
                    tables = camelot.read_pdf(str(pdf_path), pages=str(page_no), flavor="lattice", strip_text='\n')
                except Exception:
                    tables = []

            for t in tables:
                try:
                    df = t.df.copy()
                except Exception:
                    continue

                # Normalizar celdas
                df = df.applymap(lambda x: normalizar(str(x)) if x is not None else "")

                # Eliminar filas que comienzan con "Cuenta Corriente Nº " en cualquier columna
                # (aplicamos a cada fila: si la concatenación de la fila empieza con el prefijo, la saltamos)
                def row_starts_skip(r):
                    joined = " ".join([str(x) for x in r]).strip()
                    return joined.startswith(SKIP_LINE_PREFIX)
                def row_starts_skip(r):
                    joined = " ".join([str(x) for x in r]).strip()
                    return joined.startswith(SKIP_LINE_PREFIX3)
                def row_starts_skip(r):
                    joined = " ".join([str(x) for x in r]).strip()
                    return joined.startswith(SKIP_LINE_PREFIX2)
                df = df[~df.apply(row_starts_skip, axis=1)].reset_index(drop=True)
                if df.shape[0] == 0:
                    continue

                header_candidate = header_from_df(df)

                # Clasificar por encabezado
                if HEADER_MOVS_PATTERN.search(header_candidate):
                    # si la primera fila contiene "Fecha", usarla como header
                    if any("fecha" in str(c).lower() for c in df.iloc[0].tolist()):
                        df = df.rename(columns=df.iloc[0]).drop(df.index[0]).reset_index(drop=True)
                    # asignar según hint de página o default pesos
                    if page_section_hint == "dolares":
                        dolares_tables.append(df)
                    else:
                        pesos_tables.append(df)
                    continue

                if HEADER_IMP_PATTERN.search(header_candidate):
                    if any("tipo" in str(c).lower() for c in df.iloc[0].tolist()):
                        df = df.rename(columns=df.iloc[0]).drop(df.index[0]).reset_index(drop=True)
                    impositivo_tables.append(df)
                    continue

                # Si no detectó por header, usar hint de página
                if page_section_hint == "pesos":
                    pesos_tables.append(df)
                elif page_section_hint == "dolares":
                    dolares_tables.append(df)
                elif page_section_hint == "impositivo":
                    impositivo_tables.append(df)
                else:
                    # heurística: si primera columna contiene fechas dd/mm/yy -> movimientos
                    first_col = " ".join(df.iloc[:, 0].astype(str).tolist()) if df.shape[1] > 0 else ""
                    if re.search(r"\d{2}/\d{2}/\d{2}", first_col):
                        pesos_tables.append(df)
                    else:
                        # si tiene 2 columnas y la segunda parece monto -> impositivo
                        if df.shape[1] == 2 and df.iloc[:, 1].astype(str).str.contains(r"\$|\d").any():
                            impositivo_tables.append(df)
                        else:
                            pesos_tables.append(df)

    return pesos_tables, dolares_tables, impositivo_tables

def concat_and_normalize_tables(tables_list, expected_cols=None):
    if not tables_list:
        return pd.DataFrame()
    dfs = []
    for df in tables_list:
        # eliminar filas vacías
        df = df.dropna(how="all").reset_index(drop=True)
        # si df tiene header en la primera fila con nombres esperados, usarlo
        if expected_cols and set(expected_cols).issubset(set(df.iloc[0].astype(str).tolist())):
            df = df.rename(columns=df.iloc[0]).drop(df.index[0]).reset_index(drop=True)
        # si df tiene menos columnas que expected, rellenar
        if expected_cols:
            ncols = len(expected_cols)
            vals = df.values
            import numpy as np
            if vals.shape[1] < ncols:
                pad = np.full((vals.shape[0], ncols - vals.shape[1]), "", dtype=object)
                vals = np.hstack([vals, pad])
            df2 = pd.DataFrame(vals[:, :ncols], columns=expected_cols)
            dfs.append(df2)
        else:
            dfs.append(df.copy())
    result = pd.concat(dfs, ignore_index=True, sort=False)
    result.columns = [normalizar(str(c)) for c in result.columns]
    return result

def main():
    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))
    if not pdf_files:
        print("No se encontraron PDFs en 'input'.")
        return

    all_pesos_tables = []
    all_dolares_tables = []
    all_impositivo_tables = []

    for pdf in pdf_files:
        print("Procesando:", pdf.name)
        p_tables, d_tables, imp_tables = extract_tables_from_pdf(pdf)
        all_pesos_tables.extend(p_tables)
        all_dolares_tables.extend(d_tables)
        all_impositivo_tables.extend(imp_tables)

    mov_expected = ["Fecha", "Comprobante", "Movimiento", "Débito", "Crédito", "Saldo en cuenta"]
    imp_expected = ["Tipo de impuesto", "Importe"]

    df_pesos = concat_and_normalize_tables(all_pesos_tables, expected_cols=mov_expected)
    df_dolares = concat_and_normalize_tables(all_dolares_tables, expected_cols=mov_expected)
    df_imp = concat_and_normalize_tables(all_impositivo_tables, expected_cols=imp_expected)

    # Guardar en un solo Excel
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        hojas_creadas = False
        if not df_pesos.empty:
            df_pesos.to_excel(writer, sheet_name="Movimientos en pesos", index=False)
            hojas_creadas = True
        if not df_dolares.empty:
            df_dolares.to_excel(writer, sheet_name="Movimientos en dólares", index=False)
            hojas_creadas = True
        if not df_imp.empty:
            df_imp.to_excel(writer, sheet_name="Detalle impositivo", index=False)
            hojas_creadas = True
        if not hojas_creadas:
            pd.DataFrame([["Sin datos extraídos"]]).to_excel(writer, sheet_name="Vacío", index=False, header=False)

    print("Consolidado guardado en:", OUT_XLSX)

if __name__ == "__main__":
    main()
