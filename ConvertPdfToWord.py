import os
from pdf2docx import Converter

# Definir carpetas
INPUT_DIR = "input"
OUTPUT_DIR = "output"

# Crear carpeta output si no existe
os.makedirs(OUTPUT_DIR, exist_ok=True)

def print_logo():
    logo = [
        "  *******   *******   ******* ",
        "  *         *     *   *       ",
        "  *         *     *   *       ",
        "  *  ****   *     *   *       ",
        "  *     *   *     *   *       ",
        "  *     *   *     *   *       ",
        "  *******   *******   ******* "
    ]
    for line in logo:
        print(line)

if __name__ == "__main__":
    print_logo()
print("✅ Conversión Iniciada. Los archivos PDF están en la carpeta 'input'.")
# Iterar sobre todos los archivos PDF en la carpeta input
for filename in os.listdir(INPUT_DIR):
    if filename.lower().endswith(".pdf"):
        pdf_path = os.path.join(INPUT_DIR, filename)
        docx_filename = os.path.splitext(filename)[0] + ".docx"
        docx_path = os.path.join(OUTPUT_DIR, docx_filename)

        print(f"Convirtiendo: {pdf_path} -> {docx_path}")
        # Convertir PDF a DOCX
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)
        cv.close()

print("✅ Conversión finalizada. Los archivos Word están en la carpeta 'output'.")