"""
AI Storybook Generator — Plano + DigitalOcean Demo

Generates a children's bedtime storybook with illustrations using
multiple AI models orchestrated through Plano, all powered by
DigitalOcean Serverless Inference. No OpenAI key needed.

Pipeline:
  1. Story Writer   (llama3.3-70b)    → Draft a 4-page story
  2. Story Editor   (deepseek-r1-70b) → Polish prose and pacing
  3. Prompt Crafter (qwen3-32b)       → Convert pages to image prompts
  4. Illustrator    (flux/schnell)     → Generate illustrations via DO
  5. Assembler      (Python)          → Combine into HTML storybook

Usage:
  export DO_MODEL_ACCESS_KEY="dop_v1_..."
  planoai up config.yaml          # in another terminal
  uv run storybook.py "a brave little robot who learns to dream"
  uv run storybook.py             # uses a random theme
"""

import argparse
import base64
import json
import os
import random
import sys
import textwrap
import urllib.request
from datetime import datetime
from pathlib import Path

from openai import OpenAI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PLANO_URL = "http://localhost:12000/v1"
DO_INFERENCE_URL = "https://inference.do-ai.run/v1"

MODEL_WRITER = "digitalocean/llama3.3-70b-instruct"
MODEL_EDITOR = "digitalocean/deepseek-r1-distill-llama-70b"
MODEL_CRAFTER = "digitalocean/alibaba-qwen3-32b"
IMAGE_MODEL = "fal-ai/flux/schnell"

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
    """Client that routes through Plano (text models)."""
    return OpenAI(base_url=PLANO_URL, api_key="unused")


def get_do_image_client() -> OpenAI:
    """Client that talks directly to DO Inference (image generation)."""
    key = os.environ.get("DO_MODEL_ACCESS_KEY", "")
    if not key:
        print("ERROR: Set DO_MODEL_ACCESS_KEY environment variable.")
        sys.exit(1)
    return OpenAI(base_url=DO_INFERENCE_URL, api_key=key)


def step(icon: str, title: str, detail: str = ""):
    """Print a pipeline step header."""
    print(f"\n{'─'*60}")
    print(f"  {icon}  {title}")
    if detail:
        print(f"     {detail}")
    print(f"{'─'*60}")


# ---------------------------------------------------------------------------
# Pipeline Steps
# ---------------------------------------------------------------------------


