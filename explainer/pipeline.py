"""Topic in, captioned video out. Each stage is passed in, so any can be swapped."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .captions import build_cues, shift, write_srt
from .compose import mux, narration_track
from .render import Renderer, Segment
from .structures import MAX_SECONDS
from .topic import Topic
from .tts import TTSProvider


@dataclass(frozen=True)
class Output:
    video: Path
    captions: Path
    seconds: float


def render_topic(topic: Topic, tts: TTSProvider, renderer: Renderer, out_dir: Path,
                 captions: bool = True, log=print) -> Output:
    build = out_dir / "build"
    build.mkdir(parents=True, exist_ok=True)

    log(f"1/4 narrating {len(topic.sections)} sections with '{tts.name}'")
    segments = [Segment(s, tts.synthesize(s.narration)) for s in topic.sections]

    log("2/4 animating")
    video = renderer.render(segments, build)
    total = sum(video.durations)
    start = 0.0
    for seg, length in zip(segments, video.durations):
        log(f"    {start:6.1f}s  {seg.section.role:15} {length:5.1f}s  {seg.section.heading}")
        start += length
    if total > MAX_SECONDS:
        log(f"warning: video is {total:.0f}s, over the {MAX_SECONDS}s target; trim the narration")

    log("3/4 writing captions")
    cues, offset = [], 0.0
    for seg, length in zip(segments, video.durations):
        cues += shift(build_cues(list(seg.speech.words)), offset)
        offset += length
    srt = write_srt(cues, out_dir / f"{topic.slug}.srt")

    log("4/4 mixing audio and burning in captions")
    audio = narration_track([s.speech.audio_path for s in segments], video.durations, build / "narration.m4a")
    final = mux(video.path, audio, out_dir / f"{topic.slug}.mp4", srt if captions else None)
    shutil.rmtree(build / "manim", ignore_errors=True)
    return Output(final, srt, total)
