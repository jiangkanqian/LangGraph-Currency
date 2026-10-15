from fastapi.testclient import TestClient
from kagent.core import KAgentConfig


def test_health_and_agent_card(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AGENT_URL", "http://currency.example/")
    from currency import cli

    monkeypatch.setattr(
        cli, "KAgentConfig", lambda: KAgentConfig(url="http://localhost:8083", name="currency-dev", namespace="kagent")
    )
    with TestClient(cli.create_app()) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/.well-known/agent-card.json")
        assert response.status_code == 200
        assert response.json()["url"] == "http://currency.example/"
        assert response.json()["capabilities"]["streaming"] is True
