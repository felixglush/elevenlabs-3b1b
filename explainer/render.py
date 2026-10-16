"""Draw the video with Manim (the library 3Blue1Brown's videos are made with).

The renderer only knows about sections, word timings and visuals. It knows
nothing about TTS providers or captions, so either can change independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from manim import FadeIn, FadeOut, Scene, tempconfig

from . import style as S
from .timing import find_cue, schedule
from .topic import Section
from .tts import Speech
from .visuals import build_beats, section_heading


@dataclass(frozen=True)
class Segment:
    section: Section
    speech: Speech


@dataclass(frozen=True)
class RenderedVideo:
    path: Path
    durations: list[float]  # actual on-screen length of each segment


class Renderer(Protocol):
    def render(self, segments: list[Segment], out_dir: Path) -> RenderedVideo: ...


class ExplainerScene(Scene):
    segments: list[Segment] = []

    def construct(self):
        self.durations: list[float] = []
        for seg in self.segments:
            self.durations.append(self.play_segment(seg))

    def play_segment(self, seg: Segment) -> float:
        clock = 0.0

        def advance_to(t: float):
            nonlocal clock
            if t > clock + 1 / 60:
                self.wait(t - clock)
                clock = t

        def play(anims, run_time):
            nonlocal clock
            if anims:
                self.play(*anims, run_time=run_time)
                clock += run_time

        if seg.section.heading:
            play([FadeIn(section_heading(seg.section.heading, seg.section.role))], 0.4)

        beats = build_beats(seg.section.visual)
        times = schedule([b.cue for b in beats], list(seg.speech.words), seg.speech.duration,
                         start=clock, reveal_by=S.REVEAL_BY)
        for beat in beats:
            if beat.cue and find_cue(list(seg.speech.words), beat.cue) is None:
                print(f"  warning: cue '{beat.cue}' is not in the {seg.section.role} narration; spacing it evenly")
        for at, _, beat in sorted(zip(times, range(len(beats)), beats), key=lambda x: x[:2]):
            advance_to(at)
            play(beat.make(), beat.run_time)

        advance_to(seg.speech.duration + 0.3)  # let the last word breathe
        if self.mobjects:
            play([FadeOut(*self.mobjects)], S.FADE_SECONDS)
        return clock


QUALITY = {"low": "low_quality", "medium": "medium_quality", "high": "high_quality", "4k": "fourk_quality"}


class ManimRenderer:
    def __init__(self, quality: str = "medium"):
        self.quality = QUALITY[quality]

    def render(self, segments: list[Segment], out_dir: Path) -> RenderedVideo:
        out_dir.mkdir(parents=True, exist_ok=True)
        scene_cls = type("Explainer", (ExplainerScene,), {"segments": segments})
        with tempconfig({
            "quality": self.quality,
            "media_dir": str(out_dir / "manim"),
            "output_file": "video",
            "background_color": S.BACKGROUND,
            "disable_caching": True,
            "verbosity": "WARNING",
            "progress_bar": "none",
        }):
            scene = scene_cls()
            scene.render()
            path = Path(scene.renderer.file_writer.movie_file_path)
        return RenderedVideo(path, scene.durations)
