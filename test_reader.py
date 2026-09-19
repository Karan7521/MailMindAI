from agents.reader import read_emails


class FakeMessages:
    def list(self, **kwargs):
        return self

    def get(self, **kwargs):
        return self

    def execute(self):
        return {
            "messages": [{"id": "1"}],
            "payload": {"headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "Subject", "value": "Hello"},
            ]},
            "snippet": "A message",
        }


class FakeService:
    def users(self):
        return self

    def messages(self):
        return FakeMessages()


def test_reader_accepts_injected_service():
    assert read_emails(FakeService()) == [{
        "id": "1",
        "subject": "Hello",
        "sender": "sender@example.com",
        "snippet": "A message",
    }]