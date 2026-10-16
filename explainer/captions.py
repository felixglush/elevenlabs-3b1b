"""Turn word timings into short caption lines and write them as an .srt file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .tts import Word


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


def build_cues(words: list[Word], max_chars: int = 42, max_gap: float = 0.6) -> list[Cue]:
    """Group words into caption lines.

    A line ends when it would get too long, after sentence punctuation, or
    when the speaker pauses for longer than `max_gap` seconds.
    """
    cues: list[Cue] = []
    line: list[Word] = []

    def flush():
        if line:
            cues.append(Cue(line[0].start, line[-1].end, " ".join(w.text for w in line)))
            line.clear()

    for word in words:
        too_long = line and len(" ".join(w.text for w in line)) + 1 + len(word.text) > max_chars
        paused = line and word.start - line[-1].end > max_gap
        if too_long or paused:
            flush()
        line.append(word)
        if word.text[-1] in ".?!":
            flush()
    flush()
    return cues


def shift(cues: list[Cue], offset: float) -> list[Cue]:
    return [Cue(c.start + offset, c.end + offset, c.text) for c in cues]


def _timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def write_srt(cues: list[Cue], path: Path) -> Path:
    blocks = []
    for i, cue in enumerate(cues, 1):
        # Hold each line until the next starts so captions don't flicker off between words.
        end = cues[i].start if i < len(cues) and cues[i].start - cue.end < 0.5 else cue.end + 0.2
        blocks.append(f"{i}\n{_timestamp(cue.start)} --> {_timestamp(end)}\n{cue.text}\n")
    path.write_text("\n".join(blocks))
    return path
