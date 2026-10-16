"""Visual types a section can use, each turning a YAML spec into timed "beats".

A beat is one reveal (e.g. "draw the cache box"). It may carry a `cue`: a word
or phrase from the narration. The scene plays the beat when the narrator says
that phrase, so pictures appear exactly when they are talked about.

To add a visual type, write `def my_type(spec) -> list[Beat]` and decorate it
with `@visual("my_type")`. The YAML then uses `visual: {type: my_type, ...}`.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from typing import Any, Callable

from manim import (
    DOWN, LEFT, RIGHT, UP,
    PI, Animation, Arrow, CurvedArrow, Create, Dot, Ellipse, FadeIn, FadeOut, Indicate, Line,
    Mobject, Rectangle, RoundedRectangle, SurroundingRectangle, Text, VGroup, Write,
    LaggedStart, Cross, normalize, rotate_vector,
)

from . import style as S

Spec = dict[str, Any]


@dataclass
class Beat:
    make: Callable[[], list[Animation]]  # built lazily so it sees the latest state
    cue: str | None = None
    run_time: float = S.BEAT_SECONDS


VisualBuilder = Callable[[Spec], list[Beat]]
REGISTRY: dict[str, VisualBuilder] = {}


def visual(name: str):
    def register(fn: VisualBuilder) -> VisualBuilder:
        REGISTRY[name] = fn
        return fn
    return register


def build_beats(spec: Spec) -> list[Beat]:
    kind = spec.get("type", "bullets")
    if kind not in REGISTRY:
        raise ValueError(f"unknown visual type '{kind}', expected one of {sorted(REGISTRY)}")
    return REGISTRY[kind](spec)


# ── small helpers ────────────────────────────────────────────────────────────

def text(s: str, size: int = S.BODY_SIZE, color=S.TEXT, weight: str = "NORMAL", width: float | None = None) -> Text:
    t = Text(str(s), font=S.FONT, font_size=size, color=color, weight=weight)
    if width and t.width > width:
        t.scale_to_fit_width(width)
    return t


def wrapped(s: str, chars: int, size: int, color=S.TEXT, weight: str = "NORMAL") -> VGroup:
    lines = textwrap.wrap(str(s), chars) or [""]
    return VGroup(*[text(line, size, color, weight) for line in lines]).arrange(DOWN, buff=0.12, aligned_edge=LEFT)


def fit_content(group: Mobject) -> Mobject:
    """Scale down (never up) to fit the content box, then center it there."""
    height = S.CONTENT_TOP - S.CONTENT_BOTTOM
    if group.width > S.CONTENT_WIDTH:
        group.scale_to_fit_width(S.CONTENT_WIDTH)
    if group.height > height:
        group.scale_to_fit_height(height)
    group.move_to(UP * (S.CONTENT_TOP + S.CONTENT_BOTTOM) / 2)
    return group


def item_fields(item: Any) -> dict:
    return item if isinstance(item, dict) else {"text": str(item)}


def section_heading(heading: str, role: str) -> VGroup:
    color = S.ROLE_COLORS.get(role, S.PRIMARY)
    label = text(heading, S.HEADING_SIZE, color, weight="BOLD")
    rule = Line(LEFT, RIGHT, color=color, stroke_width=2).set_width(label.width)
    group = VGroup(label, rule.next_to(label, DOWN, buff=0.08)).to_corner(UP + LEFT, buff=0.45)
    return group


# ── visual types ─────────────────────────────────────────────────────────────

@visual("title")
def title_card(spec: Spec) -> list[Beat]:
    """Big centered title with an optional subtitle. Good for the hook."""
    title = text(spec.get("title", ""), S.TITLE_SIZE, S.ACCENT, weight="BOLD", width=S.CONTENT_WIDTH)
    parts = [title]
    if spec.get("subtitle"):
        parts.append(wrapped(spec["subtitle"], 48, S.BODY_SIZE, S.MUTED))
    group = fit_content(VGroup(*parts).arrange(DOWN, buff=0.5))
    beats = [Beat(lambda: [Write(title)], run_time=1.2)]
    if len(parts) > 1:
        beats.append(Beat(lambda: [FadeIn(parts[1], shift=UP * 0.2)], cue=spec.get("subtitle_cue")))
    return beats


@visual("bullets")
def bullets(spec: Spec) -> list[Beat]:
    """A list revealed one line at a time. Items: text or {text, cue, tone}."""
    rows = []
    items = [item_fields(i) for i in spec.get("items", [])]
    for item in items:
        color = S.tone(item.get("tone"), S.PRIMARY)
        dot = Dot(color=color, radius=0.08)
        body = wrapped(item["text"], spec.get("wrap", 52), S.BODY_SIZE)
        rows.append(VGroup(dot, body).arrange(RIGHT, buff=0.3, aligned_edge=UP))
        dot.shift(DOWN * 0.12)
    if not rows:
        return []
    group = fit_content(VGroup(*rows).arrange(DOWN, buff=0.4, aligned_edge=LEFT))
    return [
        Beat(lambda r=row: [FadeIn(r, shift=RIGHT * 0.3)], cue=item.get("cue"))
        for row, item in zip(group, items)
    ]


@visual("cards")
def cards(spec: Spec) -> list[Beat]:
    """Side-by-side cards: issues, fixes, metrics. Items: {title, body, cue, tone}."""
    items = [item_fields(i) for i in spec.get("items", [])]
    default_tone = spec.get("tone", "neutral")
    per_row = spec.get("per_row", min(3, max(1, len(items))))
    card_w = min(4.0, (S.CONTENT_WIDTH - 0.4 * (per_row - 1)) / per_row)
    chars = int(card_w * 6.2)
    built = []
    for n, item in enumerate(items, 1):
        color = S.tone(item.get("tone", default_tone))
        title = item.get("title", item.get("text", ""))
        if spec.get("numbered"):
            title = f"{n}. {title}"
        head = wrapped(title, chars - 4, S.LABEL_SIZE + 2, color, weight="BOLD")
        body = wrapped(item.get("body", ""), chars, S.SMALL_SIZE, S.TEXT) if item.get("body") else VGroup()
        inner = VGroup(head, body).arrange(DOWN, buff=0.25, aligned_edge=LEFT)
        box = RoundedRectangle(
            width=card_w, height=max(1.4, inner.height + 0.6), corner_radius=0.15,
            stroke_color=color, fill_color=color, fill_opacity=0.12,
        )
        inner.move_to(box).align_to(box, UP).shift(DOWN * 0.3)
        built.append(VGroup(box, inner))
    if not built:
        return []
    rows = [VGroup(*built[i:i + per_row]).arrange(RIGHT, buff=0.4, aligned_edge=UP)
            for i in range(0, len(built), per_row)]
    fit_content(VGroup(*rows).arrange(DOWN, buff=0.4))
    return [
        Beat(lambda c=card: [FadeIn(c, shift=UP * 0.3)], cue=item.get("cue"))
        for card, item in zip(built, items)
    ]


def _node_shape(label: str, shape: str, color) -> VGroup:
    name = text(label, S.LABEL_SIZE, S.TEXT)
    w, h = max(1.9, name.width + (1.1 if shape == "queue" else 0.5)), 0.95
    if shape == "db":
        body = Rectangle(width=w, height=h, stroke_width=0, fill_color=color, fill_opacity=0.15)
        top = Ellipse(width=w, height=0.35, color=color, fill_color=color, fill_opacity=0.3).move_to(body.get_top())
        bottom = Ellipse(width=w, height=0.35, color=color).move_to(body.get_bottom())
        sides = VGroup(Line(body.get_corner(UP + LEFT), body.get_corner(DOWN + LEFT), color=color),
                       Line(body.get_corner(UP + RIGHT), body.get_corner(DOWN + RIGHT), color=color))
        frame = VGroup(body, bottom, sides, top)
    elif shape == "queue":
        frame = Rectangle(width=w, height=h * 0.8, color=color, fill_color=color, fill_opacity=0.15)
        ticks = VGroup(*[Line(UP * 0.3, DOWN * 0.3, color=color, stroke_width=2) for _ in range(3)])
        ticks.arrange(RIGHT, buff=0.15).next_to(frame.get_right(), LEFT, buff=0.15)
        frame = VGroup(frame, ticks)
        name.next_to(ticks, LEFT, buff=0.15)
    else:
        frame = RoundedRectangle(width=w, height=h, corner_radius=0.15, color=color,
                                 fill_color=color, fill_opacity=0.15)
    if shape != "queue":
        name.move_to(frame)
    return VGroup(frame, name)


@visual("diagram")
def diagram(spec: Spec) -> list[Beat]:
    """Boxes and arrows on a grid.

    nodes: [{id, label, col, row, shape: box|db|queue, tone, cue}]
    edges: [{from, to, label, cue}] or [from, to]
    problem: [node ids] marked with a red cross (cue: problem_cue)
    highlight: [node ids] pulsed in yellow (cue: highlight_cue)
    note: one line shown under the diagram (cue: note_cue)
    """
    nodes_spec = spec.get("nodes", [])
    col_gap, row_gap = spec.get("col_gap", 3.2), spec.get("row_gap", 1.7)
    nodes: dict[str, VGroup] = {}
    for i, n in enumerate(nodes_spec):
        col, row = n.get("col", i), n.get("row", 0)
        node = _node_shape(n.get("label", n["id"]), n.get("shape", "box"), S.tone(n.get("tone")))
        node.move_to(RIGHT * col * col_gap + DOWN * row * row_gap)
        nodes[n["id"]] = node

    edges = []
    for e in spec.get("edges", []):
        e = {"from": e[0], "to": e[1]} if isinstance(e, list) else e
        a, b = nodes[e["from"]], nodes[e["to"]]
        direction = b.get_center() - a.get_center()
        bend = e.get("bend", 0)  # radians; positive curves left of the a->b direction
        start = a[0].get_boundary_point(rotate_vector(direction, -bend / 2))
        end = b[0].get_boundary_point(rotate_vector(-direction, bend / 2))
        if bend:
            arrow = CurvedArrow(start, end, angle=bend, stroke_width=3, color=S.MUTED, tip_length=0.2)
        else:
            arrow = Arrow(start, end, buff=0.12, stroke_width=3, color=S.MUTED, max_tip_length_to_length_ratio=0.15)
        parts = [arrow]
        if e.get("label"):
            label = text(e["label"], S.SMALL_SIZE, S.MUTED)
            normal = rotate_vector(normalize(end - start), PI / 2)
            label.move_to(arrow.point_from_proportion(0.5) + normal * 0.28)
            parts.append(label)
        edges.append((VGroup(*parts), e))

    whole = VGroup(*nodes.values(), *[g for g, _ in edges])
    note = None
    if spec.get("note"):
        note = text(spec["note"], S.LABEL_SIZE, S.ACCENT, width=S.CONTENT_WIDTH)
        whole.add(note)
        note.next_to(VGroup(*nodes.values(), *[g for g, _ in edges]), DOWN, buff=0.5)
    fit_content(whole)

    def edge_anims(groups):
        return [Create(g[0]) for g in groups] + [FadeIn(l) for g in groups for l in g[1:]]

    # Nodes appear in the order listed (neighbours in the same column together,
    # unless cued). An un-cued edge grows as soon as both of its ends are on
    # screen; that is decided at play time because cues can reorder beats.
    batches: list[list[dict]] = []
    for n in nodes_spec:
        prev = batches[-1][-1] if batches else None
        same_col = n.get("col") is not None and prev is not None and prev.get("col") == n.get("col")
        if same_col and not n.get("cue") and not prev.get("cue"):
            batches[-1].append(n)
        else:
            batches.append([n])

    shown: set[str] = set()
    pending = [(g, e) for g, e in edges if not e.get("cue")]

    def reveal(batch):
        shown.update(n["id"] for n in batch)
        ready = [(g, e) for g, e in pending if e["from"] in shown and e["to"] in shown]
        for item in ready:
            pending.remove(item)
        return [FadeIn(nodes[n["id"]], scale=0.9) for n in batch] + edge_anims([g for g, _ in ready])

    beats: list[Beat] = [Beat(lambda b=batch: reveal(b), cue=batch[0].get("cue")) for batch in batches]
    for g, e in edges:
        if e.get("cue"):
            beats.append(Beat(lambda g=g: edge_anims([g]), cue=e["cue"]))

    if spec.get("problem"):
        targets = [nodes[i] for i in spec["problem"]]
        beats.append(Beat(lambda: [Create(Cross(t, stroke_color=S.PROBLEM, stroke_width=5, scale_factor=0.6)) for t in targets],
                          cue=spec.get("problem_cue")))
    if spec.get("highlight"):
        targets = [nodes[i] for i in spec["highlight"]]
        beats.append(Beat(lambda: [Create(SurroundingRectangle(t, color=S.ACCENT, buff=0.12)) for t in targets]
                          + [Indicate(t, color=S.ACCENT, scale_factor=1.08) for t in targets],
                          cue=spec.get("highlight_cue"), run_time=1.0))
    if note is not None:
        beats.append(Beat(lambda: [FadeIn(note, shift=UP * 0.2)], cue=spec.get("note_cue")))
    return beats


@visual("table")
def table(spec: Spec) -> list[Beat]:
    """A grid revealed row by row. columns: [...]; rows: [[...]] or [{cells, cue}]."""
    columns = spec.get("columns", [])
    rows = [r if isinstance(r, dict) else {"cells": r} for r in spec.get("rows", [])]
    n_cols = max([len(columns)] + [len(r["cells"]) for r in rows])
    widths = spec.get("widths") or [S.CONTENT_WIDTH / max(1, n_cols)] * n_cols
    chars = [max(8, int(w * 5.6)) for w in widths]

    def make_row(cells, color, weight):
        out = VGroup()
        for i in range(n_cols):
            cell = wrapped(cells[i] if i < len(cells) else "", chars[i], S.SMALL_SIZE + 2, color, weight)
            slot = Rectangle(width=widths[i], height=cell.height + 0.3, stroke_opacity=0)
            cell.move_to(slot).align_to(slot, LEFT).shift(RIGHT * 0.15)
            out.add(VGroup(slot, cell))
        h = max(c.height for c in out)
        for c in out:
            c[0].stretch_to_fit_height(h)
        return out.arrange(RIGHT, buff=0)

    header = make_row(columns, S.ACCENT, "BOLD") if columns else None
    body = [make_row(r["cells"], S.TEXT, "NORMAL") for r in rows]
    lines = []
    stack = VGroup(*([header] if header else []), *body).arrange(DOWN, buff=0.08)
    if header:
        rule = Line(LEFT, RIGHT, color=S.ACCENT, stroke_width=2).set_width(stack.width)
        rule.next_to(header, DOWN, buff=0.04)
        lines.append(rule)
    fit_content(VGroup(stack, *lines))

    beats = []
    if header:
        beats.append(Beat(lambda: [FadeIn(header), *[Create(l) for l in lines]]))
    beats += [Beat(lambda r=row: [FadeIn(r, shift=DOWN * 0.15)], cue=spec_row.get("cue"))
              for row, spec_row in zip(body, rows)]
    return beats


@visual("array")
def array(spec: Spec) -> list[Beat]:
    """Array cells with indices, then animated steps for algorithm walkthroughs.

    values: [1, 1, 2, ...]
    steps: [{highlight: [indices], tone, note, cue}]
    """
    values = spec.get("values", [])
    cells = VGroup()
    for i, v in enumerate(values):
        box = RoundedRectangle(width=0.95, height=0.95, corner_radius=0.08, color=S.PRIMARY,
                               fill_color=S.PRIMARY, fill_opacity=0.1)
        val = text(v, S.BODY_SIZE).move_to(box)
        idx = text(i, S.SMALL_SIZE, S.MUTED).next_to(box, DOWN, buff=0.12)
        cells.add(VGroup(box, val, idx))
    cells.arrange(RIGHT, buff=0.1)
    label = text(spec["label"], S.LABEL_SIZE, S.MUTED).next_to(cells, LEFT, buff=0.4) if spec.get("label") else VGroup()
    note_anchor = Dot(radius=0.001).next_to(cells, DOWN, buff=0.9)
    fit_content(VGroup(label, cells, note_anchor))

    beats = [Beat(lambda: [FadeIn(label), LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in cells], lag_ratio=0.1)],
                  run_time=1.0, cue=spec.get("cue"))]
    state = {"note": None}

    def step_anims(step):
        color = S.tone(step.get("tone", "accent"))
        hl = set(step.get("highlight", []))
        anims = []
        for i, c in enumerate(cells):
            target = color if i in hl else S.PRIMARY
            anims.append(c[0].animate.set_stroke(target).set_fill(target, opacity=0.35 if i in hl else 0.1))
        if state["note"] is not None:
            anims.append(FadeOut(state["note"]))
            state["note"] = None
        if step.get("note"):
            note = text(step["note"], S.LABEL_SIZE, color, width=S.CONTENT_WIDTH).move_to(note_anchor)
            state["note"] = note
            anims.append(FadeIn(note, shift=UP * 0.15))
        return anims

    for step in spec.get("steps", []):
        beats.append(Beat(lambda s=step: step_anims(s), cue=step.get("cue"), run_time=0.6))
    return beats

