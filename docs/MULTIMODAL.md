# Desktop multimodal setup

JARVIS can fuse **local** webcam pose/heuristics and microphone prosody into the assistant system prompt (no raw video/audio is persisted server-side by default).

## Quick start

1. Enable in `.env`: `MULTIMODAL_ENABLED=true`
2. Start the API: `python -m jarvis serve`
3. In another terminal, run the desktop bridge: `python -m jarvis multimodal`
4. Open the web UI and chat — the stats bar shows **gesture** / **tone** when events arrive.

Optional flags:

- `python -m jarvis multimodal --camera 1 --no-mic`
- `MULTIMODAL_WS_URL=ws://127.0.0.1:8000/ws` if your API port differs

## Dependencies

The bridge needs:

```bash
pip install opencv-python-headless mediapipe
```

Microphone emotion cues use `sounddevice` + `librosa` (already listed in `requirements.txt`).

Check readiness: `GET /api/multimodal/status`

## Manual acceptance checklist

- [ ] `/api/multimodal/status` reports `desktop_dependencies.ok` after installing OpenCV + MediaPipe
- [ ] With `MULTIMODAL_ENABLED=true`, raising both hands triggers `attention_request` in the UI gesture field
- [ ] Speaking near the mic updates **tone** (emotion label) within a few seconds
- [ ] Chat replies subtly reflect multimodal context when enabled (no forced narration)
- [ ] Setting `MULTIMODAL_ENABLED=false` stops context injection; bridge may still connect but events are ignored

## Privacy defaults

- Processing is local; the API only receives **compact JSON events** (labels, scores), not video streams.
- Fusion window and max context size are capped via `MULTIMODAL_FUSION_WINDOW_S` and `MULTIMODAL_MAX_CONTEXT_CHARS`.
