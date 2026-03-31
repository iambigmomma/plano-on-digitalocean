# 01 - Quickstart

The simplest Plano setup: proxy requests to OpenAI through a local endpoint.

## Run

```bash
export OPENAI_API_KEY="sk-..."
planoai up config.yaml
```

## Test

```bash
curl http://localhost:12000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Say hello from Plano!"}],
    "model": "gpt-4o-mini"
  }'
```

## What this proves

- Plano CLI installs and runs
- Config format works
- Proxy successfully routes to OpenAI
