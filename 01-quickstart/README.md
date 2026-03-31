# 01 - Quickstart

The simplest Plano setup: proxy requests to DigitalOcean Serverless Inference through a local endpoint.

## Run

```bash
export DO_MODEL_ACCESS_KEY="dop_v1_..."
planoai up config.yaml
```

## Test

```bash
curl http://localhost:12000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "digitalocean/llama3.3-70b-instruct",
    "messages": [{"role": "user", "content": "Say hello from Plano!"}]
  }'
```

## What this proves

- Plano CLI installs and runs
- Config format works
- Proxy successfully routes to DO Serverless Inference
- No OpenAI key needed — all on DigitalOcean
