import httpx
import pytest

from currency.tools import get_exchange_rate


def test_exchange_request(monkeypatch):
    def fake_get(url, *, params, timeout):
        assert url.endswith("/2026-01-02")
        assert params == {"from": "USD", "to": "EUR"}
        assert timeout == 10
        return httpx.Response(200, json={"rates": {"EUR": 0.9}}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    assert get_exchange_rate("usd", "eur", "2026-01-02")["rates"]["EUR"] == 0.9


@pytest.mark.parametrize("args", [("../", "EUR"), ("USD", "1AB"), ("USD", "EUR", "../secret")])
def test_invalid_inputs_never_request(monkeypatch, args):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: pytest.fail("unexpected network request"))
    assert "error" in get_exchange_rate(*args)


def test_same_currency():
    assert get_exchange_rate("USD", "USD")["rates"] == {"USD": 1.0}


@pytest.mark.parametrize("payload", [{}, [], {"rates": None}, {"rates": {"EUR": -1}}, {"rates": {"EUR": True}}])
def test_bad_service_response(monkeypatch, payload):
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: httpx.Response(200, json=payload, request=httpx.Request("GET", "https://example.com")),
    )
    assert "error" in get_exchange_rate()


def test_timeout(monkeypatch):
    def timeout(*a, **k):
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(httpx, "get", timeout)
    assert "error" in get_exchange_rate()
