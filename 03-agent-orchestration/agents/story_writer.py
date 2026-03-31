"""
Story Writer Agent — drafts children's bedtime stories.
Runs as a standalone FastAPI service on port 10510.
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
    You are a children's storybook author. Write a short bedtime
    story for ages 3-6. The story should be warm, imaginative,
    and have a gentle moral.

    Format your output as exactly 4 pages, using this format:

    PAGE 1:
    [2-3 sentences for page 1]

    PAGE 2:
    [2-3 sentences for page 2]

    PAGE 3:
    [2-3 sentences for page 3]

    PAGE 4:
    [2-3 sentences for page 4, with a warm ending]

    Keep each page to 2-3 simple sentences. Use vivid but
    simple language that children can understand.
""")


def get_client():
    return OpenAI(base_url=DO_URL, api_key=os.environ["DO_MODEL_ACCESS_KEY"])


@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])

    # Prepend system prompt
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=full_messages,
        temperature=0.9,
        max_tokens=800,
    )

    return JSONResponse({
        "id": resp.id,
        "object": "chat.completion",
        "model": f"story_writer ({MODEL})",
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
    uvicorn.run(app, host="0.0.0.0", port=10510)
