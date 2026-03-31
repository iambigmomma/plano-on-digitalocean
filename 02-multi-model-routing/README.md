# 02 - Multi-Model Routing

Route requests to multiple DigitalOcean Serverless Inference models through a single Plano endpoint. **No OpenAI API key needed.**

## Models

| Model | Strength | Cost |
|-------|----------|------|
| `llama3.3-70b-instruct` | General tasks (default) | $0.65/1M tokens |
| `deepseek-r1-distill-llama-70b` | Reasoning / chain-of-thought | $0.99/1M tokens |
| `alibaba-qwen3-32b` | Multilingual / structured output | — |

## Setup

```bash
# 1. Get your Model Access Key from DO Control Panel → Gen AI → Model Access Keys
export DO_MODEL_ACCESS_KEY="dop_v1_..."

# 2. Start Plano
planoai up config.yaml

# 3. Test all models
uv run test.py
```

## Manual test

```bash
curl http://localhost:12000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "digitalocean/llama3.3-70b-instruct",
    "messages": [{"role": "user", "content": "Hello from DO!"}]
  }'
```

## What this proves

- Plano routes to DO Serverless Inference with zero code changes
- Multiple models accessible through one gateway
- Swap `base_url` to `https://inference.do-ai.run` — that's it
- All DO-hosted open-source models, no third-party API keys
