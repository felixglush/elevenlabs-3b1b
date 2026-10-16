"""Join the silent animation, the narration and the captions with ffmpeg."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{' '.join(cmd)}\n{result.stderr[-2000:]}")


def narration_track(audio_paths: list[Path], durations: list[float], out: Path) -> Path:
    """One audio file where clip i is padded or trimmed to exactly durations[i]."""
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for p in audio_paths:
        cmd += ["-i", str(p)]
    chains = [
        f"[{i}:a]aresample=44100,aformat=channel_layouts=mono,apad,atrim=0:{d:.3f}[a{i}]"
        for i, d in enumerate(durations)
    ]
    joined = "".join(f"[a{i}]" for i in range(len(durations)))
    graph = ";".join(chains) + f";{joined}concat=n={len(durations)}:v=0:a=1[out]"
    run(cmd + ["-filter_complex", graph, "-map", "[out]", "-c:a", "aac", "-b:a", "160k", str(out)])
    return out


CAPTION_STYLE = (
    "FontName=Inter,FontSize=17,PrimaryColour=&H00FFFFFF,OutlineColour=&H99000000,"
    "BorderStyle=3,Outline=6,Shadow=0,MarginV=22,Alignment=2"
)


def mux(video: Path, audio: Path, out: Path, subtitles: Path | None = None) -> Path:
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(audio)]
    if subtitles:
        escaped = str(subtitles.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        cmd += ["-vf", f"subtitles='{escaped}':force_style='{CAPTION_STYLE}'", "-c:v", "libx264",
                "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p"]
    else:
        cmd += ["-c:v", "copy"]
    cmd += ["-map", "0:v", "-map", "1:a", "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out)]
    run(cmd)
    return out
