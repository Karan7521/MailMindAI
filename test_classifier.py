from agents.classifier import classify_email


def test_classifier_uses_fallback_without_api_key(monkeypatch):
    monkeypatch.setattr("agents.classifier.client", None)
    assert classify_email("Interview Tomorrow", "Please join the interview") == "Needs Reply"
    assert classify_email("Security alert", "Verify your password") == "Urgent"
    assert classify_email("Special offer", "Unsubscribe from this sale") == "Newsletter"
    assert classify_email("You win free money", "Crypto lottery") == "Spam"