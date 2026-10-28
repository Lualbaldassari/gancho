"""Paso 6: entrega por WhatsApp Cloud API (Meta Graph API).

Sin credenciales trabaja en modo simulado: guarda cada mensaje en
outbox/ para la demo y los tests, con el mismo formato que se enviaría.

Vars de entorno (ver .env.example):
  WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN

API:
  enviar_texto(para, texto) -> dict con {modo, ...}
  enviar_imagen(para, ruta_imagen, caption) -> dict
  enviar_documento(para, ruta_archivo, caption) -> dict
  entregar_guiones(para, video, negocio_path) -> lista de resultados
"""

import base64
import json
import mimetypes
import os
import sys
import urllib.request
from pathlib import Path

from common import artefacto

GRAPH = "https://graph.facebook.com/v21.0"
OUTBOX = Path("outbox")


def _credenciales() -> tuple[str, str] | None:
    token = os.environ.get("WHATSAPP_TOKEN", "").strip()
    phone_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    if token and phone_id:
        return token, phone_id
    return None


def _post_graph(token: str, phone_id: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{GRAPH}/{phone_id}/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _simular(tipo: str, para: str, contenido: dict) -> dict:
    OUTBOX.mkdir(exist_ok=True)
    n = len(list(OUTBOX.glob("*.json"))) + 1
    registro = {"modo": "simulado", "tipo": tipo, "para": para, **contenido}
    (OUTBOX / f"mensaje_{n:02d}_{tipo}.json").write_text(
        json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[simulado → {para}] {tipo}: {contenido.get('preview', '')[:120]}")
    return registro


def enviar_texto(para: str, texto: str) -> dict:
    """Envía texto. WhatsApp corta en ~4096 caracteres; partimos en bloques."""
    cred = _credenciales()
    bloques = [texto[i:i + 3500] for i in range(0, len(texto), 3500)] or [""]
    resultados = []
    for b in bloques:
        if cred is None:
            resultados.append(_simular("texto", para, {"texto": b, "preview": b}))
        else:
            token, phone_id = cred
            resultados.append(_post_graph(token, phone_id, {
                "messaging_product": "whatsapp", "to": para,
                "type": "text", "text": {"body": b},
            }))
    return {"modo": "real" if cred else "simulado", "partes": resultados}


def _subir_media(token: str, phone_id: str, ruta: Path) -> str:
    """Sube un archivo y devuelve su media_id."""
    mime, _ = mimetypes.guess_type(str(ruta))
    mime = mime or "application/octet-stream"
    boundary = "----gancho"
    cuerpo = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{ruta.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + ruta.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{GRAPH}/{phone_id}/media",
        data=cuerpo,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))["id"]


def enviar_imagen(para: str, ruta_imagen: str | Path, caption: str = "") -> dict:
    ruta = Path(ruta_imagen)
    cred = _credenciales()
    if cred is None:
        return _simular("imagen", para, {"archivo": str(ruta), "caption": caption,
                                         "preview": caption or str(ruta)})
    token, phone_id = cred
    media_id = _subir_media(token, phone_id, ruta)
    return _post_graph(token, phone_id, {
        "messaging_product": "whatsapp", "to": para,
        "type": "image", "image": {"id": media_id, "caption": caption[:1024]},
    })


def enviar_documento(para: str, ruta_archivo: str | Path, caption: str = "") -> dict:
    ruta = Path(ruta_archivo)
    cred = _credenciales()
    if cred is None:
        return _simular("documento", para, {"archivo": str(ruta), "caption": caption,
                                            "preview": caption or str(ruta)})
    token, phone_id = cred
    media_id = _subir_media(token, phone_id, ruta)
    return _post_graph(token, phone_id, {
        "messaging_product": "whatsapp", "to": para,
        "type": "document", "document": {"id": media_id, "caption": caption[:1024],
                                         "filename": ruta.name},
    })


def resumir_guiones_para_whatsapp(guiones: str, max_chars: int = 3000) -> str:
    """Versión compacta de los guiones para el primer mensaje."""
    titulos = [l.strip() for l in guiones.splitlines() if "TÍTULO" in l]
    resumen = "🎬 Tus 3 guiones están listos:\n\n"
    for i, t in enumerate(titulos[:3], 1):
        resumen += f"{i}. {t.replace('**', '').replace('TÍTULO Y ÁNGULO:', '').strip()}\n"
    resumen += "\nTe mando el documento completo y las portadas abajo 👇"
    return resumen[:max_chars]


def entregar_guiones(para: str, video: Path, negocio_path: Path) -> list:
    """Entrega completa: resumen + documento + portadas + preguntas."""
    ruta_base = artefacto(video, f"_guiones_verificados_{negocio_path.stem}.txt")
    if not ruta_base.exists():
        ruta_base = artefacto(video, "_guiones_verificados.txt")
    guiones = ruta_base.read_text(encoding="utf-8")

    resultados = [enviar_texto(para, resumir_guiones_para_whatsapp(guiones))]
    resultados.append(enviar_documento(para, ruta_base, "Tus 3 guiones listos para grabar 🎬"))

    for p in sorted(video.parent.glob(f"{video.stem}_portada*.png")):
        resultados.append(enviar_imagen(para, p, f"Portada sugerida: {p.stem}"))

    preguntas_path = artefacto(video, f"_preguntas_{negocio_path.stem}.json")
    if preguntas_path.exists():
        preguntas = json.loads(preguntas_path.read_text(encoding="utf-8"))
        if preguntas:
            resultados.append(enviar_texto(
                para, "❓ Antes de grabar, cuéntame:\n" + "\n".join(f"• {q}" for q in preguntas)))
    if _credenciales() is None:
        generar_preview_html()
    return resultados


def generar_preview_html(salida: Path = OUTBOX / "preview.html") -> Path:
    """Vista tipo celular de los mensajes simulados (para demo y jueces).

    Lee outbox/*.json y genera un HTML autocontenido que se abre con
    doble clic: burbujas de chat, documentos y portadas si existen.
    """
    import html

    mensajes = []
    for f in sorted(OUTBOX.glob("*.json")):
        try:
            mensajes.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue

    burbujas = []
    for m in mensajes[-12:]:
        tipo = m.get("tipo", "texto")
        if tipo == "texto":
            cuerpo = html.escape(m.get("texto", ""))[:1500].replace("\n", "<br>")
            burbujas.append(f'<div class="msg"><p>{cuerpo}</p>'
                            f'<span class="hora">Gancho · simulado</span></div>')
        elif tipo == "documento":
            nombre = html.escape(Path(m.get("archivo", "?")).name)
            cap = html.escape(m.get("caption", ""))
            burbujas.append(f'<div class="msg doc">📄 <b>{nombre}</b><br>{cap}'
                            f'<span class="hora">Gancho · simulado</span></div>')
        elif tipo == "imagen":
            cap = html.escape(m.get("caption", ""))
            ruta = Path(m.get("archivo", ""))
            # Relativa al outbox para que el <img> funcione al abrir el HTML
            try:
                rel = os.path.relpath(ruta, OUTBOX)
            except OSError:
                rel = str(ruta)
            img = (f'<img src="{html.escape(rel)}" loading="lazy">'
                   if ruta.suffix.lower() in (".png", ".jpg", ".jpeg")
                   and ruta.exists() else "🖼️ <i>(portada no generada: "
                   "usa --con-portadas)</i>")
            burbujas.append(f'<div class="msg">{img}<br>{cap}'
                            f'<span class="hora">Gancho · simulado</span></div>')

    salida.write_text(f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gancho · entrega WhatsApp (simulada)</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0b141a;margin:0;padding:16px;color:#e9edef}}
.tel{{max-width:420px;margin:auto;background:#0b141a url('')}}
.msg{{background:#005c4b;border-radius:12px;padding:10px 12px;margin:10px 0;max-width:88%}}
.msg p{{margin:0;white-space:pre-wrap}}
.msg img{{max-width:100%;border-radius:8px}}
.doc{{background:#1f2c34}}
.hora{{display:block;font-size:11px;opacity:.7;text-align:right;margin-top:4px}}
h1{{font-size:18px}} .sub{{opacity:.7;font-size:13px}}
</style></head><body><div class="tel">
<h1>📱 Gancho → WhatsApp</h1>
<p class="sub">Vista simulada de lo que recibe la dueña ({len(mensajes)} mensajes).
Con WHATSAPP_TOKEN en .env se envía de verdad.</p>
{''.join(burbujas) or '<p><i>Sin mensajes: corre demo.py primero.</i></p>'}
</div></body></html>""", encoding="utf-8")
    print(f"Vista previa del chat: {salida}")
    return salida


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit('Uso: python whatsapp.py <para> "<texto>" | --entregar <video> --negocio <txt>')
    para = sys.argv[1]
    if sys.argv[2] == "--entregar":
        if len(sys.argv) < 4:
            sys.exit("Uso: python whatsapp.py <para> --entregar <video> [--negocio <txt>]")
        video = Path(sys.argv[3])
        negocio = Path(sys.argv[sys.argv.index("--negocio") + 1]) if "--negocio" in sys.argv else Path("negocio.txt")
        entregar_guiones(para, video, negocio)
    else:
        enviar_texto(para, sys.argv[2])


if __name__ == "__main__":
    main()
