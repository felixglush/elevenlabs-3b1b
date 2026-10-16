"""Fast tests for the parts with logic in them (no rendering)."""

from pathlib import Path

from explainer.captions import build_cues
from explainer.structures import validate
from explainer.timing import find_cue, schedule
from explainer.topic import Section, Topic, load_topic
from explainer.tts import SilentTTS, Word, chars_to_words

ROOT = Path(__file__).resolve().parent.parent


def words(text: str) -> list[Word]:
    return [Word(w, i * 1.0, i * 1.0 + 0.8) for i, w in enumerate(text.split())]


def test_sample_topics_and_templates_are_valid():
    for path in [*ROOT.glob("topics/*.yaml"), *ROOT.glob("templates/*.yaml")]:
        assert validate(load_topic(path)) == [], path.name


def test_validate_catches_too_many_issues_and_wrong_order():
    def section(role, items=()):
        return Section(role, "", "word " * 10, {"type": "cards", "items": list(items)})

    topic = Topic("t", "system_design", "T", (
        section("functional"), section("hook"), section("non_functional"), section("high_level"),
        section("issues", ["a", "b", "c", "d"]), section("deep_dive"), section("extensions"),
    ))
    problems = " ".join(validate(topic))
    assert "out of order" in problems
    assert "keep it to 3" in problems


def test_find_cue_matches_phrases_and_punctuation():
    ws = words("First, we add a cache. Then the cache warms up.")
    assert find_cue(ws, "a cache") == 3 - 0.15
    assert find_cue(ws, "cache", after=5) == 7 - 0.15
    assert find_cue(ws, "database") is None


def test_schedule_snaps_cued_beats_and_spreads_the_rest():
    ws = words("one two three four five six seven eight nine ten")
    times = schedule([None, "five", None, None], ws, duration=10, reveal_by=0.8)
    assert times[1] == 4 - 0.15
    assert times[0] == 0
    assert times[1] < times[2] < times[3] <= 8


def test_captions_break_on_sentences_and_length():
    ws = words("Short sentence. " + "word " * 20)
    cues = build_cues(ws, max_chars=30)
    assert cues[0].text == "Short sentence."
    assert all(len(c.text) <= 30 for c in cues)


def test_elevenlabs_character_alignment_becomes_words():
    chars = list("hi there")
    starts = [i * 0.1 for i in range(len(chars))]
    ends = [s + 0.1 for s in starts]
    result = chars_to_words(chars, starts, ends)
    assert [w.text for w in result] == ["hi", "there"]
    assert abs(result[1].start - 0.3) < 1e-9


def test_silent_tts_writes_audio(tmp_path):
    speech = SilentTTS().synthesize("Hello there, world.", tmp_path / "x")
    assert speech.audio_path.exists()
    assert len(speech.words) == 3
    assert speech.duration > speech.words[-1].end
