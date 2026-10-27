"""Agent 4 must strip numbers that the telemetry payload cannot support."""

from backend.agents.grounding import (
    audit_text,
    collect_numbers,
    epistemic_note,
    strip_ungrounded,
)
from backend.engine.telemetry_engine import build_telemetry


def test_injected_fake_numbers_are_stripped():
    payload = {"shift_distance_m": 26.2, "ppda_5m": 15.2, "zone": "3v2"}
    prose = (
        "The shift was 26.2 m, but the heart-rate monitor hit 180, "
        "the secret index was 9999 and the made-up xG was 9.9."
    )
    cleaned, kept, stripped = strip_ungrounded(prose, collect_numbers(payload))
    assert "26.2" in cleaned
    assert "180" not in cleaned
    assert "9999" not in cleaned
    assert "9.9" not in cleaned
    assert cleaned.count("[unverified]") == 3
    assert stripped == 3
    assert kept >= 1


def test_real_telemetry_keeps_engine_numbers_and_strips_fiction():
    telemetry = build_telemetry(minute=54)
    prose = "Shift 26.2 with PPDA 15.2 and a fictional 9999 metre run plus a 180 bpm spike."
    cleaned, kept, stripped = audit_text(prose, telemetry)
    assert "26.2" in cleaned
    assert "15.2" in cleaned
    assert "9999" not in cleaned
    assert "180" not in cleaned
    assert stripped == 2
    assert kept >= 2


def test_epistemic_note_for_unanswerable_question():
    note = epistemic_note("What was his heart rate in the locker room?", None, 0)
    assert note is not None
    assert "heart rate" in note.lower()
    assert "cannot prove" in note.lower()
