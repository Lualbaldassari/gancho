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
ficha = json.loads(video.with_name(video.stem + "_formula.json").read_text(encoding="utf-8"))
negocio = Path("negocio.txt").read_text(encoding="utf-8")
datos = ficha["datos_del_negocio_necesarios"]
datos_texto = json.dumps(datos, ensure_ascii=False, indent=2)

# 1. Muse Spark separa lo que ya sabemos de lo que hay que preguntar.
#    El molde es un texto normal (no f-string) para no duplicar las llaves.
molde = """{
  "ya_sabemos": [
    {"hueco": "[...]", "respuesta": "solo lo que dice el texto del negocio"}
  ],
  "preguntar": [
    {"hueco": "[...]", "pregunta": "..."}
  ]
}"""

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

{molde}"""

respuesta = client.responses.create(model="muse-spark-1.3", input=instrucciones)
texto = respuesta.output_text

# Igual que en formula.py: nos quedamos con lo que va de la primera { a la última }
inicio = texto.find("{")
fin = texto.rfind("}") + 1
try:
    plan = json.loads(texto[inicio:fin])
except json.JSONDecodeError:
    sys.exit("La respuesta no vino en JSON válido:\n" + texto)

# El plan B ("si_no_tiene") de cada hueco, para usarlo si el dueño no tiene algo
plan_b = {d["hueco"]: d.get("si_no_tiene", "") for d in datos}

entrevista = []

# 2. Mostrar lo que ya sabemos
print("Esto ya lo sé por tu negocio:")
for d in plan["ya_sabemos"]:
    print(f"  - {d['hueco']}: {d['respuesta']}")
    entrevista.append({"hueco": d["hueco"], "respuesta": d["respuesta"], "fuente": "negocio.txt"})

# 3. Preguntar lo que falta, una por una
print("\nTe hago unas preguntas. Si no tienes algo, deja vacío y presiona Enter.\n")
for d in plan["preguntar"]:
    r = input(d["pregunta"] + "\n> ").strip()
    if r.lower() in ("", "no", "no tengo"):
        entrevista.append({"hueco": d["hueco"], "respuesta": "NO TIENE",
                           "plan_b": plan_b.get(d["hueco"], ""), "fuente": "dueño"})
    else:
        entrevista.append({"hueco": d["hueco"], "respuesta": r, "fuente": "dueño"})
    print()

# 4. Guardar las respuestas para crear_video.py
salida = video.with_name(video.stem + "_entrevista.json")
salida.write_text(json.dumps(entrevista, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Listo. Guardé las respuestas en {salida}")
