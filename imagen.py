"""Generación de imágenes (Muse Image).

CLI:  python imagen.py "un jugo surtido..." [1080x1920]
      python imagen.py videos/matcha.txt [1024x1280]
API:  generar_imagen(descripcion, salida, tamano) -> Path
"""

import base64
import sys
from pathlib import Path

from common import get_client


def generar_imagen(descripcion: str, salida: Path, tamano: str = "1080x1920") -> Path:
    respuesta = get_client().images.generate(
        model="muse-image-1.0",
        prompt=descripcion,
        n=1,
        size=tamano,
        response_format="b64_json",
        output_format="png",
    )
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_bytes(base64.b64decode(respuesta.data[0].b64_json))
    print(f"Imagen guardada en {salida}")
    return salida


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('Uso: python imagen.py "<descripcion>"|archivo.txt [TAMANO]')
    entrada = sys.argv[1]
    if entrada.endswith(".txt"):
        descripcion = Path(entrada).read_text(encoding="utf-8")
        salida = Path("videos") / (Path(entrada).stem + ".png")
    else:
        descripcion = entrada
        salida = Path("videos/imagen_prueba.png")
    tamano = sys.argv[2] if len(sys.argv) > 2 else "1080x1920"
    generar_imagen(descripcion, salida, tamano)


if __name__ == "__main__":
    main()
