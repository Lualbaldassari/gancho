"""Utilidad SAM 3.1: del "plano cerrado" genérico al recorte real del producto.

Por qué existe: los guiones piden "enfoca bien de cerca tu producto", pero la
dueña no sabe qué encuadre funciona. SAM segmenta el producto en un frame del
video viral y Gancho usa esa máscara para dos cosas:

  1. Decirle a la dueña QUÉ parte del encuadre importa (bbox del producto).
  2. Generar portadas con la misma composición (producto centrado/abajo, etc.).

Estado hackatón: la llamada real a SAM 3.1 vía Meta Model API va aquí cuando
el endpoint esté disponible. Mientras tanto `analizar_frame` usa un detector
de saliencia por contraste (sin dependencias) que devuelve el mismo contrato
{bbox, cobertura, sugerencia_encuadre}, así el resto del pipeline ya funciona.

CLI:  python sam.py videos/prueba.mp4 [--segundo 5]
"""

import struct
import subprocess
import sys
import zlib
from pathlib import Path

from common import validar_video


def extraer_frame(video: Path, segundo: float = 5.0) -> Path:
    salida = video.parent / f"{video.stem}_frame.png"
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(segundo), "-i", str(video),
         "-frames:v", "1", str(salida)],
        check=True, capture_output=True)
    return salida


def _leer_png_gris(ruta: Path) -> tuple[int, int, list[int]]:
    """Lee un PNG (vía ffmpeg → raw) devolviendo píxeles en gris 64x64."""
    crudo = ruta.parent / f"{ruta.stem}_64.raw"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(ruta), "-vf", "scale=64:64,format=gray",
         "-f", "rawvideo", str(crudo)],
        check=True, capture_output=True)
    px = list(crudo.read_bytes())
    crudo.unlink(missing_ok=True)
    return 64, 64, px


def analizar_frame(frame: Path) -> dict:
    """Contrato estable, listo para enchufar SAM 3.1 sin cambiar llamadas.

    Devuelve {"bbox": [x0,y0,x1,y1] 0-1, "cobertura": float, "sugerencia": str}.
    """
    # TODO(hackatón): reemplazar por llamada SAM 3.1:
    #   mask = client.segment(image=frame, model="sam-3.1")
    # y derivar bbox de la máscara del objeto central.
    _, _, px = _leer_png_gris(frame)
    # Saliencia = píxeles que más se alejan de la media (el producto suele
    # contrastar con el fondo). Sin dependencias, determinista.
    media = sum(px) / len(px)
    sal = [abs(p - media) for p in px]
    umbral = sorted(sal)[int(len(sal) * 0.8)]
    pts = [(i % 64, i // 64) for i, s in enumerate(sal) if s >= umbral]
    if not pts:
        bbox = [0.1, 0.1, 0.9, 0.9]
    else:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bbox = [min(xs) / 64, min(ys) / 64, (max(xs) + 1) / 64, (max(ys) + 1) / 64]
    cobertura = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    if cobertura > 0.5:
        sugerencia = "El producto llena el encuadre: graba a ~30 cm, luz de frente."
    elif cobertura < 0.15:
        sugerencia = "El producto se ve chico: acércate hasta que llene la mitad."
    else:
        sugerencia = "Encuadre ideal: producto al centro ocupando ~1/3 de pantalla."
    return {"bbox": [round(c, 3) for c in bbox],
            "cobertura": round(cobertura, 3), "sugerencia": sugerencia}


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Uso: python sam.py <video.mp4> [--segundo 5]")
    video = validar_video(sys.argv[1])
    seg = float(sys.argv[sys.argv.index("--segundo") + 1]) if "--segundo" in sys.argv else 5.0
    frame = extraer_frame(video, seg)
    print(f"Frame: {frame}")
    print(analizar_frame(frame))


if __name__ == "__main__":
    main()
