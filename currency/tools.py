"""Validated exchange-rate requests, without a model dependency."""

import os
import re
from datetime import date

import httpx


def get_exchange_rate(currency_from: str = "USD", currency_to: str = "EUR", currency_date: str = "latest") -> dict:
    """Fetch the published exchange rate for two ISO currency codes and a date or 'latest'."""
    source, target = currency_from.upper(), currency_to.upper()
    if not all(re.fullmatch(r"[A-Z]{3}", code) for code in (source, target)):
        return {"error": "Currency codes must contain three ASCII letters."}
    if currency_date != "latest":
        try:
            date.fromisoformat(currency_date)
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", currency_date):
                raise ValueError
        except ValueError:
            return {"error": "Date must be latest or YYYY-MM-DD."}
    if source == target:
        return {"base": source, "date": currency_date, "rates": {target: 1.0}}
    try:
        base = os.getenv("EXCHANGE_RATE_BASE_URL", "https://api.frankfurter.app").rstrip("/")
        response = httpx.get(f"{base}/{currency_date}", params={"from": source, "to": target}, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        rate = data.get("rates", {}).get(target) if isinstance(data, dict) else None
        if isinstance(rate, bool) or not isinstance(rate, (int, float)) or rate <= 0:
            return {"error": "Invalid exchange-rate response."}
        return data
    except httpx.HTTPError:
        return {"error": "Exchange-rate service request failed."}
    except (ValueError, AttributeError):
        return {"error": "Invalid exchange-rate response."}
