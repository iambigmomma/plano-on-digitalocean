"""
Storybook Frontend — serves the web UI and proxies requests to Plano.
"""

import json
import os
import time
import urllib.request
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

PLANO_URL = os.environ.get("PLANO_URL", "http://localhost:8001")
DO_INFERENCE_URL = "https://inference.do-ai.run"
IMAGE_MODEL = "fal-ai/fast-sdxl"


class GenerateRequest(BaseModel):
    theme: str
    step: str  # "write", "edit", "craft", "illustrate"
    context: str = ""  # previous step output


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    """Send a request through Plano's intelligent routing."""

    if req.step == "write":
        prompt = f"Write a bedtime story about: {req.theme}"
    elif req.step == "edit":
        prompt = f"Please edit and polish this story draft to improve the prose rhythm and make it more vivid:\n\n{req.context}"
    elif req.step == "craft":
        prompt = f"Convert this story into image generation prompts. Output a JSON array of 4 strings, one per page:\n\n{req.context}"
    elif req.step == "illustrate":
        return await generate_image(req.context)
    else:
        raise HTTPException(400, f"Unknown step: {req.step}")

    # Call Plano agent listener
    import httpx
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{PLANO_URL}/v1/chat/completions",
            json={
                "model": "--",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
            },
        )
        data = resp.json()

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    model = data.get("model", "unknown")

    return JSONResponse({"content": content, "model": model, "step": req.step})


async def generate_image(prompt: str):
    """Generate an image via DO async-invoke API."""
    api_key = os.environ.get("DO_MODEL_ACCESS_KEY", "")
    if not api_key:
        raise HTTPException(500, "DO_MODEL_ACCESS_KEY not set")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Submit async job
    submit_data = json.dumps({
        "model_id": IMAGE_MODEL,
        "input": {"prompt": prompt},
    }).encode()
    req = urllib.request.Request(
        f"{DO_INFERENCE_URL}/v1/async-invoke",
        data=submit_data, headers=headers, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    request_id = result.get("request_id")
    if not request_id:
        raise HTTPException(500, "No request_id from DO")

    # Poll for completion
    status_url = f"{DO_INFERENCE_URL}/v1/async-invoke/{request_id}/status"
    for _ in range(45):
        time.sleep(2)
        req = urllib.request.Request(status_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        if result.get("status") == "COMPLETED":
            images = result.get("output", {}).get("images", [])
            if images:
                return JSONResponse({
                    "content": images[0]["url"],
                    "model": IMAGE_MODEL,
                    "step": "illustrate",
                })
            raise HTTPException(500, "No image in result")
        if result.get("status") in ("FAILED", "CANCELLED"):
            raise HTTPException(500, f"Image generation {result['status']}")

    raise HTTPException(504, "Image generation timed out")


# Serve static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(static_dir / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
