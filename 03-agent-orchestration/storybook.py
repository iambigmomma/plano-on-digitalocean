"""
AI Storybook Generator — Plano + DigitalOcean Demo

Generates a children's bedtime storybook with illustrations using
multiple AI models orchestrated through Plano, all powered by
DigitalOcean Serverless Inference. No OpenAI key needed.

Pipeline:
  1. Story Writer   → Draft a 4-page story
  2. Story Editor   → Polish prose and pacing
  3. Prompt Crafter → Convert pages to image prompts
  4. Illustrator    → Generate illustrations via DO
  5. Assembler      → Combine into HTML storybook

Model routing is task-aware: each step selects the best model for
the job. Use --economy to run everything on the cheapest model,
or --premium to use Claude Opus 4.6 for all text steps.

Usage:
  export DO_MODEL_ACCESS_KEY="dop_v1_..."
  planoai up config.yaml --with-tracing    # terminal 1
  planoai trace                            # terminal 2 (optional)
  uv run storybook.py "a kitten who is scared of the dark"  # terminal 3
"""

import argparse
import base64
import json
import os
import random
import re
import sys
import textwrap
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from openai import OpenAI

# ---------------------------------------------------------------------------
# Models — all on DigitalOcean Serverless Inference via Plano
# ---------------------------------------------------------------------------

MODELS = {
    "opus": "digitalocean/anthropic-claude-opus-4.6",  # $5/$25 per 1M — premium
    "llama": "digitalocean/llama3.3-70b-instruct",     # $0.65/1M — fast, cheap
    "deepseek": "digitalocean/deepseek-r1-distill-llama-70b",  # $0.99/1M — reasoning
}

# Task-to-model mapping: each step picks the best model for the job
TASK_ROUTING = {
    "creative":   "opus",      # Story writing needs imagination + style
    "editing":    "opus",      # Editing needs nuanced literary judgment
    "structured": "llama",     # JSON generation — fast and reliable
}

# Estimated cost per 1K tokens (input/output avg) for display
MODEL_COST_PER_1K = {
    "opus": 0.015,
    "llama": 0.00065,
    "deepseek": 0.00099,
}

IMAGE_MODEL = "fal-ai/fast-sdxl"
PLANO_URL = "http://localhost:12000/v1"
DO_INFERENCE_URL = "https://inference.do-ai.run/v1"
NUM_PAGES = 4

