"""Paso 5: verificador auto-corrector — revisa, corrige y pregunta (máx 5).

CLI:  python verificar.py videos/prueba.mp4 [--negocio negocios/jugueria.txt]
API:  verificar(video, negocio_path) -> (guiones_finales, preguntas)
"""

import json
import re
import sys
from pathlib import Path

from common import (artefacto, guardar_json, guardar_texto, leer_json_seguro,
                    pedir, validar_negocio, validar_video)

MAX_RONDAS = 3

# Precios tipo S/ 8, S/8.50, s/. 120 — los comparamos exactos contra datos reales
RE_PRECIO = re.compile(r"S/\s?\.?\s?\d+(?:[.,]\d{1,2})?", re.IGNORECASE)
RE_CONFIRMAR = re.compile(r"\[CONFIRMAR:[^\]]*\]")


def cargar_datos(video: Path, negocio_path: Path) -> tuple[str, str, str]:
    negocio = negocio_path.read_text(encoding="utf-8")
    original = video.with_suffix(".txt").read_text(encoding="utf-8")
    ruta_guiones = artefacto(video, f"_guiones_{negocio_path.stem}.txt")
    if not ruta_guiones.exists():
        ruta_guiones = artefacto(video, "_guiones.txt")
    guiones = ruta_guiones.read_text(encoding="utf-8")

    ruta_entrevista = artefacto(video, f"_entrevista_{negocio_path.stem}.json")
    if ruta_entrevista.exists():
        entrevista = ruta_entrevista.read_text(encoding="utf-8")
    elif artefacto(video, "_entrevista.json").exists():
        entrevista = artefacto(video, "_entrevista.json").read_text(encoding="utf-8")
    else:
        entrevista = "(No hubo entrevista.)"
        print("Aviso: no encontré la entrevista; solo uso el texto del negocio.")

    datos_reales = f"""{negocio}

RESPUESTAS DEL DUEÑO EN LA ENTREVISTA (también son datos reales; si una
respuesta dice "NO TIENE", el negocio no tiene eso):
{entrevista}"""
    return datos_reales, original, guiones


def _sin_confirmar(texto: str) -> str:
    """Quita los bloques [CONFIRMAR: …]: ya están marcados, no son errores."""
    return RE_CONFIRMAR.sub("", texto)


def chequeo_precios(guiones: str, datos_reales: str) -> list:
    """Determinista (sin API): todo precio del guion debe estar en los datos."""
    reales = {p.upper().replace(" ", "") for p in RE_PRECIO.findall(datos_reales)}
    problemas = []
    for precio in set(RE_PRECIO.findall(_sin_confirmar(guiones))):
        if precio.upper().replace(" ", "") not in reales:
            problemas.append({
                "tipo": "precio",
                "frase": precio,
                "explicacion": f"El precio {precio} no aparece en los datos reales.",
                "pregunta_para_dueno": f"¿Cuánto cuesta exactamente? (vi {precio} sin confirmar)",
                "origen": "regla",
            })
    return problemas


def chequeo_copia(guiones: str, original: str, n: int = 6) -> list:
    """Determinista (sin API): frases de n+ palabras copiadas del original."""
    def ngramas(texto: str) -> set:
        pals = re.findall(r"\w+", texto.lower())
        return {" ".join(pals[i:i + n]) for i in range(len(pals) - n + 1)}

    original_ng = ngramas(original)
    problemas = []
    for linea in _sin_confirmar(guiones).splitlines():
        for ng in ngramas(linea):
            if ng in original_ng:
                problemas.append({
                    "tipo": "copia",
                    "frase": linea.strip()[:160],
                    "explicacion": f"Frase casi igual al video original («…{ng}…»).",
                    "pregunta_para_dueno": "",
                    "origen": "regla",
                })
                break
    return problemas


def revisar(guiones: str, datos_reales: str, original: str) -> list:
    """Reglas deterministas + Muse; devuelve lista de problemas en JSON."""
    respuesta = pedir(f"""Eres un verificador estricto. Revisa estos guiones de TikTok.

DATOS REALES DEL NEGOCIO (lo único que se sabe con certeza):
\"\"\"{datos_reales}\"\"\"

TRANSCRIPCIÓN DEL VIDEO ORIGINAL (no se puede copiar):
\"\"\"{original}\"\"\"

GUIONES:
\"\"\"{guiones}\"\"\"

Busca solo estos problemas:
- "inventado": un hecho sobre el negocio, la dueña o sus clientes que NO está en los datos reales:
  historias personales, ingredientes, horarios, hábitos (ej. "lo pruebo todos los días"),
  o lo que piden o piensan los clientes (ej. "me lo están pidiendo", "a la gente le gusta").
  Describir la escena (ej. "el pan humeando") NO es inventado, pero nombrar productos,
  ingredientes, precios o clientes que no están en los datos SÍ lo es, aunque esté en la
  columna "qué se ve".
  Si los datos dicen "NO TIENE", afirmar que el negocio lo tiene también es inventado.
- "precio": un precio o total que no cuadra con los datos reales o que puede confundir
  (ej. precios sueltos al lado de un combo sin decir cuánto cuesta el combo).
- "copia": una frase copiada o casi igual a la transcripción original.
- "promesa": una promesa falsa o exagerada (ganancias, salud, "el mejor").

IMPORTANTE: ignora todo texto entre [CONFIRMAR: ...]. Ya está marcado para que la dueña
lo confirme, así que NO es un problema. Tampoco reportes la frase que lo acompaña por ese motivo.

Responde SOLO con JSON, sin texto antes ni después, con esta forma:
{{"problemas": [{{"tipo": "...", "frase": "texto exacto del guion",
  "explicacion": "...", "pregunta_para_dueno": "pregunta corta, o vacío si no aplica"}}]}}
Si no hay problemas: {{"problemas": []}}""")
    try:
        de_modelo = leer_json_seguro(respuesta).get("problemas", [])
    except (ValueError, json.JSONDecodeError):
        print("  ⚠ el revisor no devolvió JSON; solo aplican las reglas.")
        de_modelo = []
    for p in de_modelo:
        p.setdefault("origen", "modelo")
    # Reglas primero (deterministas, auditables), luego el modelo.
    return chequeo_precios(guiones, datos_reales) + \
        chequeo_copia(guiones, original) + de_modelo


