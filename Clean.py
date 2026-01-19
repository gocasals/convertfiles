import os
import shutil


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
print("\n🎉 Limpieza iniciada....")

# Carpetas a limpiar
FOLDERS = ["input", "output", "final"]

def clean_folder(folder):
    if os.path.exists(folder):
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)  # borrar archivo
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # borrar carpeta dentro
            except Exception as e:
                print(f"⚠️ No se pudo borrar {file_path}: {e}")
        print(f"✅ Carpeta '{folder}' limpiada.")
    else:
        print(f"ℹ️ Carpeta '{folder}' no existe, se omite.")

if __name__ == "__main__":
    for folder in FOLDERS:
        clean_folder(folder)
    print("\n🎉 Limpieza finalizada.")