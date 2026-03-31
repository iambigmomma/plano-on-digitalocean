# 02 - Multi-Model Routing + Observability

Route different tasks to different DO models through a single Plano gateway, with built-in request tracing.

## Architecture

```
Client (one endpoint)
  │
  ├─ "Write a story"  → Plano → llama3.3-70b (creative, $0.65/1M)
  └─ "Solve 127*49"   → Plano → deepseek-r1-70b (reasoning, $0.99/1M)
```

## Models

| Model | Best for | Cost |
|-------|----------|------|
| `llama3.3-70b-instruct` | Creative writing, general tasks | $0.65/1M tokens |
| `deepseek-r1-distill-llama-70b` | Math, reasoning, editing | $0.99/1M tokens |

## Setup

```bash
# 1. Set your DO Model Access Key
export DO_MODEL_ACCESS_KEY="dop_v1_..."

# 2. Start Plano WITH tracing enabled
planoai up config.yaml --with-tracing

# 3. (In a second terminal) Watch traces live
planoai trace

# 4. (In a third terminal) Run the demo
uv run test.py
```

## What you'll see

### In the test output
Different prompts routed to different models, all through `localhost:12000`.

### In `planoai trace`
Live request traces showing:
- Which model handled each request
- Request/response latency
- Token usage per request
- Full request lifecycle

## What this proves

- **Unified gateway** — one endpoint routes to multiple DO models
- **Observability** — every request is traced, zero instrumentation code
- **Zero vendor lock-in** — swap models by changing config, not code
- **All DO-native** — no OpenAI or third-party API keys needed
