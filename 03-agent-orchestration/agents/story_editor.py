"""
Story Editor Agent — polishes and refines story drafts.
Runs as a standalone FastAPI service on port 10520.
Uses Anthropic Claude Opus 4.6 via DO Serverless Inference.
"""

import os
import textwrap

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import OpenAI

app = FastAPI()

DO_URL = "https://inference.do-ai.run/v1"
MODEL = "anthropic-claude-opus-4.6"

SYSTEM_PROMPT = textwrap.dedent("""\
    You are a children's book editor. Polish the following story
    draft. Improve the prose rhythm, make descriptions more
    vivid, and ensure the pacing feels right for a bedtime story.

    Rules:
    - Keep the exact same 4-page structure (PAGE 1: ... PAGE 4:)
    - Keep each page to 2-3 sentences
    - Keep language simple enough for ages 3-6
    - Preserve the original story and moral
    - Only output the polished story, nothing else
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
        temperature=0.5,
        max_tokens=800,
    )

    return JSONResponse({
        "id": resp.id,
        "object": "chat.completion",
        "model": f"story_editor ({MODEL})",
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
    uvicorn.run(app, host="0.0.0.0", port=10520)
