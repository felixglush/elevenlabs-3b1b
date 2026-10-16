# explainer-videos

A command line tool that turns a topic file into a 3Blue1Brown-style teaching
video: animated diagrams drawn with [Manim](https://www.manim.community/), an
ElevenLabs voice, and captions burned in. Videos stay under 5 minutes.

Three kinds of topic are supported, each with an enforced lesson structure:

| kind | structure |
|---|---|
| `system_design` | hook, functional reqs, non-functional reqs, high-level design, up to 3 issues, a deep dive per issue, extensions to study |
| `agentic` | the same, plus how to build an eval dataset and how to evaluate the agent ([Hamel's evals FAQ](https://hamel.dev/blog/posts/evals-faq/)) |
| `neetcode` | problem, brute force (optional), key insight, walkthrough, complexity, follow-up problems |

## Setup (once)

You need Python 3.10+, ffmpeg, and the Cairo/Pango libraries Manim draws with.

```bash
# macOS
brew install ffmpeg pango pkg-config
# Ubuntu
sudo apt install ffmpeg libpango1.0-dev pkg-config

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[draft,dev]"

cp .env.example .env   # then paste your ELEVENLABS_API_KEY (and ANTHROPIC_API_KEY for `draft`)
```

## Everyday use

```bash
explainer list                                   # every topic, its length, and whether it's valid
explainer validate agentic-wholesale-order-agent # check structure and the 5-minute budget
explainer render agentic-wholesale-order-agent --tts silent --quality low   # free, fast preview
explainer render agentic-wholesale-order-agent                              # real voice, 720p
```

The video lands in `output/<topic>/<topic>.mp4`, with the captions also saved as
an `.srt` next to it.

Tips while iterating:

- `--tts silent` skips ElevenLabs entirely. Timings are estimated, so you can
  fix visuals for free and only pay for the voice at the end.
- `--only high_level,issues` renders just those sections.
- Voice clips are cached in `output/.tts-cache`, keyed by the exact narration
  text. Changing a visual never re-buys audio; changing a sentence re-buys only
  that section.
- `--quality low|medium|high|4k` (low renders in seconds).

## Adding a topic

1. Drop the idea in [`ideas.md`](ideas.md).
2. Either let Claude draft it, or start from a template:
   ```bash
   explainer draft "Design a distributed rate limiter" --kind system_design
   explainer new rate-limiter --kind system_design
   ```
3. Edit `topics/<slug>.yaml`, run `explainer validate <slug>`, then render.

A section looks like this:

```yaml
- role: high_level              # which part of the lesson (validated per kind)
  heading: High-level design    # shown top-left
  narration: >                  # exactly what the voice says
    A webhook receives the message and hands it to the agent.
  visual:
    type: diagram
    nodes:
      - {id: hook, label: Webhook, col: 0, row: 0, cue: webhook}
      - {id: agent, label: LLM agent, col: 1, row: 0, tone: agent, cue: the agent}
    edges:
      - [hook, agent]
```

**Cues** are what make it feel like 3Blue1Brown: `cue` is a phrase copied from
the narration, and the item appears the moment the voice says it. Items without
a cue are spread evenly. The render prints a warning if a cue isn't found.

### Visual types

| type | use it for | keys |
|---|---|---|
| `title` | the hook | `title`, `subtitle`, `subtitle_cue` |
| `bullets` | requirements, extensions | `items: [text or {text, cue, tone}]` |
| `cards` | issues, metrics, trade-offs | `items: [{title, body, cue, tone}]`, `numbered`, `per_row`, `tone` |
| `diagram` | architecture | `nodes: [{id, label, col, row, shape: box/db/queue, tone, cue}]`, `edges: [[a, b] or {from, to, label, bend, cue}]`, `highlight`, `problem`, `note` (+ `*_cue`) |
| `table` | hash maps, buckets, comparisons | `columns`, `rows: [[...] or {cells, cue}]`, `widths` |
| `array` | algorithm walkthroughs | `values`, `label`, `steps: [{highlight: [i], note, tone, cue}]` |

Tones: `neutral` (blue), `danger` (red), `good` (green), `accent` (yellow),
`data` (teal), `agent` (purple), `extra` (orange), or any hex color.

## How it works

```
topics/x.yaml ──load──▶ Topic ──validate──▶ (structure + 5 min budget)
                          │
          for each section│
                          ▼
                  TTS provider ──▶ audio + word timings      explainer/tts.py
                          │
                          ▼
     Manim scene: visual beats scheduled on word cues        explainer/render.py, visuals.py, timing.py
                          │
                          ▼
   captions from word timings ──▶ .srt                       explainer/captions.py
                          │
                          ▼
   ffmpeg: pad audio to each section, mux, burn captions     explainer/compose.py
```

`explainer/pipeline.py` wires these together, and each stage is passed in rather
than created inside it, so they can be swapped independently.

### Where to make common changes

| I want to... | change |
|---|---|
| restyle colors, fonts, sizes | `explainer/style.py` |
| change the caption look | `CAPTION_STYLE` in `explainer/compose.py` |
| add a new visual (e.g. a tree or graph) | write a function in `explainer/visuals.py` and decorate it with `@visual("tree")` |
| add a new topic kind (e.g. behavioral) | add an entry to `STRUCTURES` in `explainer/structures.py` and a template in `templates/` |
| use a different voice | `voice:` block at the top of a topic (`voice_id`, `speed`, `stability`...) |
| add a different TTS provider | a class with `name` and `synthesize(text, out_stem) -> Speech`, registered in `PROVIDERS` in `explainer/tts.py` |

## Tests

```bash
pytest
```

The tests cover the logic (validation, cue matching, scheduling, captions,
ElevenLabs alignment parsing) and check every topic and template is valid.
They don't render video.

## Credits

The visual conventions (semantic color palette, dark background, one idea per
beat, text width safety) borrow from
[AmitSubhash/3brown1blue](https://github.com/AmitSubhash/3brown1blue) (MIT).
