from agents.drafter import draft_reply


def test_drafter_uses_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr("agents.drafter.client", None)
    assert draft_reply("Interview Tomorrow", "Please confirm your availability")