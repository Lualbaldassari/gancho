"""Paso 4: fórmula + negocio + entrevista → 3 guiones listos para grabar.

CLI:  python crear_video.py videos/prueba.mp4 [--negocio negocios/jugueria.txt]
API:  crear_guiones(video, negocio_path) -> str con los 3 guiones
"""

import json
import sys
from pathlib import Path

from common import artefacto, guardar_texto, pedir, validar_negocio, validar_video


def crear_guiones(video: Path, negocio_path: Path, forzar: bool = False) -> str:
    sufijo = f"_guiones_{negocio_path.stem}.txt"
    salida = artefacto(video, sufijo)
    salida_legacy = artefacto(video, "_guiones.txt")
    if salida.exists() and not forzar:
        print(f"Ya existe {salida}, la reutilizo (--forzar para rehacer).")
        return salida.read_text(encoding="utf-8")

    ficha_path = artefacto(video, "_formula.json")
    if not ficha_path.exists():
        sys.exit(f"Falta la fórmula: corre antes formula.py sobre {video}")
    ficha = ficha_path.read_text(encoding="utf-8")
    negocio = negocio_path.read_text(encoding="utf-8")

    ruta_entrevista = artefacto(video, f"_entrevista_{negocio_path.stem}.json")
    if ruta_entrevista.exists():
        entrevista = ruta_entrevista.read_text(encoding="utf-8")
    elif artefacto(video, "_entrevista.json").exists():
        entrevista = artefacto(video, "_entrevista.json").read_text(encoding="utf-8")
    else:
        entrevista = "(No hubo entrevista.)"
        print("Aviso: no encontré la entrevista. Corre antes entrevista.py.\n")

    instrucciones = f"""Eres un estratega de contenido de TikTok para emprendedores peruanos que recién empiezan.

Esta es la fórmula de un video que se hizo viral (en JSON). Las partes "gancho",
"estructura", etc. describen el video ORIGINAL y son solo referencia; la guía
para escribir es "formula_reutilizable":
\"\"\"{ficha}\"\"\"

Este es el negocio del emprendedor:
\"\"\"{negocio}\"\"\"

Estas son las respuestas del dueño en la entrevista (en JSON):
\"\"\"{entrevista}\"\"\"

Escribe 3 guiones distintos que apliquen esa fórmula a este negocio.
Reglas:
- Desde el punto de vista del DUEÑO, no de un cliente ni de un influencer.
- Lo graba una sola persona con su celular, sin presupuesto.
- Usa la estructura de la fórmula, pero NO copies frases del video original.
- Nada de promesas falsas (ganancias, curas, "el mejor del Perú").
- Español peruano natural, como habla la gente.
- Cada guion cierra invitando a escribir por WhatsApp o a visitar el local.

Reglas de datos (las más importantes):
- Los datos del negocio (productos, ingredientes, precios, combos, clientes,
  horarios, historias) salen SOLO del texto del negocio o de la entrevista.
- Si un dato dice "NO TIENE", sigue su "plan_b" sin inventar el dato que falta.
- Si aun así falta algo, escribe [CONFIRMAR: qué falta] en lugar de inventarlo.
- Esto vale también para la columna "qué se ve": describir la escena está bien,
  pero no muestres ni nombres productos, ingredientes o precios que no estén
  en esos datos.
- No digas que algo es nuevo, ni para cuántas personas alcanza, si el dueño
  no lo dijo.

Para cada guion da:
TÍTULO Y ÁNGULO (en una línea)
TOMAS: una lista con segundo aproximado | qué se ve | qué se dice | texto en pantalla
POR QUÉ PUEDE FUNCIONAR: una frase."""

    guiones = pedir(instrucciones)
    print(guiones)
    guardar_texto(salida, guiones)
    if salida != salida_legacy:
        guardar_texto(salida_legacy, guiones)
    return guiones


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit("Uso: python crear_video.py <video.mp4> [--negocio <txt>]")
    video = validar_video(args[0])
    negocio_path = Path("negocio.txt")
    if "--negocio" in args:
        negocio_path = validar_negocio(args[args.index("--negocio") + 1])
    crear_guiones(video, negocio_path)


if __name__ == "__main__":
    main()
