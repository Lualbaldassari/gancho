import json, os, re, sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://api.meta.ai/v1",
    api_key=os.environ["MODEL_API_KEY"],
)

video = Path(sys.argv[1])
negocio = Path("negocio.txt").read_text(encoding="utf-8")
original = video.with_suffix(".txt").read_text(encoding="utf-8")
guiones = video.with_name(video.stem + "_guiones.txt").read_text(encoding="utf-8")
MAX_RONDAS = 3


def pedir(texto):
    return client.responses.create(model="muse-spark-1.3", input=texto).output_text


def leer_json(texto):
    limpio = re.sub(r"^```(json)?|```$", "", texto.strip(), flags=re.M).strip()
    return json.loads(limpio)


def revisar(guiones):
    """Muse revisa los guiones y devuelve una lista de problemas en JSON."""
    respuesta = pedir(f"""Eres un verificador estricto. Revisa estos guiones de TikTok.

DATOS REALES DEL NEGOCIO (lo único que se sabe con certeza):
\"\"\"{negocio}\"\"\"

TRANSCRIPCIÓN DEL VIDEO ORIGINAL (no se puede copiar):
\"\"\"{original}\"\"\"

GUIONES:
\"\"\"{guiones}\"\"\"

Busca solo estos problemas:
- "inventado": un hecho sobre el negocio, la dueña o sus clientes que NO está en los datos reales
  (historias personales, ingredientes, horarios, cosas que dijeron clientes, etc.).
  Describir lo que se ve en cámara (ej. "el pan humeando") NO es inventado.
- "precio": un precio o total que no cuadra con los datos reales o que puede confundir.
- "copia": una frase copiada o casi igual a la transcripción original.
- "promesa": una promesa falsa o exagerada (ganancias, salud, "el mejor").

IMPORTANTE: ignora todo texto entre [CONFIRMAR: ...]. Ya está marcado para que la dueña
lo confirme, así que NO es un problema. Tampoco reportes la frase que lo acompaña por ese motivo.

Responde SOLO con JSON, sin texto antes ni después, con esta forma:
{{"problemas": [{{"tipo": "...", "frase": "texto exacto del guion",
  "explicacion": "...", "pregunta_para_dueno": "pregunta corta, o vacío si no aplica"}}]}}
Si no hay problemas: {{"problemas": []}}""")
    return leer_json(respuesta)["problemas"]


def corregir(guiones, problemas):
    """Muse reescribe los guiones arreglando cada problema."""
    return pedir(f"""Corrige estos guiones de TikTok. Mantén el mismo formato, tono y estructura.

DATOS REALES DEL NEGOCIO:
\"\"\"{negocio}\"\"\"

PROBLEMAS A CORREGIR:
{json.dumps(problemas, ensure_ascii=False, indent=2)}

Reglas:
- Si un dato fue inventado, quítalo o reemplázalo por un [CONFIRMAR: ...] para que la dueña lo llene.
- Si un precio confunde, usa solo los precios reales y aclara qué incluye.
- Si hay una frase copiada, reescríbela con otras palabras.
- No agregues ningún dato nuevo que no esté en los datos reales.

GUIONES:
\"\"\"{guiones}\"\"\"

Devuelve solo los guiones corregidos.""")


def resumir_preguntas(preguntas):
    """Muse junta las preguntas repetidas y deja solo las 5 más importantes."""
    respuesta = pedir(f"""Estas son preguntas para la dueña de un negocio antes de grabar sus videos de TikTok.
Muchas se repiten o dicen lo mismo con otras palabras:

{json.dumps(preguntas, ensure_ascii=False, indent=2)}

Júntalas y devuelve como máximo 5, las más importantes para poder grabar.
Escríbelas cortas y en un tono amable, como se las diría alguien por WhatsApp.
Responde SOLO con JSON: {{"preguntas": ["...", "..."]}}""")
    return leer_json(respuesta)["preguntas"]


preguntas = []
for ronda in range(1, MAX_RONDAS + 1):
    problemas = revisar(guiones)
    print(f"\n--- Ronda {ronda}: {len(problemas)} problema(s) ---")
    for p in problemas:
        print(f"[{p['tipo']}] {p['frase']}\n   -> {p['explicacion']}")
        if p.get("pregunta_para_dueno"):
            preguntas.append(p["pregunta_para_dueno"])
    if not problemas:
        print("Guiones aprobados.")
        break
    guiones = corregir(guiones, problemas)
else:
    print("\nSe alcanzó el máximo de rondas; revisa a mano lo que quede.")

salida = video.with_name(video.stem + "_guiones_verificados.txt")
salida.write_text(guiones, encoding="utf-8")
print(f"\nGuiones finales guardados en {salida}")

if preguntas:
    print("\nPreguntas para la dueña antes de grabar:")
    for q in resumir_preguntas(preguntas):
        print(f"- {q}")
