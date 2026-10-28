"""Chequeo de salud del proyecto — sin API, para jueces y demos.

  .venv/bin/python check.py

Verifica: intérprete, dependencias, ffmpeg, .env, artefactos de la demo,
fixtures multi-rubro y tests. Sale 0 si todo está listo para `demo.py`.
"""

import shutil
import subprocess
import sys
from pathlib import Path

OK, FAIL = "✓", "✗"
fallos = []


def chequear(nombre: str, ok: bool, pista: str = "") -> None:
    print(f"  {OK if ok else FAIL} {nombre}" + ("" if ok else f" — {pista}"))
    if not ok:
        fallos.append(nombre)


def main() -> None:
    print("\nGancho · chequeo de salud\n")

    chequear(f"Python {sys.version.split()[0]} (≥3.10)",
             sys.version_info >= (3, 10), "usa .venv/bin/python")
    for mod in ("openai", "dotenv", "requests"):
        try:
            __import__(mod)
            chequear(f"dependencia {mod}", True)
        except ImportError:
            chequear(f"dependencia {mod}", False, "pip install -r requirements.txt")
    chequear("ffmpeg en PATH", shutil.which("ffmpeg") is not None,
             "sudo apt install ffmpeg / brew install ffmpeg")

    env = Path(".env")
    chequear(".env existe", env.exists(), "cp .env.example .env")
    import os
    clave_env = bool(os.environ.get("MODEL_API_KEY", "").strip())
    clave_archivo = (env.exists() and "MODEL_API_KEY=" in env.read_text()
                     and "tu_clave_aqui" not in env.read_text())
    chequear("MODEL_API_KEY configurada", clave_env or clave_archivo,
             "pon tu clave en .env (solo pipeline en vivo; demo.py no la necesita)")

    video = Path("videos/prueba.mp4")
    base = ["prueba.txt", "prueba_formula.json"]
    for suf in base:
        chequear(f"artefacto {suf}", (video.parent / suf).exists(),
                 "corre: bash demo_vivo.sh (gasta API)")
    n_neg = 0
    for neg in sorted(Path("negocios").glob("*.txt")):
        n_neg += 1
        ent = video.parent / f"prueba_entrevista_{neg.stem}.json"
        ver = video.parent / f"prueba_guiones_verificados_{neg.stem}.txt"
        chequear(f"demo {neg.stem} (entrevista+verificados)",
                 ent.exists() and ver.exists(),
                 f"corre main.py --negocio {neg} --no-interactivo")
    chequear("fixtures multi-rubro (≥2 negocios)", n_neg >= 2, "revisa negocios/")

    n_fix = len(list(Path("ejemplos").glob("respuestas_*.json")))
    chequear(f"respuestas no-interactivas ({n_fix} fixtures)", n_fix >= 2,
             "revisa ejemplos/")

    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "tests"],
                       capture_output=True, text=True)
    chequear("tests deterministas", r.returncode == 0,
             (r.stderr.strip().splitlines() or ["?"])[-1][:100])

    print()
    if fallos:
        print(f"{len(fallos)} chequeo(s) pendiente(s). Empieza por el primero.")
        sys.exit(1)
    print("Todo listo. Corre:  .venv/bin/python demo.py")


if __name__ == "__main__":
    main()
