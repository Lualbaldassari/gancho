"""Webhook de WhatsApp para Gancho (solo stdlib, sin dependencias).

  python servidor.py [--puerto 8000] [--negocio negocios/jugueria.txt]

Flujo demo:
  1. La dueña manda un video viral (o su media_id) por WhatsApp.
  2. El servidor lo descarga, corre main.py y le devuelve los guiones.

Verificación del webhook (Meta developers → WhatsApp → Configuration):
  URL: https://<tu-ngrok>/webhook   TOKEN: el de WHATSAPP_VERIFY_TOKEN
"""

import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "gancho_verify")
APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET", "").strip()
NEGOCIO_DEFAULT = "negocios/jugueria.txt"
TIMEOUT_PIPELINE_S = 600
MAX_WORKERS = 2
_workers = threading.BoundedSemaphore(MAX_WORKERS)


def descargar_media(media_id: str, destino: Path) -> Path:
    token = os.environ["WHATSAPP_TOKEN"]
    meta = json.loads(urllib.request.urlopen(urllib.request.Request(
        f"https://graph.facebook.com/v21.0/{media_id}",
        headers={"Authorization": f"Bearer {token}"}), timeout=30).read())
    urllib.request.urlretrieve(
        urllib.request.Request(meta["url"], headers={"Authorization": f"Bearer {token}"}),
        destino)
    return destino


def procesar_video(origen: Path, negocio: str, para: str) -> None:
    """Corre el pipeline y entrega por WhatsApp. Va en hilo aparte."""
    cmd = [sys.executable, "main.py", str(origen), "--negocio", negocio,
           "--no-interactivo", "--enviar-whatsapp", "--para", para]
    print(f"[workers] {' '.join(cmd)}", flush=True)
    with _workers:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=TIMEOUT_PIPELINE_S)
        except subprocess.TimeoutExpired:
            print(f"[worker] TIMEOUT tras {TIMEOUT_PIPELINE_S}s: {origen}", flush=True)
            return
    print(r.stdout[-2000:], flush=True)
    if r.returncode != 0:
        print(f"[worker] ERROR:\n{r.stderr[-2000:]}", flush=True)


def firma_valida(cuerpo: bytes, firma: str) -> bool:
    """Valida X-Hub-Signature-256 si hay WHATSAPP_APP_SECRET en .env."""
    if not APP_SECRET:
        return True
    esperada = "sha256=" + hmac.new(APP_SECRET.encode(), cuerpo,
                                    hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, firma or "")


class Handler(BaseHTTPRequestHandler):
    negocio = NEGOCIO_DEFAULT

    def log_message(self, *a):
        pass

    def _ok(self, cuerpo: bytes = b"ok"):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        # Verificación del webhook por Meta
        from urllib.parse import parse_qs, urlparse
        q = parse_qs(urlparse(self.path).query)
        if (q.get("hub.mode") == ["subscribe"]
                and q.get("hub.verify_token") == [VERIFY_TOKEN]):
            self._ok(q.get("hub.challenge", [""])[0].encode())
        else:
            self.send_response(403)
            self.end_headers()

    def do_POST(self):
        largo = int(self.headers.get("Content-Length", 0))
        cuerpo = self.rfile.read(largo) or b"{}"
        if not firma_valida(cuerpo, self.headers.get("X-Hub-Signature-256", "")):
            self.send_response(403)
            self.end_headers()
            return
        try:
            data = json.loads(cuerpo)
        except json.JSONDecodeError:
            self._ok()
            return
        self._ok()  # responder rápido; procesar en fondo
        try:
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    for msg in change.get("value", {}).get("messages", []):
                        self._atender(msg)
        except Exception as e:  # noqa: BLE001 — el webhook nunca debe tumbarse
            print(f"[webhook] error: {e}", flush=True)

    def _atender(self, msg: dict) -> None:
        from whatsapp import enviar_texto

        para = msg.get("from", "")
        if msg.get("type") == "video":
            if not os.environ.get("WHATSAPP_TOKEN"):
                enviar_texto(para, "Estoy en modo demo y no puedo descargar videos. "
                                   "Escríbeme DEMO y te muestro un ejemplo. 🎬")
                return
            media_id = re.sub(r"[^A-Za-z0-9_-]", "", msg["video"]["id"])[:64]
            destino = Path("videos") / f"wa_{media_id}.mp4"
            destino.parent.mkdir(exist_ok=True)
            try:
                descargar_media(media_id, destino)
            except Exception as e:  # noqa: BLE001 — avisar, no tumbar el webhook
                print(f"[webhook] no se pudo descargar {media_id}: {e}", flush=True)
                enviar_texto(para, "No pude descargar tu video, ¿me lo reenvías? 🙏")
                return
            threading.Thread(target=procesar_video,
                             args=(destino, self.negocio, para), daemon=True).start()
        elif msg.get("type") == "text":
            # Comandos de demo por texto: "demo" usa el video de ejemplo
            cuerpo = msg.get("text", {}).get("body", "").strip().lower()
            if cuerpo in ("demo", "ejemplo", "prueba") and Path("videos/prueba.mp4").exists():
                threading.Thread(target=procesar_video,
                                 args=(Path("videos/prueba.mp4"), self.negocio, para),
                                 daemon=True).start()
            else:
                enviar_texto(para, "Hola 👋 Mándame un video viral de TikTok y te devuelvo "
                                   "3 guiones adaptados a tu negocio. (O escribe DEMO para probar.)")


def main() -> None:
    puerto = 8000
    if "--puerto" in sys.argv:
        puerto = int(sys.argv[sys.argv.index("--puerto") + 1])
    if "--negocio" in sys.argv:
        Handler.negocio = sys.argv[sys.argv.index("--negocio") + 1]
    print(f"Gancho escuchando en http://localhost:{puerto}/webhook "
          f"(negocio: {Handler.negocio})")
    if not APP_SECRET:
        print("Aviso: sin WHATSAPP_APP_SECRET no se valida la firma del webhook.")
    print("Para exponerlo a Meta: ngrok http 8000")
    HTTPServer(("0.0.0.0", puerto), Handler).serve_forever()


if __name__ == "__main__":
    main()
