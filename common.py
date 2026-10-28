"""Utilidades compartidas del agente Gancho.

Un solo lugar para: cliente Meta, rutas de artefactos, parseo JSON
tolerante y validación de entradas. Los scripts de pasos importan
desde aquí; la CLI de cada paso se mantiene por compatibilidad.
"""

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_URL = "https://api.meta.ai/v1"
MODELO_SPARK = "muse-spark-1.3"
MODELO_TRANSCRIBE = "muse-voice-transcribe-1.0"
MODELO_IMAGEN = "muse-image-1.0"

# Reintentos para llamadas a la API (una caída de red no debe matar la demo)
REINTENTOS_API = 3
ESPERA_BASE_S = 2.0

_cliente = None


def get_client() -> OpenAI:
    """Cliente Meta Model API (lazy + singleton)."""
    global _cliente
    if _cliente is None:
        try:
            api_key = os.environ["MODEL_API_KEY"]
        except KeyError:
            sys.exit(
                "Falta MODEL_API_KEY. Copia .env.example a .env y pon tu clave."
            )
        if not api_key.strip():
            sys.exit("MODEL_API_KEY está vacío. Revisa tu .env.")
        _cliente = OpenAI(base_url=BASE_URL, api_key=api_key)
    return _cliente


def pedir(texto: str, modelo: str = MODELO_SPARK,
         reintentos: int = REINTENTOS_API) -> str:
    """Una llamada texto→texto a Muse Spark, con reintentos.

    Reintenta errores de red/API con espera exponencial. Si todo falla,
    sale con un mensaje claro en vez de un traceback crudo.
    """
    ultimo_error: Exception | None = None
    for intento in range(1, reintentos + 1):
        try:
            return get_client().responses.create(model=modelo, input=texto).output_text
        except Exception as e:  # noqa: BLE001 — cualquier fallo de API reintenta
            ultimo_error = e
            if intento < reintentos:
                espera = ESPERA_BASE_S * (2 ** (intento - 1))
                print(f"  ⚠ intento {intento}/{reintentos} falló ({e}); "
                      f"reintento en {espera:.0f}s…")
                time.sleep(espera)
    sys.exit(f"La API no respondió tras {reintentos} intentos: {ultimo_error}\n"
             f"Revisa tu conexión y MODEL_API_KEY, luego reintenta "
             f"(los pasos ya hechos se reutilizan).")


def pedir_json(texto: str, modelo: str = MODELO_SPARK,
               reintentos: int = REINTENTOS_API) -> dict:
    """Pide JSON al modelo y lo valida; reintenta si no viene válido."""
    ultimo: str = ""
    for intento in range(1, reintentos + 1):
        ultimo = pedir(texto, modelo)
        try:
            return leer_json_seguro(ultimo)
        except (ValueError, json.JSONDecodeError):
            if intento < reintentos:
                print(f"  ⚠ respuesta sin JSON válido (intento {intento}); reintento…")
    sys.exit("El modelo no devolvió JSON válido tras "
             f"{reintentos} intentos. Última respuesta:\n{ultimo[:800]}")


def leer_json_seguro(texto: str) -> dict:
    """Extrae JSON aunque venga con texto o bloques de código alrededor."""
    limpio = re.sub(r"^```(json)?|```$", "", texto.strip(), flags=re.M).strip()
    inicio = limpio.find("{")
    fin = limpio.rfind("}") + 1
    if inicio == -1 or fin <= inicio:
        raise ValueError(f"La respuesta no trae JSON:\n{texto[:500]}")
    return json.loads(limpio[inicio:fin])


def validar_video(ruta: str) -> Path:
    video = Path(ruta)
    if not video.exists():
        sys.exit(f"No existe el video: {ruta}")
    if video.suffix.lower() not in (".mp4", ".mov", ".webm", ".mkv"):
        sys.exit(f"Formato no soportado: {video.suffix} (usa mp4/mov/webm/mkv)")
    return video


def validar_negocio(ruta: str) -> Path:
    negocio = Path(ruta)
    if not negocio.exists():
        sys.exit(f"No existe el archivo del negocio: {ruta}")
    texto = negocio.read_text(encoding="utf-8").strip()
    if len(texto) < 20:
        sys.exit(f"{ruta} es muy corto; describe el negocio en 3-5 líneas.")
    return negocio


def leer_texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def guardar_texto(ruta: Path, texto: str) -> None:
    ruta.write_text(texto, encoding="utf-8")


def guardar_json(ruta: Path, datos) -> None:
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def paso(nombre: str) -> None:
    print(f"\n{'=' * 60}\n>>> {nombre}\n{'=' * 60}")


# Nombres de artefactos derivados del video (una sola convención)
def artefacto(video: Path, sufijo: str) -> Path:
    return video.with_name(video.stem + sufijo)


def normalizar_hueco(hueco: str) -> str:
    """Clave canónica de un hueco: sin corchetes, minúsculas, espacios simples.

    Evita que "[Combo]" y "combo para compartir" se traten como huecos
    distintos cuando el modelo varía el formato entre pasos.
    """
    h = hueco.strip().lower()
    h = h.strip("[](){}")
    return re.sub(r"\s+", " ", h).strip()


def verificar_ffmpeg() -> None:
    """Sale con instrucciones claras si ffmpeg no está instalado."""
    if shutil.which("ffmpeg") is None:
        sys.exit("Falta ffmpeg (se usa para audio y frames).\n"
                 "Instálalo: sudo apt install ffmpeg  (o: brew install ffmpeg)\n"
                 "Luego vuelve a correr el comando.")


class Crono:
    """Cronómetro simple para el resumen de tiempos del pipeline."""

    def __init__(self) -> None:
        self.t0 = time.time()
        self.marcas: list[tuple[str, float]] = []

    def marcar(self, nombre: str) -> float:
        dt = time.time() - self.t0
        self.marcas.append((nombre, dt))
        self.t0 = time.time()
        return dt

    def resumen(self) -> str:
        total = sum(d for _, d in self.marcas)
        lineas = [f"  • {n}: {d:.1f}s" for n, d in self.marcas]
        lineas.append(f"  Total pasos: {total:.1f}s")
        return "\n".join(lineas)
