"""Gancho: un comando, un agente, de video viral a guiones en WhatsApp.

  python main.py videos/prueba.mp4 --negocio negocios/jugueria.txt
  python main.py videos/prueba.mp4 --negocio negocios/ropa.txt --no-interactivo --con-portadas
  python main.py videos/prueba.mp4 --negocio negocios/jugueria.txt --enviar-whatsapp --para 51999999999

Pasos: transcribir → fórmula → entrevista → guiones → verificar → portadas → WhatsApp.
Cada paso reutiliza su artefacto si ya existe (--forzar para rehacer).
"""

import argparse
import json
import sys
import time
from pathlib import Path

from common import Crono, paso, validar_negocio, validar_video


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gancho: de video viral a guiones listos.")
    p.add_argument("video", help="Video viral de referencia (mp4/mov/webm/mkv)")
    p.add_argument("--negocio", default="negocio.txt", help="Ficha del negocio (txt)")
    p.add_argument("--respuestas", default=None,
                   help="JSON {hueco: respuesta} para entrevista no-interactiva")
    p.add_argument("--no-interactivo", action="store_true",
                   help="No pedir input: usa --respuestas o ejemplos/respuestas_<negocio>.json")
    p.add_argument("--con-portadas", action="store_true", help="Generar 3 portadas TikTok")
    p.add_argument("--con-sam", action="store_true", help="Analizar encuadre con SAM (frame)")
    p.add_argument("--enviar-whatsapp", action="store_true", help="Entregar por WhatsApp")
    p.add_argument("--para", default="", help="Número destino WhatsApp (ej. 51999999999)")
    p.add_argument("--solo-hasta", default="verificar",
                   choices=["transcribir", "formula", "entrevista", "guiones", "verificar",
                            "portadas", "whatsapp"],
                   help="Detener el pipeline en un paso (para debug/demo)")
    p.add_argument("--forzar", action="store_true", help="Rehacer pasos aunque haya cache")
    return p.parse_args()


def resolver_respuestas(args, negocio_path: Path):
    if args.respuestas:
        return json.loads(Path(args.respuestas).read_text(encoding="utf-8"))
    if args.no_interactivo:
        candidata = Path(f"ejemplos/respuestas_{negocio_path.stem}.json")
        if candidata.exists():
            print(f"Respuestas no-interactivas desde {candidata}")
            return json.loads(candidata.read_text(encoding="utf-8"))
        print("Modo no-interactivo sin fixture: huecos faltantes → NO TIENE + plan_b.")
        return {}
    return None


def main() -> None:
    t0 = time.time()
    args = parse_args()
    video = validar_video(args.video)
    negocio_path = validar_negocio(args.negocio)
    if args.enviar_whatsapp and not args.para:
        sys.exit("--enviar-whatsapp necesita --para 51999999999")

    from transcribir import transcribir
    from formula import extraer_formula
    from entrevista import entrevistar
    from crear_video import crear_guiones
    from verificar import verificar

    crono = Crono()
    paso(f"1/7 Transcribir {video.name}")
    transcribir(video, forzar=args.forzar)
    crono.marcar("transcribir")
    if args.solo_hasta == "transcribir":
        return

    paso("2/7 Extraer fórmula viral (Muse Spark)")
    extraer_formula(video, forzar=args.forzar)
    crono.marcar("fórmula")
    if args.solo_hasta == "formula":
        return

    paso(f"3/7 Entrevista del negocio ({negocio_path.stem})")
    respuestas = resolver_respuestas(args, negocio_path)
    entrevistar(video, negocio_path, respuestas, forzar=args.forzar)
    crono.marcar("entrevista")
    if args.solo_hasta == "entrevista":
        return

    paso("4/7 Generar 3 guiones")
    crear_guiones(video, negocio_path, forzar=args.forzar)
    crono.marcar("guiones")
    if args.solo_hasta == "guiones":
        return

    paso("5/7 Verificar y auto-corregir")
    _, preguntas = verificar(video, negocio_path, forzar=args.forzar)
    crono.marcar("verificar")
    if args.solo_hasta == "verificar":
        return

    if args.con_portadas or args.solo_hasta in ("portadas", "whatsapp"):
        paso("6/7 Generar portadas (Muse Image)")
        from portadas import generar_portadas
        generar_portadas(video, negocio_path, forzar=args.forzar)
        crono.marcar("portadas")
        if args.solo_hasta == "portadas":
            return

    if args.con_sam:
        paso("7/7 Analizar encuadre (SAM)")
        from sam import analizar_frame, extraer_frame
        frame = extraer_frame(video)
        print(analizar_frame(frame))
        crono.marcar("sam")

    if args.enviar_whatsapp or args.solo_hasta == "whatsapp":
        paso(f"Entregar por WhatsApp → {args.para or '(simulado)'}")
        from whatsapp import entregar_guiones
        entregar_guiones(args.para or "demo", video, negocio_path)
        crono.marcar("whatsapp")

    print(f"\nListo en {time.time() - t0:.1f}s. Artefactos junto a {video.name}: "
          f"_formula.json, _entrevista_*.json, _guiones_verificados_*.txt"
          + (", _portada*.png" if args.con_portadas else ""))
    print(f"\nTiempos por paso:\n{crono.resumen()}")
    if preguntas:
        print(f"\n❓ {len(preguntas)} pregunta(s) para la dueña antes de grabar "
              f"(ver _preguntas_{negocio_path.stem}.json).")
    else:
        print("\n✓ Sin preguntas pendientes: todo lo necesario ya se sabe.")


if __name__ == "__main__":
    main()
