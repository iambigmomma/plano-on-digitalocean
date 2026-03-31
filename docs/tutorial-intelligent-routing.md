---
title: 'Intelligent Multi-Agent Routing with Plano + DigitalOcean: Build an AI Storybook Generator That Routes Itself'
publishedAt: '2026-04-01'
description: >-
  Deploy a multi-agent AI system where a self-hosted 4B orchestrator model automatically decides which specialized agent handles each request. All models run on DigitalOcean — Opus 4.6, Llama 3.3, and image generation — routed through a single Plano gateway with full observability.
banner: 'plano-intelligent-routing'
tags: 'plano, digitalocean, ai, agents, routing, vllm, gpu'
---

# Intelligent Multi-Agent Routing with Plano + DigitalOcean

## The AI Assembly Line

Imagine you're running an animation studio. You have three specialists: a **storyteller** who writes scripts, an **editor** who polishes dialogue, and an **illustrator** who draws the scenes. When a new project comes in, someone needs to read the brief and decide who works on it first.

That "someone" is usually a human producer — reading emails, assigning tasks, routing work. But what if you had an AI producer who could read every incoming request and instantly route it to the right specialist?

That's what we're building. **Plano** is the producer. It runs a lightweight 4B-parameter model that reads each request, compares it against your agents' capabilities, and routes to the best match — in under 300 milliseconds. The agents themselves call different LLMs on **DigitalOcean Serverless Inference**: Anthropic Claude Opus 4.6 for creative writing, Llama 3.3 for structured output, and image generation via fal-ai.

One gateway. Three agents. Zero manual routing. Full observability.

**Estimated Deployment Time: 30-40 minutes**

**Tutorial Scope: Single GPU server with Docker. No Kubernetes. Plano + vLLM + FastAPI + DigitalOcean Serverless Inference.**

---

## What You'll Build

An AI Storybook Generator where users send natural language requests through one endpoint, and Plano automatically routes them:

```
User: "Write a bedtime story about a kitten who loves stars"
  → Plano Orchestrator (4B model) analyzes intent
  → Routes to Story Writer agent → Opus 4.6 drafts the story

User: "Polish this story to improve the prose rhythm"
  → Routes to Story Editor agent → Opus 4.6 refines the prose

User: "Convert this story to image generation prompts"
  → Routes to Prompt Crafter agent → Llama 3.3 outputs JSON
```

The user never specifies which agent. Plano figures it out.

---

## Key Concept: Two Types of Plano Listeners

Before we build, you need to understand this distinction — it determines which routing mechanism to use.

### `type: model` — LLM Gateway

```yaml
listeners:
  - type: model
    name: llm_proxy
    port: 12000
```

A **proxy layer**. The client sends `model: "openai/gpt-4o"` and Plano forwards to the right provider. Useful for unifying multiple LLM providers behind one endpoint with observability. The client always specifies which model to use.

### `type: agent` — Agent Orchestration

```yaml
listeners:
  - type: agent
    name: my_service
    port: 8001
    router: plano_orchestrator_v1
    agents:
      - id: writer_agent
        description: "Writes creative stories..."
```

An **orchestration layer**. The client sends a natural language message. Plano's orchestrator model reads the message, compares it against each agent's description, and routes to the best match. **This is the one that enables intelligent routing.**

### The Difference

| | `type: model` | `type: agent` |
|---|---|---|
| **What it routes** | API requests → LLM providers | Messages → agent services |
| **Client specifies** | Model name (required) | Nothing — orchestrator decides |
| **Routing brain** | Arch-Router 1.5B | Plano-Orchestrator 4B |
| **Config key** | `llm_routing_model` | `agent_orchestration_model` |
| **Best for** | Multi-provider gateway | Multi-agent orchestration |

<details>
<summary>Why This Matters</summary>

If you use `type: model`, you're building a smart proxy — great for consolidating API keys and adding observability, but the client still decides which model to call. If you use `type: agent`, Plano makes the routing decision for you based on the content of the message. This tutorial uses `type: agent` because that's where the real magic is.

</details>

---

## Architecture

