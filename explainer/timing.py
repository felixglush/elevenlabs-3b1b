"""Decide when each beat plays, from the narration's word timings."""

from __future__ import annotations

import re

from .tts import Word

LEAD = 0.15  # start an animation slightly before the word, so it lands on it


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def find_cue(words: list[Word], cue: str, after: float = 0.0) -> float | None:
    """Start time of the first occurrence of `cue` (a word or phrase) after `after`."""
    target = [_norm(w) for w in cue.split() if _norm(w)]
    if not target:
        return None
    tokens = [_norm(w.text) for w in words]
    for i, word in enumerate(words):
        if word.start < after:
            continue
        window = tokens[i:i + len(target)]
        if window == target or (len(target) > 1 and window[:1] == target[:1] and window[-1:] == target[-1:]):
            return max(0.0, word.start - LEAD)
    # A looser match: the cue's first word is a prefix ("cache" matches "caching").
    for i, word in enumerate(words):
        if word.start >= after and tokens[i].startswith(target[0][:5]):
            return max(0.0, word.start - LEAD)
    return None


def schedule(cues: list[str | None], words: list[Word], duration: float,
             start: float = 0.0, reveal_by: float = 0.8) -> list[float]:
    """Target start time for each beat (play them sorted by this time).

    Cued beats snap to the first time their phrase is spoken (a repeated cue
    snaps to the next occurrence). Un-cued beats are spread evenly between
    their neighbours in the list, or between the section start and
    `reveal_by` of the way through the narration.
    """
    known: list[float | None] = []
    last_seen: dict[str, float] = {}
    for cue in cues:
        t = None
        if cue:
            t = find_cue(words, cue, last_seen.get(cue.lower(), start))
            if t is not None:
                last_seen[cue.lower()] = t + 0.01
        known.append(t)

    times: list[float] = []
    i = 0
    while i < len(cues):
        if known[i] is not None:
            times.append(known[i])
            i += 1
            continue
        j = i
        while j < len(cues) and known[j] is None:
            j += 1
        lo = times[-1] if times else start
        hi = known[j] if j < len(cues) else duration * reveal_by
        hi = max(hi, lo)
        slots = j - i + (1 if j < len(cues) else 0)
        step = (hi - lo) / slots if slots else 0
        offset = 0 if not times else 1
        times.extend(lo + step * (k + offset) for k in range(j - i))
        i = j
    return times