def write_story(client: OpenAI, theme: str) -> str:
    """Step 1: Draft a 4-page children's story."""
    step("1", "STORY WRITER", f"Model: {MODEL_WRITER}")
    print(f"  Theme: {theme}")

    resp = client.chat.completions.create(
        model=MODEL_WRITER,
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
    story = resp.choices[0].message.content
    print(f"\n{story}")
    return story


def edit_story(client: OpenAI, draft: str) -> str:
    """Step 2: Polish the story for rhythm and clarity."""
    step("2", "STORY EDITOR", f"Model: {MODEL_EDITOR}")

    resp = client.chat.completions.create(
        model=MODEL_EDITOR,
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
    edited = resp.choices[0].message.content
    print(f"\n{edited}")
    return edited


def craft_image_prompts(client: OpenAI, story: str) -> list[str]:
    """Step 3: Convert each page into an image generation prompt."""
    step("3", "PROMPT CRAFTER", f"Model: {MODEL_CRAFTER}")

    resp = client.chat.completions.create(
        model=MODEL_CRAFTER,
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
                """),
            },
            {
                "role": "user",
                "content": story,
            },
        ],
        temperature=0.4,
        max_tokens=600,
    )

    raw = resp.choices[0].message.content.strip()
    # Extract JSON array from response (handle markdown code blocks)
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    prompts = json.loads(raw)
    for i, p in enumerate(prompts):
        print(f"\n  Page {i+1}: {p[:80]}...")
    return prompts


def generate_illustrations(
    image_client: OpenAI, prompts: list[str]
) -> list[str]:
    """Step 4: Generate illustrations using DO image model."""
    step("4", "ILLUSTRATOR", f"Model: {IMAGE_MODEL}")

    images = []
    for i, prompt in enumerate(prompts):
        print(f"  Generating page {i+1}/{len(prompts)}...", end=" ", flush=True)
        try:
            resp = image_client.images.generate(
                model=IMAGE_MODEL,
                prompt=prompt,
                n=1,
                size="1024x1024",
            )
            image_url = resp.data[0].url
            # Download image and convert to base64 for embedding in HTML
            req = urllib.request.Request(image_url)
            with urllib.request.urlopen(req, timeout=30) as response:
                image_data = base64.b64encode(response.read()).decode()
            images.append(f"data:image/png;base64,{image_data}")
            print("done")
        except Exception as e:
            print(f"failed ({e})")
            # Use a placeholder gradient as fallback
            images.append("")
    return images


def parse_pages(story: str) -> list[str]:
    """Split story text into individual page texts."""
    pages = []
    current = []
    for line in story.split("\n"):
        if line.strip().upper().startswith("PAGE") and ":" in line:
            if current:
                pages.append("\n".join(current).strip())
                current = []
            # Skip the "PAGE N:" header itself
            after_colon = line.split(":", 1)[1].strip()
            if after_colon:
                current.append(after_colon)
        else:
            if line.strip():
                current.append(line.strip())
    if current:
        pages.append("\n".join(current).strip())

    # Ensure we have exactly NUM_PAGES
    while len(pages) < NUM_PAGES:
        pages.append("...")
    return pages[:NUM_PAGES]


def assemble_html(
    theme: str, story: str, images: list[str], output_path: Path
) -> Path:
    """Step 5: Combine story and images into an HTML storybook."""
    step("5", "ASSEMBLER", f"Output: {output_path}")

    pages = parse_pages(story)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    pages_html = ""
    for i, (text, img) in enumerate(zip(pages, images)):
        img_tag = (
            f'<img src="{img}" alt="Page {i+1} illustration">'
            if img
            else f'<div class="placeholder">Illustration {i+1}</div>'
        )
        pages_html += f"""
        <div class="page">
            <div class="page-number">— {i+1} —</div>
            {img_tag}
            <div class="text">{text}</div>
        </div>
        """

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
    background: linear-gradient(135deg, #2d1b69, #11998e);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
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
  <div class="meta">Generated {timestamp}</div>
</div>

{pages_html}

<div class="footer">
  <div class="stars">&#10022; &#10022; &#10022;</div>
  <p>The End</p>
  <p>Sweet dreams.</p>
</div>

<div class="pipeline">
  <h3>Powered by Plano + DigitalOcean</h3>
  <p>Story Writer: <code>llama3.3-70b-instruct</code></p>
  <p>Story Editor: <code>deepseek-r1-distill-llama-70b</code></p>
  <p>Prompt Crafter: <code>alibaba-qwen3-32b</code></p>
  <p>Illustrator: <code>fal-ai/flux/schnell</code></p>
  <p>Gateway: <code>Plano v0.3.0</code> &rarr; DigitalOcean Serverless Inference</p>
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
        "theme",
        nargs="?",
        default=None,
        help="Story theme (e.g., 'a brave little robot who learns to dream')",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output HTML file path (default: storybook_<timestamp>.html)",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip image generation (text-only storybook)",
    )
    args = parser.parse_args()

    theme = args.theme or random.choice(RANDOM_THEMES)
    output = args.output or f"storybook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    output_path = Path(output)

    print("=" * 60)
    print("  AI Storybook Generator")
    print("  Plano + DigitalOcean Serverless Inference")
    print("=" * 60)

    plano = get_plano_client()

    # Step 1: Write
    draft = write_story(plano, theme)

    # Step 2: Edit
    polished = edit_story(plano, draft)

    # Step 3: Image prompts
    image_prompts = craft_image_prompts(plano, polished)

    # Step 4: Generate illustrations
    if args.no_images:
        step("4", "ILLUSTRATOR", "Skipped (--no-images)")
        images = [""] * NUM_PAGES
    else:
        image_client = get_do_image_client()
        images = generate_illustrations(image_client, image_prompts)

    # Step 5: Assemble
    assemble_html(theme, polished, images, output_path)

    print(f"\n{'='*60}")
    print(f"  Done! Open {output_path} in your browser.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
