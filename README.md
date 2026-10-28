# Gancho

> **Doña Rosa tiene una juguería y 0 ideas para TikTok. Manda un video viral por WhatsApp y recibe 3 guiones adaptados a SU negocio, con portadas y lista para grabar — sin inventar precios ni prometer milagros.**

Un agente que toma un TikTok viral, extrae su fórmula ganadora y la adapta en guiones listos para grabar para un negocio peruano chico. Entregado por WhatsApp.

Built for the **Meta Global AI Developer Hackathon** (Oct 27 – Nov 4, 2026). All code in this repository was written during the hackathon.

## Para jueces (3 minutos, sin clave, sin gastar API)

```bash
.venv/bin/python check.py   # salud del proyecto: deps, ffmpeg, artefactos, tests
.venv/bin/python demo.py    # la demo de 90 segundos: fórmula → guiones → WhatsApp
.venv/bin/python eval.py    # prueba del diferenciador anti-alucinación
```

Luego abre `outbox/preview.html`: es el chat de WhatsApp tal como lo ve la dueña.
El guion hablado de la demo está en [DEMO_GUION.md](DEMO_GUION.md).

## Meta models used

- **Muse Voice Transcribe** (`muse-voice-transcribe-1.0`): transcribe el audio del video
- **Muse Spark** (`muse-spark-1.3`): mira el video, extrae la fórmula, genera guiones, verifica
- **Muse Image** (`muse-image-1.0`): portadas verticales TikTok, una por guion
- **SAM 3.1** (`sam.py`): contrato listo — del "plano cerrado" genérico al recorte real del producto (ver `sam.py`; fallback determinista sin dependencias mientras el endpoint se habilita)
- **WhatsApp Cloud API**: entrega de guiones + portadas + preguntas (`whatsapp.py`, `servidor.py`)

All AI calls go to the Meta Model API (`https://api.meta.ai/v1`). The `openai` Python package is used only as the HTTP client, as shown in Meta's official quickstart.

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env   # pon tu MODEL_API_KEY
python main.py videos/prueba.mp4 --negocio negocios/jugueria.txt --no-interactivo
```

Un comando corre todo el agente: transcribir → fórmula → entrevista → guiones → verificar → (portadas, WhatsApp).

## Arquitectura

```
video viral ──► transcribir.py ──► formula.py ──► entrevista.py ──► crear_video.py ──► verificar.py ──► WhatsApp
 (TikTok)      (Voice Transcribe)  (Spark ve el   (Spark pregunta  (Spark escribe    (revisa+corrige,   (resumen +
                                    video + JSON)   solo lo que      3 guiones)        máx 3 rondas,      documento +
                                    estructura +    falta)                             máx 5 preguntas)   portadas)
                                    4-6 pasos +
                                    máx 5 huecos
                                                         │                                  │
                                                         ▼                                  ▼
                                                   portadas.py ◄── guiones verificados ──► sam.py
                                                  (Muse Image,                          (bbox producto →
                                                   1 portada/guion)                      sugerencia encuadre)
```

Cada paso guarda su artefacto junto al video (`_formula.json`, `_entrevista_<negocio>.json`,
`_guiones_verificados_<negocio>.txt`, `_portadaN_<negocio>.png`) y lo reutiliza si ya existe
(`--forzar` para rehacer). Los pasos siguen funcionando sueltos para debug.

## Demo en 90 segundos (sin gastar API)

```bash
python demo.py
```

Lee los artefactos ya generados, muestra fórmula → entrevista → antes/después del verificador
y simula la entrega WhatsApp en `outbox/`. Con `--con-imagenes` genera las 3 portadas.

Versión en vivo (gasta API, ~3-5 min, 3 rubros): `bash demo_vivo.sh`.

## WhatsApp

Sin credenciales, todo se simula en `outbox/` con el mismo formato. Para envío real:

```bash
# .env: WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN
python main.py videos/prueba.mp4 --negocio negocios/jugueria.txt --no-interactivo \
  --con-portadas --enviar-whatsapp --para 51999999999
```

Webhook (la dueña manda el video por chat y recibe los guiones):

```bash
python servidor.py --negocio negocios/jugueria.txt   # + ngrok http 8000
```

## Generalización multi-rubro

La misma fórmula viral se adapta a 3 negocios distintos sin cambiar código:

| Rubro | Negocio | Hueco ejemplo → respuesta |
|---|---|---|
| Comida | `negocios/jugueria.txt` | [combo] → 2 panes + jugo surtido |
| Ropa | `negocios/ropa.txt` | [combo] → pack 2 polos S/60 |
| Belleza | `negocios/belleza.txt` | [combo] → dúo laceados −20% mar/mié |

Respuestas de entrevista reproducibles en `ejemplos/respuestas_*.json` (modo `--no-interactivo`).

## Anti-alucinación (el diferenciador)

1. `entrevista.py` solo pregunta lo que el texto del negocio no responde.
2. `crear_video.py` escribe `[CONFIRMAR: …]` en vez de inventar.
3. `verificar.py` revisa 4 tipos de error (inventado, precio, copia, promesa): reglas deterministas auditables (precio, copia) + revisor LLM, corrige hasta 3 rondas y resume a máx 5 preguntas. Cada corrida guarda su reporte en `videos/*_reporte_verificacion_*.json`.

Mismo video, verificador antes vs después de la entrevista: **9 flags (6 falsas alarmas) → 4 reales, 0 falsas alarmas; preguntas 5 → 1.**
Verifícalo sin API: `eval.py` corre las reglas sobre los artefactos incluidos y una sonda adversaria demuestra que sí detectan.

## Progress log

- **Day 1 (Oct 27):** first Muse Spark call, video transcription, viral formula extraction
- **Day 1 (cont.):** script generator + self-correcting verifier agent (catches invented facts, misleading prices, copied lines; asks the owner max 5 questions)
- **Day 1 (night):** viral formula now outputs structured JSON with owner questions; new owner-interview step that only asks what the business info doesn't answer; scripts and verifier treat interview answers as real data. Same scripts, verifier before vs after: 9 flags (6 false alarms) → 4 real issues, 0 false alarms; owner questions 5 → 1.
- **Day 2:** single-agent orchestrator (`main.py`); per-business artifacts; non-interactive interview fixtures; WhatsApp Cloud API delivery + webhook (`whatsapp.py`, `servidor.py`, simulated `outbox/` without credentials); Muse Image covers per script (`portadas.py`); SAM 3.1 framing contract (`sam.py`); 3-business fixtures (`negocios/`); 90-second zero-API demo (`demo.py`) + live multi-vertical demo (`demo_vivo.sh`); shared client/config (`common.py`), `requirements.txt`, `.env.example`.
