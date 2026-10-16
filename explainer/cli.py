"""Command line entry point: `explainer <command>`. Run `explainer -h` for help."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

from .structures import STRUCTURES, estimated_seconds, validate
from .topic import TopicError, load_topic

ROOT = Path(__file__).resolve().parent.parent
TOPICS = ROOT / "topics"
TEMPLATES = ROOT / "templates"
OUTPUT = ROOT / "output"


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Read KEY=value lines from .env into the environment (without overriding)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def resolve_topic(name: str) -> Path:
    path = Path(name)
    if path.exists():
        return path
    candidate = TOPICS / f"{name.removesuffix('.yaml')}.yaml"
    if candidate.exists():
        return candidate
    sys.exit(f"no topic '{name}' (looked for {path} and {candidate})")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def cmd_list(args) -> None:
    for path in sorted(TOPICS.glob("*.yaml")):
        try:
            topic = load_topic(path)
            problems = validate(topic)
            status = "ok" if not problems else f"{len(problems)} problem(s)"
            print(f"{path.stem:40} {topic.kind:14} ~{estimated_seconds(topic):4.0f}s  {status}")
        except TopicError as e:
            print(f"{path.stem:40} invalid: {e}")


def cmd_new(args) -> None:
    dest = TOPICS / f"{slugify(args.slug)}.yaml"
    if dest.exists():
        sys.exit(f"{dest} already exists")
    shutil.copy(TEMPLATES / f"{args.kind}.yaml", dest)
    print(f"created {dest.relative_to(ROOT)}; fill it in, then run: explainer validate {dest.stem}")


def cmd_draft(args) -> None:
    from .drafter import draft_topic

    slug = slugify(args.slug or args.idea)
    dest = TOPICS / f"{slug}.yaml"
    if dest.exists() and not args.force:
        sys.exit(f"{dest} already exists (use --force to overwrite)")
    example = TOPICS / "agentic-wholesale-order-agent.yaml"
    print(f"drafting '{args.idea}' as a {args.kind} topic with Claude...")
    dest.write_text(draft_topic(args.idea, args.kind, TEMPLATES / f"{args.kind}.yaml", example))
    print(f"wrote {dest.relative_to(ROOT)}")
    _report(dest)


def _report(path: Path) -> bool:
    topic = load_topic(path)
    problems = validate(topic)
    print(f"{topic.title}: {topic.word_count} words, ~{estimated_seconds(topic):.0f}s")
    for p in problems:
        print(f"  - {p}")
    if not problems:
        print("  looks good")
    return not problems


def cmd_validate(args) -> None:
    ok = _report(resolve_topic(args.topic))
    sys.exit(0 if ok else 1)


def cmd_render(args) -> None:
    from .pipeline import render_topic
    from .render import ManimRenderer
    from .tts import make_tts

    path = resolve_topic(args.topic)
    topic = load_topic(path)
    problems = validate(topic)
    if problems and not args.force:
        print("fix these first (or pass --force):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    if args.only:
        topic = topic.only(set(args.only.split(",")))
        if not topic.sections:
            sys.exit(f"no sections with role(s) {args.only}")

    voice = topic.voice if args.tts == "elevenlabs" else {}
    tts = make_tts(args.tts, OUTPUT / ".tts-cache", **voice)
    out_dir = OUTPUT / topic.slug
    result = render_topic(topic, tts, ManimRenderer(args.quality), out_dir, captions=not args.no_captions)
    print(f"done: {result.video.relative_to(ROOT)} ({result.seconds:.0f}s)")


def main(argv: list[str] | None = None) -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="explainer", description="Make 3Blue1Brown-style explainer videos from topic files.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list topics and whether they are ready").set_defaults(fn=cmd_list)

    p = sub.add_parser("new", help="start a topic from a blank template")
    p.add_argument("slug", help="file name, e.g. rate-limiter")
    p.add_argument("--kind", choices=sorted(STRUCTURES), required=True)
    p.set_defaults(fn=cmd_new)

    p = sub.add_parser("draft", help="have Claude write a topic from a one-line idea")
    p.add_argument("idea", help='e.g. "Design a distributed rate limiter"')
    p.add_argument("--kind", choices=sorted(STRUCTURES), required=True)
    p.add_argument("--slug", help="file name (defaults to the idea)")
    p.add_argument("--force", action="store_true", help="overwrite an existing topic")
    p.set_defaults(fn=cmd_draft)

    p = sub.add_parser("validate", help="check a topic's structure and length")
    p.add_argument("topic", help="topic name in topics/ or a path")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("render", help="make the video")
    p.add_argument("topic", help="topic name in topics/ or a path")
    p.add_argument("--tts", choices=["silent", "elevenlabs"], default="elevenlabs",
                   help="voice provider; 'silent' is free and offline, for previewing")
    p.add_argument("--quality", choices=["low", "medium", "high", "4k"], default="medium")
    p.add_argument("--only", help="comma-separated roles to render, e.g. high_level,issues")
    p.add_argument("--no-captions", action="store_true")
    p.add_argument("--force", action="store_true", help="render even if validation fails")
    p.set_defaults(fn=cmd_render)

    args = parser.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
