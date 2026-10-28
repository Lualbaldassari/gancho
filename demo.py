"""Demo filmable de Gancho en ~90 segundos, sin gastar API.

  .venv/bin/python demo.py [--negocio negocios/jugueria.txt] [--con-imagenes]

Muestra el pipeline completo sobre artefactos ya generados:
  fórmula → entrevista → guiones → verificados → WhatsApp (simulado).
Con --con-imagenes genera además las 3 portadas (3 llamadas a Muse Image).

Para la versión en vivo (gasta API): ver demo_vivo.sh
"""

import difflib
import json
import sys
import time
from pathlib import Path

from common import artefacto, paso

VIDEO_DEFAULT = "videos/prueba.mp4"


def exigir(ruta: Path, como: str) -> str:
    if not ruta.exists():
        sys.exit(f"Falta {ruta}.\nPara regenerarla: {como}")
    return ruta.read_text(encoding="utf-8")


def con_fallback(video: Path, prefijo: str, stem: str) -> tuple[str, Path]:
    """Artefacto por negocio, con fallback al legacy de un negocio."""
    ruta = artefacto(video, f"{prefijo}_{stem}.txt")
    if not ruta.exists():
        ruta = artefacto(video, f"{prefijo}.txt")
    return exigir(ruta, f".venv/bin/python main.py {video} --negocio negocios/{stem}.txt "
                        f"--no-interactivo"), ruta


def main() -> None:
    t0 = time.time()
    argv = sys.argv[1:]
    video = Path(VIDEO_DEFAULT)
    negocio_path = Path("negocios/jugueria.txt")
    con_imagenes = "--con-imagenes" in argv
    posicionales = []
    i = 0
    while i < len(argv):
        if argv[i] == "--negocio" and i + 1 < len(argv):
            negocio_path = Path(argv[i + 1])
            i += 2
        elif argv[i].startswith("--"):
            i += 1
        else:
            posicionales.append(argv[i])
            i += 1
    if posicionales:
        video = Path(posicionales[0])
    stem = negocio_path.stem

    exigir(video.with_suffix(".txt"),
            f"transcribe {video} o usa los artefactos incluidos.")
    exigir(artefacto(video, "_formula.json"), f".venv/bin/python formula.py {video}")

    paso("1/5 Fórmula viral extraída del video")
    ficha = json.loads(artefacto(video, "_formula.json").read_text(encoding="utf-8"))
    print(f"Formato: {ficha['formato']} | Emoción: {ficha['emocion']}")
    print(f"Gancho original: {ficha['gancho']['que_se_dice'][:100]}…")
    print("Fórmula reutilizable:")
    for p in ficha["formula_reutilizable"]:
        print(f"  • {p}")

    paso(f"2/5 Entrevista del negocio ({stem}) — solo lo que faltaba")
    ent_path = artefacto(video, f"_entrevista_{stem}.json")
    if not ent_path.exists():
        ent_path = artefacto(video, "_entrevista.json")
    entrevista = json.loads(exigir(ent_path, f".venv/bin/python entrevista.py {video} "
                                              f"--negocio {negocio_path} --respuestas "
                                              f"ejemplos/respuestas_{stem}.json"))
    n_archivo = sum(1 for d in entrevista if d["fuente"] != "dueño")
    print(f"  {n_archivo}/{len(entrevista)} datos ya estaban en {negocio_path.name} "
          f"(no se preguntaron).")
    for d in entrevista:
        marca = "📄" if d["fuente"] != "dueño" else "💬"
        print(f"  {marca} {d['hueco']}: {d['respuesta'][:80]}")

    paso("3/5 Guiones antes vs después del verificador")
    antes, _ = con_fallback(video, "_guiones", stem)
    despues, ruta_ver = con_fallback(video, "_guiones_verificados", stem)
    n_confirm = despues.count("[CONFIRMAR")
    print(f"  Antes: {len(antes)} caracteres sin marcas de verificación")
    print(f"  Después: {len(despues)} caracteres, "
          f"{n_confirm} datos marcados [CONFIRMAR] en vez de inventados")
    print("  Cambios reales del verificador (muestra):")
    mostrados = 0
    for linea in difflib.unified_diff(antes.splitlines(), despues.splitlines(), lineterm=""):
        if linea.startswith(("+", "-")) and not linea.startswith(("+++", "---")) \
                and "[CONFIRMAR" in linea:
            print(f"    {linea[:115]}")
            mostrados += 1
            if mostrados >= 4:
                break
    if not mostrados:
        for l in despues.splitlines()[:6]:
            print(f"    {l[:110]}")
    print(f"  Guiones completos: {ruta_ver}")

    paso("4/5 Portadas TikTok (Muse Image)")
    from portadas import extraer_ganchos, generar_portadas
    ganchos = extraer_ganchos(despues)
    for i, g in enumerate(ganchos, 1):
        print(f"  Portada {i}: {g['titulo'][:90]}")
    if con_imagenes:
        for p in generar_portadas(video, negocio_path):
            print(f"  ✓ {p}")
    else:
        print("  (usa --con-imagenes para generarlas; prompts listos en portadas.py)")

    paso("5/5 Entrega por WhatsApp (modo simulado → outbox/)")
    from whatsapp import entregar_guiones
    # Demo limpia: empezar sin mensajes viejos para que la vista previa
    # muestre exactamente lo que recibe la dueña.
    for viejo in Path("outbox").glob("mensaje_*.json"):
        viejo.unlink()
    entregar_guiones("51999999999", video, negocio_path)
    print("\nMensajes guardados en outbox/. Con WHATSAPP_TOKEN en .env se envían de verdad.")
    print("Abre outbox/preview.html para ver el chat como lo ve la dueña.")

    print(f"\nDemo completa en {time.time() - t0:.1f}s (sin gastar API).")
    print("Siguiente para jueces: .venv/bin/python eval.py  "
          "(prueba del anti-alucinación)")


if __name__ == "__main__":
    main()
