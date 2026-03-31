"""
Prompt Crafter Agent — converts story pages into image generation prompts.
Runs as a standalone FastAPI service on port 10530.
Uses Llama 3.3 70B via DO Serverless Inference (fast, cheap, good at JSON).
"""

import os
import textwrap

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import OpenAI

app = FastAPI()

DO_URL = "https://inference.do-ai.run/v1"
MODEL = "llama3.3-70b-instruct"

SYSTEM_PROMPT = textwrap.dedent("""\
    You convert children's story pages into image generation
    prompts. For each page, create a detailed prompt suitable
    for an AI image generator.

    Rules:
    - Output exactly 4 prompts, one per page
    - Format as a JSON array of 4 strings
    - Style: soft watercolor children's book illustration,
      warm colors, gentle lighting, whimsical
    - Include the main character's appearance consistently
    - Describe the scene, mood, and key visual elements
    - Do NOT include any text or words in the image
    - Output ONLY the JSON array, no other text
    - Do NOT include any thinking or explanation
""")


def get_client():
    return OpenAI(base_url=DO_URL, api_key=os.environ["DO_MODEL_ACCESS_KEY"])


@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])

    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=full_messages,
        temperature=0.4,
        max_tokens=2000,
    )

    return JSONResponse({
        "id": resp.id,
        "object": "chat.completion",
        "model": f"prompt_crafter ({MODEL})",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": resp.choices[0].message.content,
            },
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
            "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            "total_tokens": resp.usage.total_tokens if resp.usage else 0,
        },
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10530)
