"""Paso 1: audio → transcripción (Muse Voice Transcribe).

CLI:  python transcribir.py videos/prueba.mp4
API:  transcribir(video) -> Path del .txt
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from common import REINTENTOS_API, validar_video, verificar_ffmpeg

load_dotenv()


def transcribir(video: Path, forzar: bool = False) -> Path:
    salida = video.with_suffix(".txt")
    if salida.exists() and not forzar:
        print(f"Ya existe {salida}, la reutilizo (--forzar para rehacer).")
        return salida

    verificar_ffmpeg()
    audio = video.with_suffix(".wav")
    # 1. Sacar el audio en el formato que pide Meta: WAV mono, 16 bits, 24 kHz
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "24000",
             "-c:a", "pcm_s16le", "-map_metadata", "-1", str(audio)],
            check=True, capture_output=True,
        )
    except subprocess.CalledProcessError:
        sys.exit(f"ffmpeg no pudo leer {video}: archivo corrupto o códec raro. "
                 f"Prueba con otro mp4.")

    # 2. Enviarlo a Muse Voice Transcribe
    ajustes = {
        "mode": "PUSH_TO_TALK",
        "model": "muse-voice-transcribe-1.0",
        "audioEncoding": "WAV",
        "languageBias": ["Spanish"],
    }
    try:
        api_key = os.environ["MODEL_API_KEY"]
    except KeyError:
        sys.exit("Falta MODEL_API_KEY. Copia .env.example a .env.")
    r = None
    for intento in range(1, REINTENTOS_API + 1):
        try:
            with open(audio, "rb") as f:
                r = requests.post(
                    "https://api.meta.ai/v1/asr/transcribe",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={
                        "request": (None, json.dumps(ajustes), "application/json"),
                        "audio": (audio.name, f, "audio/wav"),
                    },
                    timeout=120,
                )
            if r.ok:
                break
            print(f"  ⚠ transcripción devolvió {r.status_code} "
                  f"(intento {intento}/{REINTENTOS_API})")
        except requests.RequestException as e:
            print(f"  ⚠ error de red ({e}); intento {intento}/{REINTENTOS_API}")
            r = None
        time.sleep(2.0 * intento)

    if r is None or not r.ok:
        detalle = r.text[:300] if r is not None else "sin respuesta"
        sys.exit(f"No se pudo transcribir tras {REINTENTOS_API} intentos: {detalle}")

    datos = r.json()
    print(f"Duración: {datos.get('audioDurationMs', 0) / 1000:.1f} s\n")
    print(datos["transcript"])
    salida.write_text(datos["transcript"], encoding="utf-8")
    return salida


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Uso: python transcribir.py <video.mp4>")
    transcribir(validar_video(sys.argv[1]))


if __name__ == "__main__":
    main()
