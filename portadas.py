"""Paso 7: portadas TikTok para cada guion (Muse Image).

Lee los guiones verificados, extrae el gancho visual de cada uno
(primera toma "qué se ve") y genera una portada vertical 1080x1920.

CLI:  python portadas.py videos/prueba.mp4 [--negocio negocios/jugueria.txt]
API:  generar_portadas(video, negocio_path) -> lista de Paths
"""

import re
import sys
from pathlib import Path

from common import artefacto, validar_negocio, validar_video
from imagen import generar_imagen


def extraer_ganchos(guiones: str) -> list[dict]:
    """Saca título + primera toma visual de cada guion."""
    bloques = re.split(r"\*\*GUION \d+\*\*", guiones)
    ganchos = []
    for b in bloques:
        if not b.strip():
            continue
        titulo = ""
        m = re.search(r"TÍTULO Y ÁNGULO:\s*(.+)", b)
        if m:
            titulo = m.group(1).replace("*", "").strip().rstrip(".")[:120]
        tomas = re.findall(r"qué se ve:\*\*\s*(.+?)\s*\|\s*\*\*qué se dice", b)
        primera = tomas[0].strip()[:300] if tomas else ""
        if titulo or primera:
            ganchos.append({"titulo": titulo, "visual": primera})
    return ganchos[:3]


def prompt_portada(gancho: dict, negocio: str) -> str:
    negocio_corto = negocio.splitlines()[0][:120] if negocio else ""
    return (
        "Portada vertical de TikTok 9:16, foto realista estilo UGC grabada con celular, "
        f"sin texto ni letras ni watermark. Negocio: {negocio_corto}. "
        f"Escena del gancho: {gancho['visual']}. "
        f"Ángulo del video: {gancho['titulo']}. "
        "Luz natural, colores cálidos, encuadre cerrado al producto, fondo del local "
        "ligeramente desenfocado, estética de video viral peruano de emprendimiento."
    )


def generar_portadas(video: Path, negocio_path: Path, forzar: bool = False) -> list[Path]:
    ruta = artefacto(video, f"_guiones_verificados_{negocio_path.stem}.txt")
    if not ruta.exists():
        ruta = artefacto(video, "_guiones_verificados.txt")
    if not ruta.exists():
        sys.exit(f"Falta el paso de verificación para {video}")
    guiones = ruta.read_text(encoding="utf-8")
    negocio = negocio_path.read_text(encoding="utf-8")

    ganchos = extraer_ganchos(guiones)
    if not ganchos:
        sys.exit("No pude extraer guiones del archivo verificado.")

    salidas = []
    for i, g in enumerate(ganchos, 1):
        salida = video.parent / f"{video.stem}_portada{i}_{negocio_path.stem}.png"
        if salida.exists() and not forzar:
            print(f"Ya existe {salida}, la reutilizo (--forzar para rehacer).")
        else:
            prompt = prompt_portada(g, negocio)
            (video.parent / f"{video.stem}_portada{i}_{negocio_path.stem}.txt").write_text(
                prompt, encoding="utf-8")
            generar_imagen(prompt, salida, "1080x1920")
        salidas.append(salida)
    return salidas


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit("Uso: python portadas.py <video.mp4> [--negocio <txt>]")
    video = validar_video(args[0])
    negocio_path = Path("negocio.txt")
    if "--negocio" in args:
        negocio_path = validar_negocio(args[args.index("--negocio") + 1])
    generar_portadas(video, negocio_path)


if __name__ == "__main__":
    main()
