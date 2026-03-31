# Plano on DigitalOcean

Using [Plano](https://planoai.dev) as the AI gateway for DigitalOcean's Serverless Inference — routing, orchestration, and multi-model collaboration without third-party API keys.

## Structure

| Directory | Description | Status |
|-----------|-------------|--------|
| `01-quickstart/` | Basic Plano proxy — get it running | Done |
| `02-multi-model-routing/` | Route to 3 DO models through one gateway | Done |
| `03-agent-orchestration/` | **AI Storybook Generator** — 4 models collaborate to create illustrated children's stories | Done |
| `04-vllm-integration/` | Plano + vLLM on DO GPU Droplet | Planned |

## The Demo: AI Storybook Generator

The headline demo in `03-agent-orchestration/` generates a children's bedtime storybook:

```
"a kitten who is scared of the dark"
  → Story Writer   (llama3.3-70b)        writes the draft
  → Story Editor   (deepseek-r1-70b)     polishes the prose
  → Prompt Crafter (qwen3-32b)           creates image prompts
  → Illustrator    (flux/schnell)        generates watercolor illustrations
  → Assembler      (Python)              outputs an HTML storybook
```

All models run on DigitalOcean Serverless Inference. Total cost per storybook: < $0.01.

## Prerequisites

- A DigitalOcean account with a **Model Access Key** (Control Panel → Gen AI → Model Access Keys)
- [uv](https://github.com/astral-sh/uv) for Python tooling
- Plano CLI: `uv tool install planoai`

## Quick Start

```bash
# 1. Set your DO credentials
export DO_MODEL_ACCESS_KEY="dop_v1_..."

# 2. Start Plano
cd 03-agent-orchestration
planoai up config.yaml

# 3. Generate a storybook (in another terminal)
cd 03-agent-orchestration
uv run storybook.py "a brave little robot who learns to dream"

# 4. Open the generated HTML file in your browser
```
