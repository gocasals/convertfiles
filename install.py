import subprocess
import sys

# Lista de paquetes a instalar
packages = ["docx2pdf", "pdf2docx"]

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


print("\n🎉 Instalación Inicada, aguarde unos minutos....")

def install(package):
    """Instala un paquete usando pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} instalado correctamente.")
    except subprocess.CalledProcessError:
        print(f"❌ Error al instalar {package}")

if __name__ == "__main__":
    for pkg in packages:
        install(pkg)

    print("\n🎉 Instalación finalizada. Ya podés usar los scripts de conversión.")