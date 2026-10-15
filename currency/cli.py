"""Standalone console entry point; Kagent supplies runtime identity in Kubernetes."""

import json
import logging
import os
from importlib.resources import files

import uvicorn
from kagent.core import KAgentConfig
from kagent.langgraph import KAgentApp

from currency.agent import build_graph


def create_app():
    config = KAgentConfig()
    card = json.loads(files("currency").joinpath("agent-card.json").read_text(encoding="utf-8"))
    card["url"] = os.getenv("AGENT_URL", "http://localhost:8080/")
    return KAgentApp(
        graph=build_graph(config),
        agent_card=card,
        config=config,
        tracing=os.getenv("OTEL_TRACING_ENABLED", "false").lower() == "true",
    ).build()


def main():
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(create_app(), host="0.0.0.0", port=int(os.getenv("PORT", "8080")))


if __name__ == "__main__":
    main()
