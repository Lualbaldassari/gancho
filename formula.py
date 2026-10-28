"""Paso 2: video + transcripción → ficha de fórmula viral en JSON (Muse Spark).

CLI:  python formula.py videos/prueba.mp4
API:  extraer_formula(video) -> dict de la ficha
"""

import sys
from pathlib import Path

from common import (REINTENTOS_API, artefacto, get_client, guardar_json,
                    guardar_texto, leer_json_seguro, validar_video,
                    MODELO_SPARK)

MOLDE = """{
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


def extraer_formula(video: Path, forzar: bool = False) -> dict:
    import json

    salida_json = artefacto(video, "_formula.json")
    if salida_json.exists() and not forzar:
        print(f"Ya existe {salida_json}, la reutilizo (--forzar para rehacer).")
        return json.loads(salida_json.read_text(encoding="utf-8"))

    transcripcion_path = video.with_suffix(".txt")
    if not transcripcion_path.exists():
        sys.exit(f"Falta la transcripción: corre antes transcribir.py sobre {video}")
    transcripcion = transcripcion_path.read_text(encoding="utf-8")

    client = get_client()

    # 1. Subir el video (se borra solo en 1 hora)
    with open(video, "rb") as f:
        archivo = client.files.create(
            purpose="user_data",
            file=f,
            expires_after={"anchor": "created_at", "seconds": 3600},
        )
    print(f"Video subido: {archivo.id}\n")

    # 2. Pedir la ficha de fórmula viral en JSON
    instrucciones = f"""Eres un estratega de contenido de TikTok para emprendedores peruanos.
Mira el video y usa esta transcripción de lo que se dice:

\"\"\"{transcripcion}\"\"\"

Responde SOLO con un JSON válido que siga este molde, sin texto antes ni después
y sin bloques de código:

{MOLDE}

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

    ficha = None
    texto = ""
    for intento in range(1, REINTENTOS_API + 1):
        respuesta = client.responses.create(
            model=MODELO_SPARK,
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
        try:
            candidata = leer_json_seguro(texto)
            faltan = {"formula_reutilizable", "datos_del_negocio_necesarios",
                      "gancho", "formato"} - set(candidata)
            if faltan:
                raise ValueError(f"faltan claves: {sorted(faltan)}")
            ficha = candidata
            break
        except (ValueError, json.JSONDecodeError) as e:
            if intento < REINTENTOS_API:
                print(f"  ⚠ fórmula inválida ({e}); reintento {intento + 1}…")
    if ficha is None:
        artefacto(video, "_formula_error.txt").write_text(texto, encoding="utf-8")
        sys.exit("La respuesta no vino en JSON válido. La guardé en "
                 "_formula_error.txt para revisarla.")

    # 4. Guardar: .json para los siguientes pasos y .txt para inspección
    import json as _json

    bonito = _json.dumps(ficha, ensure_ascii=False, indent=2)
    print(bonito)
    guardar_json(salida_json, ficha)
    guardar_texto(artefacto(video, "_formula.txt"), bonito)
    return ficha


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Uso: python formula.py <video.mp4>")
    extraer_formula(validar_video(sys.argv[1]))


if __name__ == "__main__":
    main()
