"""Look and feel, kept in one place so restyling never touches layout code.

Palette follows 3Blue1Brown conventions: dark background, blue for the main
thing, yellow for "look here", red for problems, green for fixes. Viewers learn
the vocabulary, so keep the meanings consistent across sections.
"""

from manim import BLUE, GREEN, GREY_B, GREY_D, RED, TEAL, WHITE, YELLOW, ORANGE, PURPLE

BACKGROUND = "#0E1117"
FONT = "Inter"  # falls back to the system sans-serif if not installed

PRIMARY = BLUE
ACCENT = YELLOW
PROBLEM = RED
FIX = GREEN
DATA = TEAL
AGENT = PURPLE
EXTRA = ORANGE
TEXT = WHITE
MUTED = GREY_B
DIM = GREY_D

TONES = {
    "neutral": PRIMARY,
    "danger": PROBLEM,
    "good": FIX,
    "accent": ACCENT,
    "data": DATA,
    "agent": AGENT,
    "extra": EXTRA,
}

ROLE_COLORS = {
    "hook": ACCENT,
    "functional": PRIMARY,
    "non_functional": TEAL,
    "high_level": PRIMARY,
    "issues": PROBLEM,
    "deep_dive": FIX,
    "eval_dataset": AGENT,
    "evaluation": AGENT,
    "extensions": EXTRA,
    "recap": ACCENT,
    "brute_force": PROBLEM,
    "insight": ACCENT,
    "walkthrough": PRIMARY,
    "complexity": TEAL,
}

# Frame is 14.2 x 8 units. Captions are burned into the bottom strip, so
# visuals stay inside this box.
CONTENT_TOP = 2.75
CONTENT_BOTTOM = -2.55
CONTENT_WIDTH = 12.6

HEADING_SIZE = 30
TITLE_SIZE = 60
BODY_SIZE = 30
LABEL_SIZE = 22
SMALL_SIZE = 18

BEAT_SECONDS = 0.8  # default length of one reveal animation
FADE_SECONDS = 0.4  # fade between sections
REVEAL_BY = 0.8  # un-cued beats are spread over the first 80% of the narration


def tone(name: str | None, default=PRIMARY):
    if name is None:
        return default
    return TONES.get(name, name)  # also accepts raw colors like "#FF8800"
