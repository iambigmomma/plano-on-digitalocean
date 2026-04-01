# Frontend — AI Storybook Generator Web UI

Web interface for the storybook generator. Sends requests through Plano's agent listener and renders the results as an illustrated storybook with PDF export.

## Run

```bash
export DO_MODEL_ACCESS_KEY="dop_v1_..."
export PLANO_URL="http://localhost:8001"  # Plano agent listener (Lab 03)

uv run uvicorn app:app --port 8080
# Open http://localhost:8080
```

## Prerequisites

Plano and the agent services from `03-agent-orchestration/` must be running:

- vLLM orchestrator on `:10010`
- Agent services on `:10510`, `:10520`, `:10530`
- `planoai up config.yaml --with-tracing` on `:8001`

## How It Works

The frontend drives a 4-step pipeline, each step as a separate `/api/generate` call:

1. **write** — Plano routes to `story_writer` (Opus 4.6)
2. **edit** — Plano routes to `story_editor` (Opus 4.6)
3. **craft** — Plano routes to `prompt_crafter` (Llama 3.3)
4. **illustrate** — calls DO async-invoke API directly (fal-ai/fast-sdxl)

Steps 1-3 go through Plano's `type: agent` listener (`:8001`), which uses the Plano-Orchestrator-4B to pick the right agent. Step 4 bypasses Plano and calls DO's image generation API directly.