```
  ┌──────────────┐    ┌──────────────┐
  │  Browser     │    │  Jaeger UI   │
  │  :8080       │    │  :16686      │
  └──────┬───────┘    └──────▲───────┘
         │                   │ traces
         ▼                   │
  ┌──────────────────────────┴───────┐
  │  Plano Gateway (:8001)           │
  │  type: agent                     │
  │  router: plano_orchestrator_v1   │
  └──────────────┬───────────────────┘
                 │
  ┌──────────────▼───────────────────┐
  │  Plano-Orchestrator-4B           │
  │  Self-hosted on vLLM (:10010)    │
  │  Analyzes intent → picks agent   │
  │  ~200ms per decision (RTX 6000)  │
  └──────────────┬───────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
  ┌──────┐  ┌──────┐  ┌──────────┐
  │Writer│  │Editor│  │ Crafter  │
  │:10510│  │:10520│  │  :10530  │
  │Opus  │  │Opus  │  │ Llama    │
  │4.6   │  │4.6   │  │ 3.3     │
  └──┬───┘  └──┬───┘  └────┬────┘
     │         │            │
     └─────────┼────────────┘
               │
     ┌─────────▼──────────┐     ┌──────────────┐
     │ DO Serverless      │     │ DO Async      │
     │ Inference          │     │ Invoke        │
     │ inference.do-ai.run│     │ (fal-ai/      │
     │                    │     │  fast-sdxl)   │
     │ Opus 4.6           │     │ Image gen     │
     │ Llama 3.3          │     └──────────────┘
     │ DeepSeek R1        │
     └────────────────────┘
```

**Plano's role:** It sits between the frontend and the agents as an intelligent router. Instead of the application deciding which agent to call, Plano's 4B orchestrator model reads the user's message and picks the right agent automatically. This means adding a new agent is a config change — no application code needs to change.

---

## Prerequisites

Before you begin, make sure you have the following:

