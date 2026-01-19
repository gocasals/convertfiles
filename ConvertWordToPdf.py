import os
from docx2pdf import convert

# Definir carpetas
INPUT_DIR = "output"
OUTPUT_DIR = "final"

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
print("✅ Conversión Iniciada. Los archivos Word están en la carpeta 'output'.")
# Iterar sobre todos los archivos Word en la carpeta input
for filename in os.listdir(INPUT_DIR):
    if filename.lower().endswith(".docx"):
        word_path = os.path.join(INPUT_DIR, filename)
        pdf_filename = os.path.splitext(filename)[0] + ".pdf"
        pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)

        print(f"Convirtiendo: {word_path} -> {pdf_path}")
        convert(word_path, pdf_path)

print("✅ Conversión finalizada. Los archivos PDF están en la carpeta 'final'.")