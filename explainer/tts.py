"""Text to speech. Every provider turns text into an audio file plus word timings.

Word timings are what make captions (and visuals that appear "on cue") line up
with the voice. To add a provider, write a class with a `name` and a
`synthesize(text, out_stem)` method, then register it in PROVIDERS.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

import requests


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class Speech:
    audio_path: Path
    duration: float
    words: tuple[Word, ...]


class TTSProvider(Protocol):
    name: str

    def synthesize(self, text: str, out_stem: Path) -> Speech:
        """Write audio to `out_stem` + an extension and return its timings."""
        ...


class SilentTTS:
    """Offline stand-in: silent audio with word timings estimated from pace.

    Lets you iterate on visuals and captions without spending API credits.
    """

    name = "silent"

    def __init__(self, words_per_minute: float = 150):
        self.seconds_per_char = 60 / words_per_minute / 5.5  # ~5.5 chars per word incl. space

    def synthesize(self, text: str, out_stem: Path) -> Speech:
        words, t = [], 0.0
        for token in text.split():
            length = (len(token) + 1) * self.seconds_per_char
            pause = 0.25 if token[-1] in ".?!" else 0.1 if token[-1] in ",;:" else 0.0
            words.append(Word(token, t, t + length))
            t += length + pause
        duration = t + 0.2
        path = out_stem.with_suffix(".wav")
        with wave.open(str(path), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(22050)
            f.writeframes(b"\x00\x00" * int(22050 * duration))
        return Speech(path, duration, tuple(words))


class ElevenLabsTTS:
    """ElevenLabs text-to-speech using the `with-timestamps` endpoint.

    That endpoint returns per-character timings; we group them into words.
    """

    name = "elevenlabs"
    URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"

    def __init__(
        self,
        api_key: str | None = None,
        voice_id: str = "JBFqnCBsd6RMkjVDRZzb",
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        speed: float = 1.0,
    ):
        # ELEVEN_API_KEY is the name the official ElevenLabs SDK uses; accept either.
        self.api_key = (
            api_key or os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVEN_API_KEY")
        )
        if not self.api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is not set (put it in .env or your shell)")
        self.voice_id = voice_id
        self.model_id = model_id
        self.voice_settings = {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "speed": speed,
        }

    @property
    def cache_salt(self) -> str:
        return f"{self.voice_id}:{self.model_id}:{sorted(self.voice_settings.items())}"

    def synthesize(self, text: str, out_stem: Path) -> Speech:
        response = requests.post(
            self.URL.format(voice_id=self.voice_id),
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": self.api_key, "Content-Type": "application/json"},
            json={"text": text, "model_id": self.model_id, "voice_settings": self.voice_settings},
            timeout=120,
        )
        response.raise_for_status()
        body = response.json()
        path = out_stem.with_suffix(".mp3")
        path.write_bytes(base64.b64decode(body["audio_base64"]))
        alignment = body.get("alignment") or body["normalized_alignment"]
        words = chars_to_words(
            alignment["characters"],
            alignment["character_start_times_seconds"],
            alignment["character_end_times_seconds"],
        )
        return Speech(path, probe_duration(path), tuple(words))


def chars_to_words(chars: list[str], starts: list[float], ends: list[float]) -> list[Word]:
    words: list[Word] = []
    buf, w_start, w_end = "", 0.0, 0.0
    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            if buf:
                words.append(Word(buf, w_start, w_end))
            buf = ""
            continue
        if not buf:
            w_start = s
        buf += ch
        w_end = e
    if buf:
        words.append(Word(buf, w_start, w_end))
    return words


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


class CachedTTS:
    """Wraps any provider so identical text is only synthesized (and paid for) once."""

    def __init__(self, inner: TTSProvider, cache_dir: Path):
        self.inner = inner
        self.name = inner.name
        self.cache_dir = cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(self, text: str, out_stem: Path | None = None) -> Speech:
        salt = getattr(self.inner, "cache_salt", "")
        key = hashlib.sha256(f"{self.inner.name}|{salt}|{text}".encode()).hexdigest()[:16]
        meta = self.cache_dir / f"{key}.json"
        if meta.exists():
            data = json.loads(meta.read_text())
            return Speech(
                Path(data["audio_path"]),
                data["duration"],
                tuple(Word(**w) for w in data["words"]),
            )
        speech = self.inner.synthesize(text, self.cache_dir / key)
        meta.write_text(json.dumps({
            "audio_path": str(speech.audio_path),
            "duration": speech.duration,
            "words": [asdict(w) for w in speech.words],
        }))
        return speech


PROVIDERS: dict[str, type] = {"silent": SilentTTS, "elevenlabs": ElevenLabsTTS}


def make_tts(name: str, cache_dir: Path, **options) -> TTSProvider:
    if name not in PROVIDERS:
        raise ValueError(f"unknown TTS provider '{name}', expected one of {sorted(PROVIDERS)}")
    return CachedTTS(PROVIDERS[name](**options), cache_dir)