RANDOM_THEMES = [
    "a shy firefly who wants to light up the whole forest",
    "a little cloud who is afraid of thunder",
    "a baby dragon who sneezes flowers instead of fire",
    "a penguin who dreams of flying to the moon",
    "a tiny robot who learns what friendship means",
    "a kitten who is scared of the dark but loves stars",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_plano_client() -> OpenAI:
    """Client that routes through Plano gateway."""
    return OpenAI(base_url=PLANO_URL, api_key="unused")


def get_do_api_key() -> str:
    """Get the DO Model Access Key for direct API calls (image generation)."""
    key = os.environ.get("DO_MODEL_ACCESS_KEY", "")
    if not key:
        print("ERROR: Set DO_MODEL_ACCESS_KEY environment variable.")
        sys.exit(1)
    return key


def resolve_model(task: str, mode: str) -> str:
    """Pick the right model based on task type and routing mode."""
    if mode == "premium":
        return MODELS["opus"]
    if mode == "economy":
        return MODELS["llama"]
    # Default: task-aware routing
    model_key = TASK_ROUTING.get(task, "llama")
    return MODELS[model_key]


def model_short_name(full_name: str) -> str:
    """Extract short display name from full model path."""
    return full_name.split("/")[-1] if "/" in full_name else full_name


def strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks from DeepSeek/Qwen responses."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def step_header(num: str, title: str, model: str, task_type: str):
    """Print a pipeline step header with routing info."""
    short = model_short_name(model)
    print(f"\n{'─'*60}")
    print(f"  {num}  {title}")
    print(f"     Task: {task_type}  →  {short}")
    print(f"{'─'*60}")


# ---------------------------------------------------------------------------
# Pipeline Steps
# ---------------------------------------------------------------------------


def write_story(client: OpenAI, theme: str, model: str) -> tuple[str, str]:
    """Step 1: Draft a 4-page children's story. Returns (story, actual_model)."""
    step_header("1", "STORY WRITER", model, "creative")
    print(f"  Theme: {theme}")

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": textwrap.dedent("""\
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
                """),
            },
            {
                "role": "user",
                "content": f"Write a bedtime story about: {theme}",
            },
        ],
        temperature=0.9,
        max_tokens=800,
    )
    actual = resp.model or model_short_name(model)
    story = strip_thinking(resp.choices[0].message.content or "")
    print(f"  Routed to: {actual}")
    print(f"\n{story}")
    return story, actual


def edit_story(client: OpenAI, draft: str, model: str) -> tuple[str, str]:
    """Step 2: Polish the story. Returns (edited_story, actual_model)."""
    step_header("2", "STORY EDITOR", model, "editing")

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": textwrap.dedent("""\
                    You are a children's book editor. Polish the following story
                    draft. Improve the prose rhythm, make descriptions more
                    vivid, and ensure the pacing feels right for a bedtime story.

                    Rules:
                    - Keep the exact same 4-page structure (PAGE 1: ... PAGE 4:)
                    - Keep each page to 2-3 sentences
                    - Keep language simple enough for ages 3-6
                    - Preserve the original story and moral
                    - Only output the polished story, nothing else
                """),
            },
            {
                "role": "user",
                "content": draft,
            },
        ],
        temperature=0.5,
        max_tokens=800,
    )
    actual = resp.model or model_short_name(model)
    edited = strip_thinking(resp.choices[0].message.content or "")
    print(f"  Routed to: {actual}")
    print(f"\n{edited}")
    return edited, actual


def craft_image_prompts(client: OpenAI, story: str, model: str) -> tuple[list[str], str]:
    """Step 3: Convert each page into image prompts. Returns (prompts, actual_model)."""
    step_header("3", "PROMPT CRAFTER", model, "structured")

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": textwrap.dedent("""\
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
                """),
            },
            {
                "role": "user",
                "content": story,
            },
        ],
        temperature=0.4,
        max_tokens=2000,
    )
    actual = resp.model or model_short_name(model)
    raw = strip_thinking(resp.choices[0].message.content or "")

    # Extract JSON array
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1:
        raw = raw[start : end + 1]

    prompts = json.loads(raw)
    print(f"  Routed to: {actual}")
    for i, p in enumerate(prompts):
        print(f"\n  Page {i+1}: {p[:80]}...")
    return prompts, actual


# ---------------------------------------------------------------------------
# Image Generation (direct DO async-invoke API)
# ---------------------------------------------------------------------------


def _do_async_invoke(api_key: str, model_id: str, prompt: str) -> str | None:
    """Call DO async-invoke API and poll until image is ready."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    submit_data = json.dumps({
        "model_id": model_id,
        "input": {"prompt": prompt},
    }).encode()
    req = urllib.request.Request(
        f"{DO_INFERENCE_URL.rstrip('/v1')}/v1/async-invoke",
        data=submit_data, headers=headers, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    request_id = result.get("request_id") or result.get("id")
    if not request_id:
        return None

    status_url = f"{DO_INFERENCE_URL.rstrip('/v1')}/v1/async-invoke/{request_id}/status"
    for _ in range(45):
        time.sleep(2)
        req = urllib.request.Request(status_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        if result.get("status") == "COMPLETED":
            output = result.get("output", {})
            images_list = output.get("images", [])
            if images_list:
                return images_list[0].get("url")
            return None
        if result.get("status") in ("FAILED", "CANCELLED"):
            return None
    return None


def generate_illustrations(api_key: str, prompts: list[str]) -> list[str]:
    """Step 4: Generate illustrations using DO async-invoke API."""
    print(f"\n{'─'*60}")
    print(f"  4  ILLUSTRATOR")
    print(f"     Task: image_gen  →  {IMAGE_MODEL}")
    print(f"{'─'*60}")

    images = []
    for i, prompt in enumerate(prompts):
        print(f"  Generating page {i+1}/{len(prompts)}...", end=" ", flush=True)
        try:
            image_url = _do_async_invoke(api_key, IMAGE_MODEL, prompt)
            if not image_url:
                print("failed (no image URL)")
                images.append("")
                continue
            req = urllib.request.Request(image_url)
            with urllib.request.urlopen(req, timeout=30) as response:
                image_data = base64.b64encode(response.read()).decode()
            images.append(f"data:image/png;base64,{image_data}")
            print("done")
        except Exception as e:
            print(f"failed ({e})")
            images.append("")
    return images


# ---------------------------------------------------------------------------
# HTML Assembly
# ---------------------------------------------------------------------------


def parse_pages(story: str) -> list[str]:
    """Split story text into individual page texts."""
    pages = []
    current = []
    for line in story.split("\n"):
        if line.strip().upper().startswith("PAGE") and ":" in line:
            if current:
                pages.append("\n".join(current).strip())
                current = []
            after_colon = line.split(":", 1)[1].strip()
            if after_colon:
                current.append(after_colon)
        else:
            if line.strip():
                current.append(line.strip())
    if current:
        pages.append("\n".join(current).strip())
    while len(pages) < NUM_PAGES:
        pages.append("...")
    return pages[:NUM_PAGES]


def assemble_html(
    theme: str, story: str, images: list[str],
    model_log: dict[str, str], mode: str, output_path: Path,
) -> Path:
    """Step 5: Combine story and images into an HTML storybook."""
    print(f"\n{'─'*60}")
    print(f"  5  ASSEMBLER")
    print(f"     Output: {output_path}")
    print(f"{'─'*60}")

    pages = parse_pages(story)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    page_gradients = [
        "linear-gradient(135deg, #2d1b69 0%, #5b2c8e 50%, #8e44ad 100%)",
        "linear-gradient(135deg, #0c3547 0%, #11998e 50%, #38ef7d 100%)",
        "linear-gradient(135deg, #2c3e50 0%, #4a69bd 50%, #6a89cc 100%)",
        "linear-gradient(135deg, #1a1a2e 0%, #e2703a 50%, #eec643 100%)",
    ]
    page_emojis = ["🏠", "✨", "🌙", "💤"]

    pages_html = ""
    for i, (text, img) in enumerate(zip(pages, images)):
        if img:
            img_tag = f'<img src="{img}" alt="Page {i+1} illustration">'
        else:
            grad = page_gradients[i % len(page_gradients)]
            emoji = page_emojis[i % len(page_emojis)]
            img_tag = (
                f'<div class="placeholder" style="background: {grad};">'
                f'<span style="font-size:4rem;">{emoji}</span></div>'
            )
        pages_html += f"""
        <div class="page">
            <div class="page-number">— {i+1} —</div>
            {img_tag}
            <div class="text">{text}</div>
        </div>
        """

    # Dynamic pipeline footer from actual model_log
    pipeline_lines = []
    for step_name, actual_model in model_log.items():
        pipeline_lines.append(f"<p>{step_name}: <code>{actual_model}</code></p>")
    pipeline_html = "\n  ".join(pipeline_lines)

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bedtime Story: {theme}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600&family=Caveat:wght@500&display=swap');

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Quicksand', sans-serif;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    min-height: 100vh;
    color: #f0e6d3;
  }}

  .cover {{
    text-align: center;
    padding: 80px 20px 60px;
    max-width: 700px;
    margin: 0 auto;
  }}

  .cover h1 {{
    font-family: 'Caveat', cursive;
    font-size: 3rem;
    color: #ffd700;
    margin-bottom: 10px;
    text-shadow: 0 2px 10px rgba(255, 215, 0, 0.3);
  }}

  .cover .subtitle {{
    font-size: 1.1rem;
    opacity: 0.7;
    margin-bottom: 8px;
  }}

  .cover .meta {{
    font-size: 0.85rem;
    opacity: 0.5;
  }}

  .page {{
    max-width: 700px;
    margin: 40px auto;
    padding: 0 20px;
    text-align: center;
  }}

  .page img {{
    width: 100%;
    max-width: 600px;
    border-radius: 16px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.4);
    margin-bottom: 24px;
  }}

  .page .placeholder {{
    width: 100%;
    max-width: 600px;
    height: 400px;
    margin: 0 auto 24px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0.6;
  }}

  .page .text {{
    font-size: 1.25rem;
    line-height: 1.8;
    max-width: 550px;
    margin: 0 auto;
  }}

  .page-number {{
    font-family: 'Caveat', cursive;
    font-size: 1.5rem;
    color: #ffd700;
    margin-bottom: 20px;
    opacity: 0.8;
  }}

  .footer {{
    text-align: center;
    padding: 60px 20px 40px;
    opacity: 0.5;
    font-size: 0.8rem;
  }}

  .footer .stars {{ font-size: 1.5rem; margin-bottom: 10px; }}

  .pipeline {{
    max-width: 600px;
    margin: 0 auto;
    padding: 40px 20px;
    font-size: 0.75rem;
    opacity: 0.4;
    text-align: left;
  }}

  .pipeline h3 {{ margin-bottom: 8px; font-size: 0.85rem; }}
  .pipeline code {{ color: #7ec8e3; }}
</style>
</head>
<body>

<div class="cover">
  <h1>Bedtime Story</h1>
  <div class="subtitle">{theme}</div>
  <div class="meta">Generated {timestamp} | Routing: {mode}</div>
</div>

{pages_html}

<div class="footer">
  <div class="stars">&#10022; &#10022; &#10022;</div>
  <p>The End</p>
  <p>Sweet dreams.</p>
</div>

<div class="pipeline">
  <h3>Powered by Plano + DigitalOcean Serverless Inference</h3>
  {pipeline_html}
  <p>Gateway: <code>Plano</code> &rarr; DigitalOcean Serverless Inference</p>
  <p>Routing mode: <code>{mode}</code></p>
</div>

</body>
</html>"""

    output_path.write_text(html)
    print(f"  Storybook saved to: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Generate a children's bedtime storybook using AI"
    )
    parser.add_argument(
        "theme", nargs="?", default=None,
        help="Story theme (e.g., 'a brave little robot who learns to dream')",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output HTML file path",
    )
    parser.add_argument(
        "--no-images", action="store_true",
        help="Skip image generation (text-only storybook)",
    )
    routing = parser.add_mutually_exclusive_group()
    routing.add_argument(
        "--premium", action="store_true",
        help="Use Claude Opus 4.6 for all text steps (highest quality)",
    )
    routing.add_argument(
        "--economy", action="store_true",
        help="Use Llama 3.3 70B for all text steps (cheapest)",
    )
    args = parser.parse_args()

    if args.premium:
        mode = "premium"
    elif args.economy:
        mode = "economy"
    else:
        mode = "task-aware"

    theme = args.theme or random.choice(RANDOM_THEMES)
    output = args.output or f"storybook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    output_path = Path(output)

    print("=" * 60)
    print("  AI Storybook Generator")
    print("  Plano + DigitalOcean Serverless Inference")
    print(f"  Routing: {mode}")
    print("=" * 60)

    plano = get_plano_client()
    model_log = {}

    # Step 1: Write
    writer_model = resolve_model("creative", mode)
    draft, actual = write_story(plano, theme, writer_model)
    model_log["Story Writer"] = actual

    # Step 2: Edit
    editor_model = resolve_model("editing", mode)
    polished, actual = edit_story(plano, draft, editor_model)
    model_log["Story Editor"] = actual

    # Step 3: Image prompts
    crafter_model = resolve_model("structured", mode)
    image_prompts, actual = craft_image_prompts(plano, polished, crafter_model)
    model_log["Prompt Crafter"] = actual

    # Step 4: Generate illustrations
    if args.no_images:
        print(f"\n{'─'*60}")
        print(f"  4  ILLUSTRATOR — Skipped (--no-images)")
        print(f"{'─'*60}")
        images = [""] * NUM_PAGES
    else:
        api_key = get_do_api_key()
        images = generate_illustrations(api_key, image_prompts)
    model_log["Illustrator"] = IMAGE_MODEL

    # Step 5: Assemble
    assemble_html(theme, polished, images, model_log, mode, output_path)

    # Summary
    print(f"\n{'='*60}")
    print(f"  Done! Open {output_path} in your browser.")
    print(f"{'─'*60}")
    print(f"  Routing mode: {mode}")
    for step_name, actual_model in model_log.items():
        print(f"    {step_name}: {actual_model}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
