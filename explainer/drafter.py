"""Optional: turn a one-line idea into a full topic YAML with Claude.

Needs `pip install anthropic` and ANTHROPIC_API_KEY. You can always skip this
and write or edit the YAML by hand.
"""

from __future__ import annotations

from pathlib import Path

from .structures import MAX_SECONDS, STRUCTURES, WORDS_PER_MINUTE
from .visuals import REGISTRY

MODEL = "claude-opus-5-5"


def _prompt(idea: str, kind: str, template: str, example: str) -> str:
    slots = "\n".join(
        f"- {s.role} ({s.min}-{s.max} sections): {s.hint}" for s in STRUCTURES[kind]
    )
    words = MAX_SECONDS * WORDS_PER_MINUTE // 60
    return f"""Write a topic file for a 3Blue1Brown-style teaching video.

Idea: {idea}
Kind: {kind}

Sections, in this order:
{slots}

Rules:
- Total narration must be under {words - 50} words (the video must stay under 5 minutes).
- Narration is spoken aloud: short sentences, no markdown, no symbols, spell out numbers when it helps.
- Each section has role, heading, narration, visual. Visual types available: {", ".join(sorted(REGISTRY))}.
- Give each revealed item a `cue`: a short phrase copied exactly from that section's narration,
  so the picture appears as the narrator says it.
- Issues: at most three, each solved by its own deep_dive section.
- For agentic topics, follow Hamel Husain's evals FAQ: start from error analysis on real traces
  (open coding then axial coding), build synthetic inputs from dimensions and tuples, prefer
  binary pass/fail judgments, use code assertions for objective checks, and validate any
  LLM judge against human labels (true positive and true negative rates).

Template for this kind (shows the expected keys):
```yaml
{template}
```

A complete example of a finished topic (a different kind is fine, copy the style):
```yaml
{example}
```

Reply with only the YAML, no code fences and no commentary."""


def draft_topic(idea: str, kind: str, template_path: Path, example_path: Path) -> str:
    import anthropic  # imported here so the rest of the tool works without it

    client = anthropic.Anthropic()
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "high"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{
            "role": "user",
            "content": _prompt(idea, kind, template_path.read_text(), example_path.read_text()),
        }],
    ) as stream:
        message = stream.get_final_message()
    if message.stop_reason == "refusal":
        raise RuntimeError("Claude declined to draft this topic; try rephrasing the idea")
    text = "".join(b.text for b in message.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return text.strip() + "\n"
