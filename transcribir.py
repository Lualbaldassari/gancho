import json, os, subprocess, sys
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

video = Path(sys.argv[1])
audio = video.with_suffix(".wav")

# 1. Sacar el audio en el formato que pide Meta: WAV mono, 16 bits, 24 kHz
subprocess.run(
    ["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "24000",
     "-c:a", "pcm_s16le", "-map_metadata", "-1", str(audio)],
    check=True, capture_output=True,
)

# 2. Enviarlo a Muse Voice Transcribe
ajustes = {
    "mode": "PUSH_TO_TALK",
    "model": "muse-voice-transcribe-1.0",
    "audioEncoding": "WAV",
    "languageBias": ["Spanish"],
}
with open(audio, "rb") as f:
    r = requests.post(
        "https://api.meta.ai/v1/asr/transcribe",
        headers={"Authorization": f"Bearer {os.environ['MODEL_API_KEY']}"},
        files={
            "request": (None, json.dumps(ajustes), "application/json"),
            "audio": (audio.name, f, "audio/wav"),
        },
        timeout=120,
    )

if not r.ok:
    sys.exit(f"Error {r.status_code}: {r.text}")

datos = r.json()
print(f"Duración: {datos.get('audioDurationMs', 0) / 1000:.1f} s\n")
print(datos["transcript"])
video.with_suffix(".txt").write_text(datos["transcript"], encoding="utf-8")
