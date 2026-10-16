"""Topic files: the YAML you write, loaded into small immutable objects.

A topic is a list of sections. Each section has a `role` (which part of the
lesson it is, e.g. "functional" or "deep_dive"), the words the narrator says,
and a `visual` telling the renderer what to draw while those words play.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Section:
    role: str
    heading: str
    narration: str
    visual: dict[str, Any] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len(self.narration.split())


@dataclass(frozen=True)
class Topic:
    slug: str
    kind: str
    title: str
    sections: tuple[Section, ...]
    voice: dict[str, Any] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return sum(s.word_count for s in self.sections)

    def only(self, roles: set[str]) -> "Topic":
        """A copy keeping just the given roles: handy for previewing one part."""
        kept = tuple(s for s in self.sections if s.role in roles)
        return Topic(self.slug, self.kind, self.title, kept, self.voice)


class TopicError(ValueError):
    pass


def load_topic(path: str | Path) -> Topic:
    path = Path(path)
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise TopicError(f"{path}: expected a mapping at the top level")
    for key in ("kind", "title", "sections"):
        if key not in data:
            raise TopicError(f"{path}: missing required key '{key}'")

    sections = []
    for i, raw in enumerate(data["sections"]):
        if "role" not in raw or "narration" not in raw:
            raise TopicError(f"{path}: section {i} needs 'role' and 'narration'")
        sections.append(
            Section(
                role=raw["role"],
                heading=raw.get("heading", ""),
                narration=" ".join(str(raw["narration"]).split()),
                visual=raw.get("visual") or {"type": "bullets", "items": []},
            )
        )
    return Topic(
        slug=data.get("slug", path.stem),
        kind=data["kind"],
        title=data["title"],
        sections=tuple(sections),
        voice=data.get("voice") or {},
    )
