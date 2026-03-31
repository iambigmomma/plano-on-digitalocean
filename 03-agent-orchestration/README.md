# 03 - Intelligent Agent Orchestration

Plano's 4B orchestrator model automatically decides which agent handles each request. No manual routing — the user just sends a message and Plano figures out the rest.

## Architecture

```
User: "Write a bedtime story about a kitten"
  │
  ▼
Plano Gateway (:8001)
  │
  ├─ Plano-Orchestrator-4B (vLLM, ~200ms)
  │  Analyzes: "This is a creative writing request"
  │  Decision: → story_writer
  │
  ▼
Story Writer (:10510) → Opus 4.6 via DO → 4-page story
```

```
User: "Convert this story to image prompts as JSON"
  │
  ▼
Plano Gateway (:8001)
  │
  ├─ Plano-Orchestrator-4B
  │  Analyzes: "This is a structured output request"
  │  Decision: → prompt_crafter
  │
  ▼
Prompt Crafter (:10530) → Llama 3.3 via DO → JSON array
```

## How it works

1. User sends a message to `localhost:8001/v1/chat/completions`
2. Plano forwards the message + agent descriptions to the **Plano-Orchestrator-4B** model (self-hosted on vLLM)
3. The 4B model analyzes intent and returns which agent should handle it
4. Plano routes the request to that agent's HTTP endpoint
5. The agent calls DO Serverless Inference and returns the response

## Agents

| Agent | Port | Model | Task |
|-------|------|-------|------|
| `story_writer` | 10510 | Opus 4.6 | Draft creative stories |
| `story_editor` | 10520 | Opus 4.6 | Polish and refine prose |
| `prompt_crafter` | 10530 | Llama 3.3 | Convert text to image prompts (JSON) |

Each agent is a FastAPI service (~60 lines of Python) in the `agents/` directory.

## Key config: `type: agent`

```yaml
listeners:
  - type: agent                          # NOT type: model
    name: storybook_orchestrator
    port: 8001
    router: plano_orchestrator_v1        # Uses the 4B model
    agents:
      - id: story_writer
        description: |
          StoryWriter drafts original children's bedtime stories.
          Handles: "Write a story about...", "Create a bedtime tale..."
```

The `description` field is what the orchestrator reads to make routing decisions. Good descriptions = accurate routing.

## Setup

```bash
export DO_MODEL_ACCESS_KEY="dop_v1_..."

# 1. Start the orchestrator model (requires GPU)
# See root README for the docker run command

# 2. Start agents
uv run uvicorn agents.story_writer:app --host 0.0.0.0 --port 10510 &
uv run uvicorn agents.story_editor:app --host 0.0.0.0 --port 10520 &
uv run uvicorn agents.prompt_crafter:app --host 0.0.0.0 --port 10530 &

# 3. Start Plano
planoai up config.yaml --with-tracing

# 4. Watch traces (optional, in another terminal)
planoai trace
```

## Test

```bash
# Write a story → routes to story_writer
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"--","messages":[{"role":"user","content":"Write a bedtime story about a dragon"}]}'

# Edit a story → routes to story_editor
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"--","messages":[{"role":"user","content":"Edit this story: PAGE 1: A dog sat. He was sad."}]}'

# Image prompts → routes to prompt_crafter
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"--","messages":[{"role":"user","content":"Convert to image prompts as JSON: PAGE 1: A kitten looked at stars."}]}'
```

## Trace output

```
plano(orchestrator) storybook_orchestrator
  ┣━━ selection.agents: story_writer
  ┣━━ selection.determination_ms: 232.18    ← real 4B model inference
  ┗━━ selection.listener: storybook_orchestrator
```

## What this proves

- **Plano does intelligent routing** — the 4B orchestrator picks the right agent in ~200ms
- **`type: agent`** is the key — not `type: model` (which is a proxy, not an orchestrator)
- **Each agent picks the best model for its task** — Opus 4.6 for creative, Llama 3.3 for structured
- **All on DigitalOcean** — models via DO Serverless Inference, orchestrator on GPU Droplet
- **Full observability** — `planoai trace` and Jaeger show the complete routing chain
