# 03 - Agent Orchestration: AI Storybook Generator

Generate a children's bedtime storybook with illustrations — powered entirely by DigitalOcean.

Four AI models collaborate through Plano to write, edit, illustrate, and assemble a storybook:

```
User: "a kitten who is scared of the dark"
         |
         v
  Story Writer (llama3.3-70b)    → Draft 4-page story
         |
         v
  Story Editor (deepseek-r1-70b) → Polish prose and pacing
         |
         v
  Prompt Crafter (qwen3-32b)     → Convert pages to image prompts
         |
         v
  Illustrator (flux/schnell)     → Generate 4 watercolor illustrations
         |
         v
  Assembler (Python)             → HTML storybook you can open in a browser
```

## Setup

```bash
# 1. Set your DO Model Access Key
export DO_MODEL_ACCESS_KEY="dop_v1_..."

# 2. Start Plano gateway (in a separate terminal)
planoai up config.yaml

# 3. Generate a storybook
uv run storybook.py "a brave little robot who learns to dream"
```

## Options

```bash
# Random theme
uv run storybook.py

# Custom output path
uv run storybook.py -o my_story.html "a penguin who dreams of flying"

# Text only (skip image generation)
uv run storybook.py --no-images "a shy firefly"
```

## What this demo shows

1. **Multi-model orchestration** — 4 different models, each chosen for its strength
2. **DO-native stack** — All models hosted on DigitalOcean, no third-party API keys
3. **Plano as gateway** — Single endpoint routes to the right model per task
4. **Text + Image** — Combines text inference and image generation in one pipeline
5. **Tangible output** — A real storybook, not just API responses

## Architecture

| Agent | Model | Role | Why this model |
|-------|-------|------|----------------|
| Story Writer | `llama3.3-70b-instruct` | Draft creative story | Fast, creative, cheap |
| Story Editor | `deepseek-r1-distill-llama-70b` | Polish and refine | Strong reasoning for structure |
| Prompt Crafter | `alibaba-qwen3-32b` | Text → image prompts | Good at structured output |
| Illustrator | `fal-ai/flux/schnell` | Generate illustrations | Fast image gen on DO |

All text models route through Plano. Image generation goes directly to DO Serverless Inference.

## Cost

A single storybook generation costs approximately **< $0.01 USD** in API usage.
