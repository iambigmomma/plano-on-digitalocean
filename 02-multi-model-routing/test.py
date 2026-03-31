"""
Test multi-model routing through Plano → DigitalOcean Serverless Inference.

Prerequisites:
  export DO_MODEL_ACCESS_KEY="dop_v1_..."
  planoai up config.yaml

Usage:
  uv run test.py
"""

from openai import OpenAI

PLANO_URL = "http://localhost:12000/v1"
client = OpenAI(base_url=PLANO_URL, api_key="unused")

models = [
    ("digitalocean/llama3.3-70b-instruct", "What is DigitalOcean in one sentence?"),
    ("digitalocean/deepseek-r1-distill-llama-70b", "What is 15 * 37? Think step by step."),
    ("digitalocean/alibaba-qwen3-32b", "Translate 'Hello World' to Japanese, Korean, and Chinese."),
]

for model, prompt in models:
    print(f"\n{'='*60}")
    print(f"Model: {model}")
    print(f"Prompt: {prompt}")
    print("-" * 60)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )
    print(resp.choices[0].message.content)

print(f"\n{'='*60}")
print("All 3 models routed through Plano successfully!")
