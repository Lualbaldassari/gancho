"""Paso 3: entrevista al dueño — solo pregunta lo que negocio.txt no responde.

CLI interactiva:  python entrevista.py videos/prueba.mp4 [--negocio negocios/jugueria.txt]
CLI demo/batch:   python entrevista.py videos/prueba.mp4 --respuestas ejemplos/respuestas_jugueria.json
API:  entrevistar(video, negocio_path, respuestas=None) -> lista
"""

import json
import sys
from pathlib import Path

from common import (artefacto, guardar_json, normalizar_hueco, pedir_json,
                    validar_negocio, validar_video)

MOLDE = """{
  "ya_sabemos": [
    {"hueco": "[...]", "respuesta": "solo lo que dice el texto del negocio"}
  ],
  "preguntar": [
    {"hueco": "[...]", "pregunta": "..."}
  ]
}"""


def planificar(ficha: dict, negocio: str) -> dict:
    """Muse Spark separa lo que ya sabemos de lo que hay que preguntar."""
    datos_texto = json.dumps(ficha["datos_del_negocio_necesarios"], ensure_ascii=False, indent=2)
    instrucciones = f"""Vas a entrevistar al dueño de un negocio chico para grabar un TikTok.

Esto es lo que ya sabemos de su negocio:
\"\"\"{negocio}\"\"\"

Estos son los datos que necesitamos:
{datos_texto}

Para cada dato decide:
- Si el texto del negocio YA lo responde claramente, ponlo en "ya_sabemos".
  En "respuesta" usa solo lo que dice el texto, sin agregar nada.
- Si no lo responde, o lo responde a medias, ponlo en "preguntar". Puedes
  adaptar la pregunta al rubro del negocio para que suene natural, sin cambiar
  lo que se pide. Corta, tuteando, en español peruano sencillo.

Cada dato va en una sola de las dos listas. Responde SOLO con un JSON válido
que siga este molde, sin texto antes ni después y sin bloques de código:

{MOLDE}"""

    plan = pedir_json(instrucciones)
    # Validar forma; si el modelo se desvía, preguntar todo antes que perder datos.
    if not isinstance(plan.get("ya_sabemos"), list) or \
            not isinstance(plan.get("preguntar"), list):
        plan = {"ya_sabemos": [], "preguntar": [
            {"hueco": d.get("hueco", f"[dato {i + 1}]"),
             "pregunta": d.get("pregunta",
                               f"Cuéntame sobre {d.get('hueco', 'tu negocio')}")}
            for i, d in enumerate(ficha["datos_del_negocio_necesarios"])]}
    vistos = set()
    for grupo in ("ya_sabemos", "preguntar"):
        únicos = []
        for d in plan[grupo]:
            h = normalizar_hueco(str(d.get("hueco", "")))
            if h and h not in vistos:
                vistos.add(h)
                únicos.append(d)
        plan[grupo] = únicos
    return plan


def es_no_tiene(respuesta: str) -> bool:
    """¿El dueño indicó que no tiene ese dato?"""
    return respuesta.strip().lower() in ("", "no", "no tengo", "n/a", "-")


def entrevistar(video: Path, negocio_path: Path, respuestas: dict | None = None,
                forzar: bool = False) -> list:
    """Si `respuestas` es dict {hueco: respuesta}, corre sin pedir input.

    `respuestas` con valor "" / "no" / "no tengo" se guarda como NO TIENE
    con su plan_b, igual que en modo interactivo.
    """
    salida = artefacto(video, f"_entrevista_{negocio_path.stem}.json")
    # Compatibilidad: el flujo original de un negocio usaba _entrevista.json
    salida_legacy = artefacto(video, "_entrevista.json")
    if salida.exists() and not forzar:
        print(f"Ya existe {salida}, la reutilizo (--forzar para rehacer).")
        return json.loads(salida.read_text(encoding="utf-8"))

    ficha_path = artefacto(video, "_formula.json")
    if not ficha_path.exists():
        sys.exit(f"Falta la fórmula: corre antes formula.py sobre {video}")
    ficha = json.loads(ficha_path.read_text(encoding="utf-8"))
    negocio = negocio_path.read_text(encoding="utf-8")
    datos = ficha["datos_del_negocio_necesarios"]

    plan = planificar(ficha, negocio)
    plan_b = {d["hueco"]: d.get("si_no_tiene", "") for d in datos}

    entrevista = []

    print("Esto ya lo sé por tu negocio:")
    for d in plan["ya_sabemos"]:
        print(f"  - {d['hueco']}: {d['respuesta']}")
        entrevista.append({"hueco": d["hueco"], "respuesta": d["respuesta"],
                           "fuente": negocio_path.name})

    faltantes = plan["preguntar"]
    if respuestas is not None:
        # Modo no-interactivo (demo, WhatsApp, batch multi-rubro).
        # Búsqueda normalizada: el fixture casa aunque el modelo varíe
        # corchetes o mayúsculas entre la fórmula y la entrevista.
        por_hueco = {normalizar_hueco(k): v for k, v in respuestas.items()}
        for d in faltantes:
            r = (por_hueco.get(normalizar_hueco(d["hueco"]), "") or "").strip()
            if es_no_tiene(r):
                entrevista.append({"hueco": d["hueco"], "respuesta": "NO TIENE",
                                   "plan_b": plan_b.get(d["hueco"], ""), "fuente": "dueño"})
            else:
                entrevista.append({"hueco": d["hueco"], "respuesta": r, "fuente": "dueño"})
        print(f"\nEntrevista no-interactiva: {len(faltantes)} huecos resueltos por archivo.")
    else:
        print("\nTe hago unas preguntas. Si no tienes algo, deja vacío y presiona Enter.\n")
        for d in faltantes:
            r = input(d["pregunta"] + "\n> ").strip()
            if es_no_tiene(r):
                entrevista.append({"hueco": d["hueco"], "respuesta": "NO TIENE",
                                   "plan_b": plan_b.get(d["hueco"], ""), "fuente": "dueño"})
            else:
                entrevista.append({"hueco": d["hueco"], "respuesta": r, "fuente": "dueño"})
            print()

    guardar_json(salida, entrevista)
    # Mantener copia legacy para compatibilidad con flujos de un negocio
    if salida != salida_legacy:
        guardar_json(salida_legacy, entrevista)
    print(f"Listo. Guardé las respuestas en {salida}")
    return entrevista


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        sys.exit("Uso: python entrevista.py <video.mp4> [--negocio <txt>] [--respuestas <json>]")
    video = validar_video(args[0])
    negocio_path = Path("negocio.txt")
    respuestas = None
    i = 1
    while i < len(args):
        if args[i] == "--negocio" and i + 1 < len(args):
            negocio_path = validar_negocio(args[i + 1])
            i += 2
        elif args[i] == "--respuestas" and i + 1 < len(args):
            respuestas = json.loads(Path(args[i + 1]).read_text(encoding="utf-8"))
            i += 2
        else:
            sys.exit(f"Argumento desconocido: {args[i]}")
    entrevistar(video, negocio_path, respuestas)


if __name__ == "__main__":
    main()
