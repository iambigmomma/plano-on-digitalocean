# 03 - Agent Orchestration: AI Storybook Generator

Generate a children's bedtime storybook with illustrations — powered entirely by DigitalOcean Serverless Inference, routed through Plano.

## Architecture

```
User: "a kitten who is scared of the dark"
         |
         v   (task-aware routing picks the best model per step)
  Story Writer   (Opus 4.6)   → Draft 4-page story       [creative]
         |
  Story Editor   (Opus 4.6)   → Polish prose and pacing   [editing]
         |
  Prompt Crafter (Llama 3.3)  → Image prompts as JSON     [structured]
         |
  Illustrator    (fast-sdxl)  → 4 watercolor illustrations [image_gen]
         |
  Assembler      (Python)     → HTML storybook
```

All models accessed through one Plano gateway at `localhost:12000`.
Anthropic Claude Opus 4.6 is available via DO's pass-through — same endpoint, same API key.

## Models

| Model | Task | Why | Cost |
|-------|------|-----|------|
| `anthropic-claude-opus-4.6` | Writing, editing | Best creative quality | $5/$25 per 1M |
| `llama3.3-70b-instruct` | Structured output | Fast, cheap, reliable JSON | $0.65/1M |
| `deepseek-r1-distill-llama-70b` | Reasoning | Strong chain-of-thought | $0.99/1M |
| `fal-ai/fast-sdxl` | Illustrations | Fast image generation | ~$0.001/image |

## Setup

```bash
# 1. Set your DO Model Access Key
export DO_MODEL_ACCESS_KEY="dop_v1_..."

# 2. Start Plano with tracing (terminal 1)
planoai up config.yaml --with-tracing

# 3. Watch traces live (terminal 2, optional)
planoai trace

# 4. Generate a storybook (terminal 3)
uv run storybook.py "a brave little robot who learns to dream"
```

## Routing Modes

```bash
# Task-aware (default) — best model per step
uv run storybook.py "a kitten and the stars"

# Premium — Claude Opus 4.6 for all text steps
uv run storybook.py --premium "a kitten and the stars"

# Economy — Llama 3.3 for everything (cheapest)
uv run storybook.py --economy "a kitten and the stars"

# Text only (skip image generation)
uv run storybook.py --no-images "a kitten and the stars"
```

## What this demo shows

1. **Task-aware model routing** — Different models for different tasks, all through one gateway
2. **DO-native stack** — Anthropic Opus 4.6 + Llama + DeepSeek + image gen, all via DO Serverless Inference
3. **Plano as unified gateway** — Single endpoint, multiple providers, zero code changes to swap models
4. **Observability** — `planoai trace` shows every request with model, latency, token usage
5. **Cost optimization** — Premium models only where quality matters, cheap models for mechanical tasks
6. **Tangible output** — A real illustrated storybook, not just API responses
