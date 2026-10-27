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
ficha = video.with_name(video.stem + "_formula.json").read_text(encoding="utf-8")
negocio = Path("negocio.txt").read_text(encoding="utf-8")

# Las respuestas de la entrevista con el dueño (si ya se hizo)
ruta_entrevista = video.with_name(video.stem + "_entrevista.json")
if ruta_entrevista.exists():
    entrevista = ruta_entrevista.read_text(encoding="utf-8")
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

respuesta = client.responses.create(model="muse-spark-1.3", input=instrucciones)

guiones = respuesta.output_text
print(guiones)
video.with_name(video.stem + "_guiones.txt").write_text(guiones, encoding="utf-8")
