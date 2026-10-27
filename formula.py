import os, sys, json
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

# 2. Molde de la ficha. Es un texto normal (no f-string) para no tener que
#    duplicar las llaves { } del JSON.
molde = """{
  "gancho": {
    "segundos": "0-3",
    "que_se_ve": "...",
    "que_se_dice": "...",
    "por_que_funciona": "..."
  },
  "estructura": [
    {"segundos": "0-3", "bloque": "gancho", "que_pasa": "..."}
  ],
  "formato": "reseña | tutorial | antes/después | storytime | POV | lista | otro",
  "ritmo_y_edicion": "...",
  "emocion": "...",
  "llamada_a_la_accion": "...",
  "formula_reutilizable": [
    "Paso 1: ... [hueco] ..."
  ],
  "datos_del_negocio_necesarios": [
    {"hueco": "[nombre del hueco]", "pregunta": "...", "por_que": "...", "si_no_tiene": "..."}
  ]
}"""

# 3. Pedir la ficha de fórmula viral en JSON
instrucciones = f"""Eres un estratega de contenido de TikTok para emprendedores peruanos.
Mira el video y usa esta transcripción de lo que se dice:

\"\"\"{transcripcion}\"\"\"

Responde SOLO con un JSON válido que siga este molde, sin texto antes ni después
y sin bloques de código:

{molde}

Reglas:
- Todo en español.
- "gancho", "estructura", "formato", "ritmo_y_edicion", "emocion" y
  "llamada_a_la_accion" describen el video ORIGINAL tal como es.
- "estructura": todos los bloques del video, cada uno con su segundo aproximado.
- "formula_reutilizable": de 4 a 6 pasos que el propio DUEÑO graba con su celular
  en su negocio (no un cliente ni un influencer que lo visita).
- Los [huecos] deben servir para cualquier rubro (comida, ropa, belleza,
  servicios...). Nómbralos por su función, como [producto estrella] o
  [lo que lo hace especial], nunca por lo que sale en el video original
  (nada de sus productos, su local ni su dirección).
- "datos_del_negocio_necesarios": máximo 5 elementos. Si un mismo dato llena
  varios huecos, júntalos en una sola pregunta. "pregunta" es lo que le
  preguntaríamos al dueño: corta, en español peruano sencillo y tuteando, y que
  sirva para un negocio chico (un puesto, una tienda o un emprendimiento en casa).
  "por_que" explica en una línea para qué sirve ese dato. "si_no_tiene" dice
  cómo adaptar el paso si el dueño no tiene eso.
- No inventes nada que no se vea o escuche en el video."""

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

texto = respuesta.output_text

# 4. Convertir la respuesta en datos. A veces el modelo agrega texto alrededor,
#    así que nos quedamos con lo que va de la primera { a la última }.
inicio = texto.find("{")
fin = texto.rfind("}") + 1
try:
    ficha = json.loads(texto[inicio:fin])
except json.JSONDecodeError:
    video.with_name(video.stem + "_formula_error.txt").write_text(texto, encoding="utf-8")
    sys.exit("La respuesta no vino en JSON válido. La guardé en _formula_error.txt para revisarla.")

# 5. Guardar: .json para los siguientes pasos y .txt para que crear_video.py siga funcionando
bonito = json.dumps(ficha, ensure_ascii=False, indent=2)
print(bonito)
video.with_name(video.stem + "_formula.json").write_text(bonito, encoding="utf-8")
video.with_name(video.stem + "_formula.txt").write_text(bonito, encoding="utf-8")
