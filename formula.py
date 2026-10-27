import os, sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://api.meta.ai/v1",
    api_key=os.environ["MODEL_API_KEY"],
)

video = Path(sys.argv[1])
transcripcion = video.with_suffix(".txt").read_text(encoding="utf-8")

# 1. Subir el video (se borra solo en 1 hora)
with open(video, "rb") as f:
    archivo = client.files.create(
        purpose="user_data",
        file=f,
        expires_after={"anchor": "created_at", "seconds": 3600},
    )
print(f"Video subido: {archivo.id}\n")

# 2. Pedir la ficha de fórmula viral
instrucciones = f"""Eres un estratega de contenido de TikTok para emprendedores peruanos.
Mira el video y usa esta transcripción de lo que se dice:

\"\"\"{transcripcion}\"\"\"

Responde en español con esta ficha y nada más:

GANCHO (0-3 s): qué se ve, qué se dice y por qué hace que la gente no deslice.
ESTRUCTURA: los bloques del video con su segundo aproximado (ej. 0-3 s gancho, 3-15 s ...).
FORMATO: tipo de video (reseña, tutorial, antes/después, storytime, POV, lista u otro).
RITMO Y EDICIÓN: cortes, planos, texto en pantalla, música o sonidos.
EMOCIÓN: qué siente quien lo ve (antojo, curiosidad, risa, confianza...).
LLAMADA A LA ACCIÓN: qué le pide al espectador.
FÓRMULA REUTILIZABLE: una plantilla de 4-6 pasos con [huecos] que cualquier
emprendedor pueda llenar con su propio negocio.

No inventes nada que no se vea o escuche en el video."""

respuesta = client.responses.create(
    model="muse-spark-1.3",
    input=[{
        "type": "message",
        "role": "user",
        "content": [
            {"type": "input_text", "text": instrucciones},
            {"type": "input_video", "file_id": archivo.id},
        ],
    }],
)

ficha = respuesta.output_text
print(ficha)
video.with_name(video.stem + "_formula.txt").write_text(ficha, encoding="utf-8")
