from uuid import uuid4

from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def payload(**overrides):
    data = {"session_id": str(uuid4()), "topic": "Python", "message": "What is a list?"}
    data.update(overrides)
    return data


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_frontend():
    response = client.get("/")
    assert response.status_code == 200
    assert "TopicChat AI" in response.text


def test_topics():
    response = client.get("/topics")
    assert "General" in response.json()["topics"]


def test_chat(monkeypatch):
    def fake_agent(message, topic, session_id):
        assert message == "What is a list?"
        assert topic == "Python"
        return "A list stores ordered items."
    monkeypatch.setattr(main, "chat_with_agent", fake_agent)
    response = client.post("/chat", json=payload())
    assert response.status_code == 200
    assert response.json() == {"answer": "A list stores ordered items.", "answer_html": "<p>A list stores ordered items.</p>\n", "topic": "Python"}


def test_bad_topic():
    response = client.post("/chat", json=payload(topic="Not a real topic"))
    assert response.status_code == 400


def test_blank_message():
    response = client.post("/chat", json=payload(message="   "))
    assert response.status_code == 422


def test_missing_key(monkeypatch):
    def broken_agent(*args, **kwargs):
        raise RuntimeError("GROQ_API_KEY is missing")
    monkeypatch.setattr(main, "chat_with_agent", broken_agent)
    response = client.post("/chat", json=payload())
    assert response.status_code == 503
