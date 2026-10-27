from fastapi.testclient import TestClient

from backend.engine.auto_event import auto_event_segment
from backend.main import app

client = TestClient(app)


def test_health_on_both_prefixes():
    for path in ("/api/health", "/health"):
        body = client.get(path).json()
        assert body["status"] == "healthy"
        assert body["orchestrator"] == "Microsoft Semantic Kernel"
        assert body["fallback_ready"] is True


def test_analyze_diagnose_recap_and_telemetry():
    analyzed = client.post(
        "/api/analyze-moment",
        json={"minute": 82, "persona": "BROADCAST_STUDIO", "language": "en", "favorite_club": "NLR"},
    )
    assert analyzed.status_code == 200
    body = analyzed.json()
    assert body["mode"] == "fallback"
    assert any("33.8" in badge["label"] for badge in body["badges"])
    assert body["positions_22_players"]

    struggle = client.post(
        "/api/diagnose-struggle",
        json={"minute": 67, "team_id": "NLR", "persona": "CASUAL_FAN", "language": "en"},
    )
    assert struggle.status_code == 200
    assert "struggl" in struggle.json()["narrative_body"].lower() or "We" in struggle.json()["narrative_body"]

    recap = client.get("/api/recap", params={"persona": "CASUAL_FAN", "language": "es", "favorite_club": "MCB"})
    assert recap.status_code == 200
    payload = recap.json()
    assert [card["minute"] for card in payload["turning_points"]] == [22, 54, 82]
    assert payload["xg"]["NLR"] == 1.84
    assert payload["tactical_shifts"] == 4

    telemetry = client.get("/api/telemetry", params={"minute": 22})
    assert telemetry.json()["team_metrics"]["NLR"]["ppda_5m"] == 5.8


def test_live_stream_emits_sse():
    with client.stream("GET", "/api/live/stream", params={"start_minute": 89, "speed": 10}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        chunks = []
        for chunk in response.iter_text():
            chunks.append(chunk)
            if "done" in "".join(chunks):
                break
    body = "".join(chunks)
    assert "data:" in body
    assert '"current_minute": 89' in body or '"current_minute":89' in body
    assert '"done": true' in body or '"done":true' in body


def test_auto_event_detects_pass_shot_and_sprint_without_labels():
    for minute in (22, 54, 82):
        detected = auto_event_segment(minute)
        kinds = {event["event_type"] for event in detected["events"]}
        assert {"pass", "shot", "sprint"} <= kinds
        sprint = next(event for event in detected["events"] if event["event_type"] == "sprint")
        assert sprint["player_speed_kmh"] == 33.8
        assert sprint["sprint_threshold_triggered"] is True
        passed = next(event for event in detected["events"] if event["event_type"] == "pass")
        assert passed["pass_metrics"]["distance_m"] > 0
        assert passed["ball_speed_kmh"] > 0
        shot = next(event for event in detected["events"] if event["event_type"] == "shot")
        assert shot["shot_speed_kmh"] > 80

    api = client.post("/api/auto-event", json={"segment_minute": 54})
    assert api.status_code == 200
    assert "event" not in (api.json().get("frames_preview") or [{}])[0]
