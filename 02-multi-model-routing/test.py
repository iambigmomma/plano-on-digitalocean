"""
Demo: Multi-Model Routing + Observability through Plano → DigitalOcean

Sends different types of prompts to different DO models through Plano,
then shows you can trace every request with `planoai trace`.

Prerequisites:
  export DO_MODEL_ACCESS_KEY="dop_v1_..."
  planoai up config.yaml --with-tracing     # <-- enables trace collection
  # In another terminal:
  planoai trace                              # <-- watch traces live

Usage:
  uv run test.py
"""

from openai import OpenAI

PLANO_URL = "http://localhost:12000/v1"
client = OpenAI(base_url=PLANO_URL, api_key="unused")

test_cases = [
    {
        "model": "digitalocean/llama3.3-70b-instruct",
        "prompt": "Write a 2-sentence bedtime story about a dragon who bakes cookies.",
        "task": "Creative Writing",
    },
    {
        "model": "digitalocean/deepseek-r1-distill-llama-70b",
        "prompt": "What is 127 * 49? Show your step-by-step reasoning.",
        "task": "Math Reasoning",
    },
    {
        "model": "digitalocean/llama3.3-70b-instruct",
        "prompt": "Write a haiku about cloud computing.",
        "task": "Creative Writing",
    },
    {
        "model": "digitalocean/deepseek-r1-distill-llama-70b",
        "prompt": "A train leaves Station A at 60 km/h. Another leaves Station B (300 km away) at 90 km/h heading toward A. When do they meet?",
        "task": "Logic Problem",
    },
]

print("=" * 65)
print("  Plano Multi-Model Routing + Observability Demo")
print("  All models on DigitalOcean Serverless Inference")
print("=" * 65)
print()
print("  Tip: Run `planoai trace` in another terminal to see live traces!")
print()

for i, case in enumerate(test_cases, 1):
    model_short = case["model"].split("/")[-1]
    print(f"{'─'*65}")
    print(f"  [{i}] {case['task']}  →  {model_short}")
    print(f"  Prompt: {case['prompt'][:55]}...")
    print(f"{'─'*65}")

    resp = client.chat.completions.create(
        model=case["model"],
        messages=[{"role": "user", "content": case["prompt"]}],
        max_tokens=200,
    )

    content = (resp.choices[0].message.content or "").strip().replace("\n", " ")
    print(f"  Response: {content[:150]}...")
    print()

print("=" * 65)
print("  Done! Check `planoai trace` output for request traces.")
print("  Each trace shows: model selected, latency, token usage.")
print("=" * 65)
