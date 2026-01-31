#!/usr/bin/env python3
"""
extract_tarjeta.py
Extrae movimientos de resúmenes de tarjeta (PDF) y genera output/consolidado_tarjeta.xlsx
Hoja: Movimientos tarjeta
"""

from pathlib import Path
import re
import pdfplumber
import pandas as pd

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_XLSX = OUTPUT_DIR / "consolidado_tarjeta.xlsx"

# Normalizar espacios invisibles comunes en PDFs
INVISIBLE_CHARS = {
    "\u00A0": " ",  # non-breaking space
    "\u2009": " ",
    "\u202F": " ",
    "\u2003": " ",
    "\u2002": " ",
    "\t": " ",
}

def normalizar(s: str) -> str:
    if s is None:
        return ""
    for k, v in INVISIBLE_CHARS.items():
        s = s.replace(k, v)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

# Detectores
HEADER_MOVS_RE = re.compile(r"fecha.*comprobante.*referencia.*\$.*u\$s", re.IGNORECASE)
ALT_HEADER_MOVS_RE = re.compile(r"fecha.*comprobante.*referencia", re.IGNORECASE)
END_SECTION_KEYS = ["SALDO ACTUAL", "EL PRESENTE ES COPIA", "NO TENÉS MOVIMIENTOS", "NO TENÉS MOVIMIENTOS EN DÓLARES"]

# Detecta si una línea comienza con día (1-31) posiblemente seguido por mes palabra o abreviatura
DAY_START_RE = re.compile(r"^\s*(\d{1,2})(?:\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+))?\b")

# Detecta montos en formato argentino (ej: 1.234.567,89 o 1234,56) y U$S
MONTO_PESOS_RE = re.compile(r"(-?\d{1,3}(?:\.\d{3})*,\d{2})")
MONTO_USD_RE = re.compile(r"(-?\d{1,3}(?:\.\d{3})*,\d{2})")  # mismo patrón, se decide por columna

def parse_page_lines(lines):
    """
    Recibe lista de líneas normalizadas de una página y devuelve lista de filas (Fecha, Comprobante, Movimiento, $ , U$S)
    """
    filas = []
    capturando = False

    for i, raw in enumerate(lines):
        line = normalizar(raw)
        if not line:
            continue

        # Saltar líneas que son encabezados de cuenta u otros
        if line.upper().startswith("CUENTA:") or line.upper().startswith("CUENTA"):
            continue

        # Detectar inicio de sección de movimientos
        if HEADER_MOVS_RE.search(line) or ALT_HEADER_MOVS_RE.search(line):
            capturando = True
            continue

        # Si aparece una clave de fin de sección, cortar captura
        if any(k.lower() in line.lower() for k in END_SECTION_KEYS):
            capturando = False
            continue

        if not capturando:
            continue

        # Si la línea comienza con día -> nueva fila
        mday = DAY_START_RE.match(line)
        if mday:
            day = mday.group(1)
            month = mday.group(2) or ""
            # Remover el día/mes del inicio para procesar el resto
            rest = line[mday.end():].strip()
            # Separar por 2+ espacios (PDFs suelen alinear columnas con múltiples espacios)
            parts = re.split(r"\s{2,}", rest)
            # Heurística de columnas:
            # parts puede ser: [Comprobante Referencia, Movimiento, $ , U$S]
            comprobante = ""
            movimiento = ""
            monto_pesos = ""
            monto_usd = ""

            if len(parts) >= 3:
                comprobante = parts[0].strip()
                movimiento = parts[1].strip()
                # últimos elementos suelen ser montos; tomar los últimos dos como $ y U$S (si existen)
                tail = parts[2:]
                if len(tail) == 1:
                    # puede ser solo $ o solo U$S; decidir por presencia de U$S en movimiento o en tail
                    if "U$S" in tail[0] or "USD" in tail[0] or re.search(r"\d+,\d{2}", tail[0]) and "U$S" in line:
                        monto_usd = tail[0].strip()
                    else:
                        monto_pesos = tail[0].strip()
                else:
                    monto_pesos = tail[-2].strip()
                    monto_usd = tail[-1].strip()
            else:
                # fallback: intentar separar por espacios simples y buscar montos al final
                tokens = rest.split()
                # buscar montos desde el final
                montos = re.findall(r"-?\d{1,3}(?:\.\d{3})*,\d{2}", rest)
                if montos:
                    # asignar último a U$S si en la línea aparece "U$S" o si la columna final parece USD
                    if "U$S" in line or "USD" in line:
                        monto_usd = montos[-1]
                        if len(montos) >= 2:
                            monto_pesos = montos[-2]
                    else:
                        monto_pesos = montos[-1]
                # intentar extraer comprobante como primer token si es numérico
                if tokens and re.fullmatch(r"\d{1,6}", tokens[0]):
                    comprobante = tokens[0]
                    movimiento = " ".join(tokens[1:- (1 if monto_pesos or monto_usd else 0)]).strip()
                else:
                    movimiento = rest

            fecha = f"{day} {month}".strip()
            filas.append([fecha, comprobante, movimiento, monto_pesos, monto_usd])
        else:
            # línea sin día: detalle que se concatena al último movimiento
            if filas:
                filas[-1][2] = (filas[-1][2] + " " + line).strip()
            else:
                # si no hay fila previa, ignorar o guardar como fila suelta
                # guardamos como movimiento sin fecha para revisión
                filas.append(["", "", line, "", ""])
    return filas

def parse_pdf_movimientos(pdf_path: Path):
    """
    Recorre el PDF página por página, normaliza y extrae movimientos.
    Devuelve lista de filas.
    """
    todas_filas = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            # cortar todo lo posterior a "Legales" o "EL PRESENTE ES COPIA" si aparece
            text_norm = normalizar(text)
            # Si aparece "Legales" cortar la página y las siguientes
            if "legales" in text_norm.lower():
                break
            # dividir en líneas y parsear
            lines = text.split("\n")
            filas = parse_page_lines(lines)
            todas_filas.extend(filas)
    return todas_filas

def monto_to_float(s: str):
    """
    Convierte string tipo '1.234.567,89' o '204.730,97-' a float con signo.
    Devuelve None si no se puede convertir.
    """
    if not s:
        return None
    s = s.replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    # quitar guiones al final o al inicio
    sign = 1
    if s.endswith("-"):
        sign = -1
        s = s[:-1]
    if s.startswith("-"):
        sign = -1
        s = s[1:]
    try:
        return sign * float(s)
    except Exception:
        return None

def procesar_carpeta(input_dir: Path, out_xlsx: Path):
    all_rows = []
    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        print("No se encontraron PDFs en", input_dir)
        return

    for pdf in pdf_files:
        print("Procesando:", pdf.name)
        filas = parse_pdf_movimientos(pdf)
        # agregar columna origen archivo
        for f in filas:
            all_rows.append([pdf.name] + f)

    # DataFrame y limpieza
    cols = ["Archivo", "Fecha", "Comprobante", "Movimiento", "Monto $", "Monto U$S"]
    df = pd.DataFrame(all_rows, columns=cols)

    # convertir montos a float en nuevas columnas
    df["Monto $ (num)"] = df["Monto $"].apply(monto_to_float)
    df["Monto U$S (num)"] = df["Monto U$S"].apply(monto_to_float)

    # Guardar en Excel
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Movimientos tarjeta", index=False)

    print("Consolidado guardado en:", out_xlsx)

if __name__ == "__main__":
    procesar_carpeta(INPUT_DIR, OUT_XLSX)
