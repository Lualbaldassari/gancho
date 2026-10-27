# Gancho

An agent that takes a viral TikTok video, extracts its winning formula, and adapts it into a ready-to-shoot script for a small Peruvian business. Delivered over WhatsApp.

Built for the **Meta Global AI Developer Hackathon** (Oct 27 – Nov 4, 2026). All code in this repository was written during the hackathon.

## Meta models used
- **Muse Voice Transcribe** (`muse-voice-transcribe-1.0`): transcribes the video's audio
- **Muse Spark** (`muse-spark-1.3`): watches the video and extracts the viral formula
- Coming next: Muse Image, SAM 3.1, WhatsApp Cloud API

All AI calls go to the Meta Model API (`https://api.meta.ai/v1`). The `openai` Python package is used only as the HTTP client, as shown in Meta's official quickstart.

## Progress log
- **Day 1 (Oct 27):** first Muse Spark call, video transcription, viral formula extraction
- **Day 1 (cont.):** script generator + self-correcting verifier agent (catches invented facts, misleading prices, copied lines; asks the owner max 5 questions)
