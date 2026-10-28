"""Eval determinista del anti-alucinación — sin API, reproducible.

  .venv/bin/python eval.py [videos/prueba.mp4]

Compara los guiones ANTES vs DESPUÉS del verificador con las mismas reglas
deterministas que usa verificar.py (precios + copia) y cuenta marcas
[CONFIRMAR]. Es la evidencia auditable del claim "antes vs después":
cualquiera puede correrlo sin clave y obtener los mismos números.
"""

import json
import sys
from pathlib import Path

from common import artefacto
from verificar import chequeo_copia, chequeo_precios


def cargar_texto(ruta: Path, obligatoria: str = "") -> str:
    if not ruta.exists():
        sys.exit(f"Falta {ruta}: {obligatoria}")
    return ruta.read_text(encoding="utf-8")


def evaluar_negocio(video: Path, negocio_path: Path) -> dict:
    negocio = cargar_texto(negocio_path)
    original = cargar_texto(video.with_suffix(".txt"),
                            "corre transcribir.py o usa los artefactos incluidos.")

    ent = artefacto(video, f"_entrevista_{negocio_path.stem}.json")
    entrevista = ent.read_text(encoding="utf-8") if ent.exists() else ""
    datos_reales = negocio + "\n" + entrevista

    base = artefacto(video, f"_guiones_{negocio_path.stem}.txt")
    if not base.exists():
        base = artefacto(video, "_guiones.txt")
    ver = artefacto(video, f"_guiones_verificados_{negocio_path.stem}.txt")
    if not ver.exists():
        ver = artefacto(video, "_guiones_verificados.txt")
    antes = cargar_texto(base, "corre crear_video.py primero.")
    despues = cargar_texto(ver, "corre verificar.py primero.")

    def medir(guiones: str) -> dict:
        return {
            "precio": len(chequeo_precios(guiones, datos_reales)),
            "copia": len(chequeo_copia(guiones, original)),
            "confirmar": guiones.count("[CONFIRMAR"),
        }

    return {"negocio": negocio_path.stem, "antes": medir(antes),
            "despues": medir(despues)}


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    video = Path(args[0] if args else "videos/prueba.mp4")
    negocios = sorted(Path("negocios").glob("*.txt"))
    if not negocios:
        sys.exit("No hay fichas en negocios/*.txt")

    filas = [evaluar_negocio(video, n) for n in negocios]
    print(f"\nEval anti-alucinación sobre {video.name} "
          f"(reglas deterministas, sin API)\n")
    print(f"  {'negocio':<10} {'precio ant→des':<15} {'copia ant→des':<14} "
          f"[CONFIRMAR] ant→des")
    tot_a = tot_d = tot_c = tot_c2 = 0
    for f in filas:
        a, d = f["antes"], f["despues"]
        print(f"  {f['negocio']:<10} {a['precio']}→{d['precio']:<12} "
              f"{a['copia']}→{d['copia']:<11} {a['confirmar']}→{d['confirmar']}")
        tot_a += a["precio"] + a["copia"]
        tot_d += d["precio"] + d["copia"]
        tot_c += a["confirmar"]
        tot_c2 += d["confirmar"]
    print(f"\n  Problemas regla (precio+copia): {tot_a} → {tot_d}")
    print(f"  Datos marcados [CONFIRMAR]: {tot_c} → {tot_c2} "
          f"(marcar en vez de inventar)")

    # Sonda adversaria: demuestra que las reglas sí detectan (no que no miran).
    original = (video.with_suffix(".txt")).read_text(encoding="utf-8")
    sonda = ("TODO A S/ 999. " + " ".join(original.split()[:12]))
    detecta_precio = bool(chequeo_precios(sonda, "Jugos a S/ 8."))
    detecta_copia = bool(chequeo_copia(sonda, original))
    print(f"\n  Sonda adversaria (inyectada, no es un guion real): "
          f"precio {'detectado ✓' if detecta_precio else 'NO DETECTADO ✗'}, "
          f"copia {'detectada ✓' if detecta_copia else 'NO DETECTADA ✗'}")

    print("\nNota: el verificador completo suma el revisor LLM (inventado, "
          "promesas); este eval cubre la parte auditable sin costo.")
    print("Detalle por rondas: videos/*_reporte_verificacion_*.json")


if __name__ == "__main__":
    main()
