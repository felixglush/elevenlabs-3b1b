"""The lesson shape each kind of topic must follow, and a validator for it.

To add a new kind (say "behavioral"), add one entry to STRUCTURES and a
template in templates/. Nothing else needs to change.
"""

from __future__ import annotations

from dataclasses import dataclass

from .topic import Topic

WORDS_PER_MINUTE = 150  # typical narration pace; ElevenLabs is close to this
MAX_SECONDS = 5 * 60
MAX_ISSUES = 3


@dataclass(frozen=True)
class Slot:
    """One role in the lesson, and how many sections may fill it."""

    role: str
    min: int = 1
    max: int = 1
    hint: str = ""


_SYSTEM_DESIGN_CORE = [
    Slot("hook", hint="Why this problem is interesting, in two sentences."),
    Slot("functional", hint="What the system must do (features)."),
    Slot("non_functional", hint="Scale, latency, availability, consistency targets."),
    Slot("high_level", hint="The simplest design that meets the functional requirements."),
    Slot("issues", hint=f"At most {MAX_ISSUES} problems the simple design has at scale."),
    Slot("deep_dive", 1, MAX_ISSUES, hint="One section per issue, solving it."),
]

STRUCTURES: dict[str, list[Slot]] = {
    "system_design": _SYSTEM_DESIGN_CORE
    + [
        Slot("extensions", hint="A handful of follow-ups to study on your own."),
        Slot("recap", 0, 1),
    ],
    "agentic": _SYSTEM_DESIGN_CORE
    + [
        Slot("eval_dataset", hint="How to build the eval set: traces, error analysis, synthetic tuples."),
        Slot("evaluation", hint="Code checks, LLM judges aligned to humans, CI and production."),
        Slot("extensions", hint="A handful of follow-ups to study on your own."),
        Slot("recap", 0, 1),
    ],
    "neetcode": [
        Slot("hook", hint="State the problem with a tiny example."),
        Slot("brute_force", 0, 1, hint="The obvious solution and why it is slow."),
        Slot("insight", hint="The key observation that unlocks the fast solution."),
        Slot("walkthrough", 1, 3, hint="Animate the algorithm on the example."),
        Slot("complexity", hint="Time and space, and why."),
        Slot("extensions", hint="Related problems and variations to try next."),
        Slot("recap", 0, 1),
    ],
}


def estimated_seconds(topic: Topic) -> float:
    return topic.word_count / WORDS_PER_MINUTE * 60


def validate(topic: Topic) -> list[str]:
    """Return a list of problems; an empty list means the topic is good to render."""
    slots = STRUCTURES.get(topic.kind)
    if slots is None:
        return [f"unknown kind '{topic.kind}', expected one of {sorted(STRUCTURES)}"]

    errors: list[str] = []
    order = {slot.role: i for i, slot in enumerate(slots)}
    last = -1
    for section in topic.sections:
        idx = order.get(section.role)
        if idx is None:
            errors.append(f"role '{section.role}' is not part of a {topic.kind} lesson")
            continue
        if idx < last:
            errors.append(f"role '{section.role}' is out of order (expected order: {', '.join(order)})")
        last = max(last, idx)

    for slot in slots:
        count = sum(1 for s in topic.sections if s.role == slot.role)
        if not slot.min <= count <= slot.max:
            want = f"{slot.min}" if slot.min == slot.max else f"{slot.min}-{slot.max}"
            errors.append(f"expected {want} '{slot.role}' section(s), found {count}")

    for section in topic.sections:
        if section.role == "issues":
            items = section.visual.get("items", [])
            if len(items) > MAX_ISSUES:
                errors.append(f"'issues' lists {len(items)} problems; keep it to {MAX_ISSUES}")

    seconds = estimated_seconds(topic)
    if seconds > MAX_SECONDS:
        errors.append(
            f"narration is {topic.word_count} words (~{seconds:.0f}s); "
            f"cut to about {MAX_SECONDS * WORDS_PER_MINUTE // 60} words to stay under 5 minutes"
        )
    return errors