def corregir(guiones: str, problemas: list, datos_reales: str) -> str:
    """Muse reescribe los guiones arreglando cada problema."""
    return pedir(f"""Corrige estos guiones de TikTok. Mantén el mismo formato, tono y estructura.

DATOS REALES DEL NEGOCIO:
\"\"\"{datos_reales}\"\"\"

PROBLEMAS A CORREGIR:
{json.dumps(problemas, ensure_ascii=False, indent=2)}

Reglas:
- Si un dato fue inventado, quítalo o reemplázalo por un [CONFIRMAR: ...] para que la dueña lo llene.
- Si un precio confunde, usa solo los precios reales y aclara qué incluye.
- Si hay una frase copiada, reescríbela con otras palabras.
- No agregues ningún dato nuevo que no esté en los datos reales.
- No quites datos que sí están en los datos reales si no son parte de un problema.

GUIONES:
\"\"\"{guiones}\"\"\"

Devuelve solo los guiones corregidos.""")


def resumir_preguntas(preguntas: list, datos_reales: str) -> list:
    """Muse descarta lo ya respondido, junta las repetidas y deja máximo 5."""
    respuesta = pedir(f"""Estas son preguntas para la dueña de un negocio antes de grabar sus videos de TikTok.
Muchas se repiten o dicen lo mismo con otras palabras:

{json.dumps(preguntas, ensure_ascii=False, indent=2)}

Esto ya lo sabemos, así que NO lo vuelvas a preguntar:
\"\"\"{datos_reales}\"\"\"

Descarta las preguntas que ya están respondidas arriba, junta las repetidas y devuelve
como máximo 5, las más importantes para poder grabar.
Escríbelas cortas y en un tono amable, como se las diría alguien por WhatsApp.
Responde SOLO con JSON: {{"preguntas": ["...", "..."]}}
Si no queda ninguna: {{"preguntas": []}}""")
    return leer_json_seguro(respuesta)["preguntas"]


def verificar(video: Path, negocio_path: Path, forzar: bool = False) -> tuple[str, list]:
    sufijo = f"_guiones_verificados_{negocio_path.stem}.txt"
    salida = artefacto(video, sufijo)
    ruta_preguntas = artefacto(video, f"_preguntas_{negocio_path.stem}.json")
    if salida.exists() and ruta_preguntas.exists() and not forzar:
        print(f"Ya existe {salida}, la reutilizo (--forzar para rehacer).")
        return salida.read_text(encoding="utf-8"), json.loads(ruta_preguntas.read_text(encoding="utf-8"))

    datos_reales, original, guiones = cargar_datos(video, negocio_path)

    preguntas: list = []
    rondas: list = []
    for ronda in range(1, MAX_RONDAS + 1):
        problemas = revisar(guiones, datos_reales, original)
        print(f"\n--- Ronda {ronda}: {len(problemas)} problema(s) ---")
        for p in problemas:
            print(f"[{p['tipo']}/{p.get('origen', '?')}] {p['frase']}\n   -> {p['explicacion']}")
            if p.get("pregunta_para_dueno"):
                preguntas.append(p["pregunta_para_dueno"])
        rondas.append({"ronda": ronda,
                       "problemas": [(p.get("tipo"), p.get("origen")) for p in problemas]})
        if not problemas:
            print("Guiones aprobados.")
            break
        guiones = corregir(guiones, problemas, datos_reales)
    else:
        print("\nSe alcanzó el máximo de rondas; revisa a mano lo que quede.")

    guardar_json(artefacto(video, f"_reporte_verificacion_{negocio_path.stem}.json"),
                 {"rondas": rondas, "preguntas_candidatas": preguntas})
    guardar_texto(salida, guiones)
    guardar_texto(artefacto(video, "_guiones_verificados.txt"), guiones)
    print(f"\nGuiones finales guardados en {salida}")

    finales: list = []
    if preguntas:
        finales = resumir_preguntas(preguntas, datos_reales)
        if finales:
            print("\nPreguntas para la dueña antes de grabar:")
            for q in finales:
                print(f"- {q}")
        else:
            print("\nNo hay preguntas pendientes: todo lo necesario ya lo sabemos.")
    guardar_json(ruta_preguntas, finales)
    return guiones, finales


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit("Uso: python verificar.py <video.mp4> [--negocio <txt>]")
    video = validar_video(args[0])
    negocio_path = Path("negocio.txt")
    if "--negocio" in args:
        negocio_path = validar_negocio(args[args.index("--negocio") + 1])
    verificar(video, negocio_path)


if __name__ == "__main__":
    main()
