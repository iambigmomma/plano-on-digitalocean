# Plano on DigitalOcean

Using [Plano](https://planoai.dev) as the AI gateway for DigitalOcean's Serverless Inference — task-aware routing, multi-model orchestration, and observability. All models (including Anthropic Claude Opus 4.6) accessed through one DO endpoint, one API key.

## Structure

| Directory | Description | Status |
|-----------|-------------|--------|
| `01-quickstart/` | Basic Plano proxy — get it running | Done |
| `02-multi-model-routing/` | Route to 3 DO models + tracing observability | Done |
| `03-agent-orchestration/` | **AI Storybook Generator** — task-aware routing across Opus 4.6, Llama, DeepSeek + image gen | Done |
| `04-vllm-integration/` | Plano + vLLM on DO GPU Droplet | Planned |

## The Demo: AI Storybook Generator

The headline demo in `03-agent-orchestration/` generates an illustrated children's bedtime storybook with task-aware model routing:

```
"a kitten who is scared of the dark"
  → Story Writer   (Opus 4.6)       writes the draft         [creative]
  → Story Editor   (Opus 4.6)       polishes the prose       [editing]
  → Prompt Crafter (Llama 3.3)      creates image prompts    [structured]
  → Illustrator    (fast-sdxl)      generates illustrations   [image_gen]
  → Assembler      (Python)         outputs HTML storybook
```

Premium model (Opus 4.6) for creative tasks, cheap model (Llama 3.3) for mechanical tasks. All through one Plano gateway, all on DigitalOcean.

## Prerequisites

- A DigitalOcean account with a **Model Access Key** (Control Panel → Gen AI → Model Access Keys)
- [uv](https://github.com/astral-sh/uv) for Python tooling
- Plano CLI: `uv tool install planoai`

## Quick Start

```bash
# 1. Set your DO credentials
export DO_MODEL_ACCESS_KEY="dop_v1_..."

# 2. Start Plano with tracing
cd 03-agent-orchestration
planoai up config.yaml --with-tracing

# 3. Watch traces (optional, in another terminal)
planoai trace

# 4. Generate a storybook
uv run storybook.py "a brave little robot who learns to dream"

# 5. Open the generated HTML file in your browser
```