- **DigitalOcean GPU Droplet** with NVIDIA GPU (RTX 6000 Ada or similar, ~10GB+ free VRAM for the orchestrator)
- **DigitalOcean Model Access Key** (Control Panel → Gen AI → Model Access Keys)
- **Docker** with NVIDIA Container Toolkit (`nvidia-smi` should work inside Docker)
- **[uv](https://github.com/astral-sh/uv)** for Python tooling
- **Plano CLI**: `uv tool install planoai`
- Basic familiarity with the Linux command line

---

## Part A: Deploy the Orchestrator Model

The orchestrator is a 4B-parameter model that reads user messages and decides which agent should handle them. We self-host it on the GPU Droplet using vLLM.

### Step 1: Download the chat template

The orchestrator model requires a specific chat template for its input format.

```bash
huggingface-cli download katanemo/Plano-Orchestrator-4B \
  --include "*.jinja" \
  --local-dir ~/plano-orchestrator
```

<details>
<summary>Why This Step Matters</summary>

The Plano-Orchestrator-4B model uses a custom chat template that structures agent descriptions and user messages into a format the model was trained on. Without this template, the model receives raw text and produces garbage routing decisions. The template is the contract between Plano and the model.

</details>

---

### Step 2: Start vLLM with the orchestrator model

```bash
docker run -d \
  --name vllm-orchestrator \
  --gpus all \
  -p 10010:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -v ~/plano-orchestrator:/templates \
  vllm/vllm-openai:latest \
  --model katanemo/Plano-Orchestrator-4B \
  --host 0.0.0.0 \
  --port 8000 \
  --tokenizer katanemo/Plano-Orchestrator-4B \
  --chat-template /templates/chat_template.jinja \
  --served-model-name katanemo/Plano-Orchestrator-4B \
  --gpu-memory-utilization 0.3 \
  --max-model-len 4096 \
  --tensor-parallel-size 1 \
  --enable-prefix-caching
```

**Key parameters:**

- `--served-model-name katanemo/Plano-Orchestrator-4B` — Plano looks for this exact name in the config
- `--chat-template /templates/chat_template.jinja` — the custom template from Step 1
- `--gpu-memory-utilization 0.3` — uses 30% of VRAM, leaving room for other models
- `--max-model-len 4096` — the orchestrator only needs to read agent descriptions + one user message, so 4K tokens is plenty

The first run downloads ~8GB of model weights. Watch the logs:

```bash
docker logs -f vllm-orchestrator
```

Wait for:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Press `Ctrl+C` to exit the log stream.

<details>
<summary>Why This Step Matters</summary>

The orchestrator model is the brain of the routing system. Every incoming request passes through it before reaching any agent. Running it on vLLM gives you production-grade serving with PagedAttention for memory efficiency. The 4B model is small enough to share a GPU with other workloads while delivering routing decisions in ~200-300ms.

</details>

![vLLM loading the Plano-Orchestrator-4B model](image-placeholder-step-2)

---

### Step 3: Verify the orchestrator is running

```bash
curl http://localhost:10010/v1/models
```

You should see `katanemo/Plano-Orchestrator-4B` in the response. Also test health:

```bash
curl http://localhost:10010/health
```

<details>
<summary>Why This Step Matters</summary>

If the orchestrator isn't responding, Plano will start but every routing decision will fail silently. Verifying now saves you from debugging a blank `route: null` response later.

</details>

---

## Part B: Build the Agent Services

Each agent is a lightweight FastAPI service that receives OpenAI-compatible chat requests and calls the appropriate LLM on DigitalOcean Serverless Inference.

### Step 4: Understand the agent pattern

Every agent follows the same structure:

1. Receive an OpenAI-compatible `/v1/chat/completions` request
2. Prepend a task-specific system prompt
3. Call the appropriate LLM via DO Serverless Inference (`inference.do-ai.run`)
4. Return the response in OpenAI format

```python
# agents/story_writer.py (simplified)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import OpenAI
import os

app = FastAPI()

SYSTEM_PROMPT = """You are a children's storybook author. Write a short
bedtime story for ages 3-6 with exactly 4 pages..."""

@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    client = OpenAI(
        base_url="https://inference.do-ai.run/v1",
        api_key=os.environ["DO_MODEL_ACCESS_KEY"],
    )
    resp = client.chat.completions.create(
        model="anthropic-claude-opus-4.6",  # Premium model for creative tasks
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + body["messages"],
    )
    return JSONResponse({
        "model": f"story_writer (anthropic-claude-opus-4.6)",
        "choices": [{"message": {"role": "assistant", "content": resp.choices[0].message.content}}],
        ...
    })
```

The key insight: **each agent picks the best model for its task**. The Story Writer uses Opus 4.6 (premium, creative), while the Prompt Crafter uses Llama 3.3 (cheap, fast, good at structured JSON). The user doesn't need to know any of this — Plano routes the request, and the agent picks the model.

<details>
<summary>Why This Step Matters</summary>

Agents are the building blocks of the orchestration system. Each one encapsulates a specific capability — its system prompt, its model choice, its response format. This separation means you can upgrade one agent's model without touching the others, add new agents without changing existing code, and test each agent independently.

</details>

---

### Step 5: Create the three agents

The project structure:

```
03-agent-orchestration/
├── agents/
│   ├── story_writer.py     # Port 10510 — drafts stories (Opus 4.6)
│   ├── story_editor.py     # Port 10520 — polishes prose (Opus 4.6)
│   └── prompt_crafter.py   # Port 10530 — creates image prompts (Llama 3.3)
├── config.yaml
└── pyproject.toml
```

The full source code for each agent is in the [project repository](https://github.com/iambigmomma/plano-on-digitalocean/tree/master/03-agent-orchestration/agents). Each agent is ~60 lines of Python.

### Step 6: Start the agent services

```bash
export DO_MODEL_ACCESS_KEY="dop_v1_..."

cd 03-agent-orchestration

uv run uvicorn agents.story_writer:app --host 0.0.0.0 --port 10510 &
uv run uvicorn agents.story_editor:app --host 0.0.0.0 --port 10520 &
uv run uvicorn agents.prompt_crafter:app --host 0.0.0.0 --port 10530 &
```

Verify all three are running:

```bash
curl -s http://localhost:10510/docs -o /dev/null && echo "Writer: OK"
curl -s http://localhost:10520/docs -o /dev/null && echo "Editor: OK"
curl -s http://localhost:10530/docs -o /dev/null && echo "Crafter: OK"
```

<details>
<summary>Why This Step Matters</summary>

Each agent needs to be reachable as an HTTP service before Plano can route to it. If an agent is down, Plano will return a connection error instead of a routing failure — the traces help you distinguish between "orchestrator picked the wrong agent" and "agent was unreachable."

</details>

---

## Part C: Configure Plano for Intelligent Routing

This is where everything connects. The Plano config tells the gateway where the orchestrator runs, what agents are available, and how to describe each agent's capabilities.

### Step 7: Write the Plano config

```yaml
version: v0.3.0

overrides:
  agent_orchestration_model: plano/katanemo/Plano-Orchestrator-4B

agents:
  - id: story_writer
    url: http://localhost:10510
  - id: story_editor
    url: http://localhost:10520
  - id: prompt_crafter
    url: http://localhost:10530

model_providers:
  # The orchestrator model (self-hosted on vLLM)
  - model: plano/katanemo/Plano-Orchestrator-4B
    base_url: http://localhost:10010

  # LLMs used by agents — all via DO Serverless Inference
  - model: digitalocean/llama3.3-70b-instruct
    base_url: https://inference.do-ai.run
    provider_interface: openai
    access_key: $DO_MODEL_ACCESS_KEY
    default: true

  - model: digitalocean/anthropic-claude-opus-4.6
    base_url: https://inference.do-ai.run
    provider_interface: openai
    access_key: $DO_MODEL_ACCESS_KEY

listeners:
  - type: agent
    name: storybook_orchestrator
    port: 8001
    router: plano_orchestrator_v1
    agents:
      - id: story_writer
        description: |
          StoryWriter is a creative writing agent that drafts original children's
          bedtime stories. It creates warm, imaginative 4-page stories for ages 3-6.
          Handles: "Write a story about...", "Create a bedtime tale..."

      - id: story_editor
        description: |
          StoryEditor polishes and refines story drafts. It improves prose rhythm,
          vivid descriptions, and pacing while preserving the original story.
          Handles: "Edit this story...", "Polish this draft...", "Improve this text..."

      - id: prompt_crafter
        description: |
          PromptCrafter converts story text into structured image generation prompts.
          It outputs a JSON array of visual descriptions for AI image generators.
          Handles: "Create image prompts for...", "Convert to image descriptions..."

tracing:
  random_sampling: 100
```

Three things to pay attention to:

1. **`overrides.agent_orchestration_model`** — points to the orchestrator on vLLM. This is NOT `llm_routing_model` (that's for `type: model` listeners).
2. **`agents` section** — maps agent IDs to their HTTP URLs.
3. **Agent `description`s in the listener** — this is what the orchestrator reads to make routing decisions. Write them like job descriptions: clear capabilities and example trigger phrases.

<details>
<summary>Why This Step Matters</summary>

The agent descriptions are the most important part of the config. The 4B orchestrator model doesn't understand your code — it only reads these descriptions and the user's message, then picks the best match. Vague descriptions lead to wrong routing. Specific descriptions with example phrases lead to accurate routing. Treat them like prompts for the routing model.

</details>

---

### Step 8: Start Plano

```bash
planoai up config.yaml --with-tracing
```

The `--with-tracing` flag enables OpenTelemetry trace collection, which you can view with `planoai trace`.

<details>
<summary>Why This Step Matters</summary>

Tracing is what makes intelligent routing debuggable. Without it, a wrong routing decision is invisible — you just get a weird response and no idea why. With tracing, you can see exactly which agent was selected, how long the decision took, and the full request lifecycle.

</details>

---

## Part D: Test Intelligent Routing

### Step 9: Send requests and observe routing

Open a **second terminal** for live traces:

```bash
planoai trace
```

In your **main terminal**, send three different types of requests:

```bash
# Test 1: Creative writing → should route to story_writer
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "--",
    "messages": [{"role": "user", "content": "Write a bedtime story about a dragon who bakes cookies"}]
  }'

# Test 2: Editing → should route to story_editor
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "--",
    "messages": [{"role": "user", "content": "Edit this story to improve the prose: PAGE 1: A dog sat. He was sad."}]
  }'

# Test 3: Structured output → should route to prompt_crafter
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "--",
    "messages": [{"role": "user", "content": "Convert this story to image generation prompts as JSON: PAGE 1: A kitten looked at stars."}]
  }'
```

Note: the `model: "--"` field is required by the OpenAI API format but ignored by Plano — the orchestrator decides the routing.

In the **trace terminal**, you should see output like:

```
plano(orchestrator) storybook_orchestrator
  ┣━━ selection.agents: story_writer
  ┣━━ selection.determination_ms: 232.18
  ┗━━ selection.listener: storybook_orchestrator

plano(agent) story_writer /v1/chat/completions
  ┣━━ agent_id: story_writer
  ┗━━ message_count: 1
```

The `selection.determination_ms: 232.18` shows the orchestrator model actually running inference — about 200-300ms on an RTX 6000. This is real AI-powered routing, not keyword matching.

<details>
<summary>Why This Step Matters</summary>

This is the payoff moment. Three different request types, one endpoint, zero manual routing. The orchestrator reads each message, matches it against the agent descriptions, and picks the right one. The traces prove it's working and show you exactly how long each decision takes.

</details>

![Trace output showing orchestrator routing decisions](image-placeholder-step-9)

---

## Part E: Frontend (Optional)

The `frontend/` directory contains a web UI that lets users type a story theme and watch the pipeline run in real time.

```bash
cd frontend
uv run uvicorn app:app --host 0.0.0.0 --port 8080 &
```

Open `http://localhost:8080` in your browser. The frontend:
- Shows each pipeline step with the model used
- Generates illustrations via DO async-invoke API
- Renders the final storybook with images
- Supports PDF download (with CJK/multilingual support)

---

## What You've Built

```
Browser (:8080) → Frontend (FastAPI)
                      │
                      ▼
              Plano Gateway (:8001)
                      │
              Plano-Orchestrator-4B (vLLM, ~200ms routing)
                      │
              ┌───────┼───────┐
              ▼       ▼       ▼
           Writer  Editor  Crafter  →  DO Serverless Inference
                                       (Opus 4.6, Llama 3.3, fast-sdxl)
                      │
              Jaeger (:16686) ← traces
```

You now have:

- A **self-hosted 4B orchestrator model** that routes requests by intent
- **Three specialized agents**, each using the optimal LLM for its task
- **All LLMs on DigitalOcean** — including Anthropic Claude Opus 4.6 via DO's pass-through (same endpoint, same API key, no separate Anthropic account)
- **Full observability** via `planoai trace`
- **One gateway endpoint** that handles everything

## What's Happening Under the Hood

1. **Client** sends a message to `localhost:8001/v1/chat/completions`
2. **Plano (Envoy)** receives it and forwards to **brightstaff** (Plano's control plane)
3. **brightstaff** sends the message + all agent descriptions to **Plano-Orchestrator-4B** running on vLLM
4. The **4B model** analyzes intent vs. descriptions and returns a routing decision (~232ms)
5. **Plano** forwards the original request to the selected agent's HTTP endpoint
6. The **agent** calls DO Serverless Inference with its task-specific prompt and model
7. **Plano** streams the response back to the client, logging the full trace

## DigitalOcean Models Used

All models are accessed through DO Serverless Inference (`inference.do-ai.run`) with a single Model Access Key. No third-party API keys needed.

| Model | Used By | Cost | Why |
|-------|---------|------|-----|
| `anthropic-claude-opus-4.6` | Story Writer, Editor | $5/$25 per 1M tokens | Best creative quality |
| `llama3.3-70b-instruct` | Prompt Crafter | $0.65/1M tokens | Fast, cheap, good at JSON |
| `fal-ai/fast-sdxl` | Image generation | ~$0.001/image | Via DO async-invoke API |

Anthropic Opus 4.6 is available as a DO pass-through — same `inference.do-ai.run` endpoint, same `DO_MODEL_ACCESS_KEY`. No separate Anthropic account or API key.

---

## Common Issues and Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| vLLM OOM on startup | `max-model-len` too high or not enough free VRAM | Add `--max-model-len 4096` and reduce `--gpu-memory-utilization` |
| Plano `cannot bind` error | Port conflict with another service or internal Plano listener | Use port 8001 for the agent listener (Plano reserves 10000 and 12000 internally) |
| `route: null` in all responses | Orchestrator model not reachable, or using `type: model` instead of `type: agent` | Verify `curl localhost:10010/v1/models` works; confirm your listener is `type: agent` |
| Agent returns connection error | Agent service not running | Check `curl localhost:10510/docs` for each agent port |
| `determination_ms: 0` | Plano is not calling the external orchestrator | Ensure `overrides.agent_orchestration_model` matches the model name in `model_providers`, and the `base_url` is correct |
| Wrong agent selected | Agent descriptions too vague or overlapping | Make descriptions more specific with example trigger phrases |

---

## Next Steps

- **Add a frontend**: Build a web UI where users type story themes and see illustrated storybooks generated in real-time
- **Add more agents**: Image generation agent, translator agent, narrator agent
- **Deploy to production**: Run Plano + agents on DO App Platform, orchestrator on GPU Droplet
- **Add guardrails**: Plano supports input/output filter chains for content moderation

---

## Related Resources

- [Plano Documentation](https://docs.planoai.dev/)
- [Plano GitHub — Travel Agents Demo](https://github.com/katanemo/plano/tree/main/demos/agent_orchestration/travel_agents)
- [Plano-Orchestrator-4B on HuggingFace](https://huggingface.co/katanemo/Plano-Orchestrator-4B)
- [DigitalOcean Serverless Inference](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/)
- [DigitalOcean GPU Droplets](https://www.digitalocean.com/products/gpu-droplets)
- [Project Source Code](https://github.com/iambigmomma/plano-on-digitalocean)
