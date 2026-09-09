# Sale Deed Chain Validator — Prototype

Upload the sale deeds for a property → click **Analyze** → each deed is read into structured
data **one at a time** → a combined **chain verdict** shows whether ownership flows unbroken.

**Design spine:** *the AI reads, the code judges.* Gemini extracts each deed; deterministic Python
(`chain.py`) decides whether the chain holds — so the verdict is explainable and testable.

## Run

```bash
cp .env.example .env          # then paste your Google AI Studio key into GEMINI_API_KEY
./run.sh                      # → http://localhost:8000
```

Requires [`uv`](https://docs.astral.sh/uv/) (already installed). `run.sh` resolves deps on first run.

> This build does **real** extraction — it needs `GEMINI_API_KEY`. There is no mock path.

## Units (each does one thing)

| File | Role |
|---|---|
| `schema.py` | the `DeedRecord` contract — shared by extraction and chain logic |
| `ingest.py` | file (PDF/image) → normalised PNG page images |
| `extract.py` | page images → `DeedRecord` via Gemini *(the only model call)* |
| `analyze_deed.py` | per-deed checks (Tier 1: deed-type, completeness, red flags) |
| `chain.py` | cross-deed validation → link + overall verdict *(deterministic core IP)* |
| `report.py` | assemble the combined payload for the UI |
| `app.py` | FastAPI: upload + Server-Sent-Events analyze stream |
| `static/` | the single-page UI (upload + progressive render) |

## Test

```bash
uv run pytest -q        # verifies the chain engine: clean / weak / gap / broken
```

## Prototype limits

Local, single-user, no auth, in-memory sessions, files in `uploads/`. It **flags for a human,
never auto-clears** title, and does **not** verify against the government registry (no official
API exists — that's the Phase-2 advisory path). Not production-hardened.
