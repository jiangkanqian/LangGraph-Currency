"""Adapted from the Kagent v0.9.10 LangGraph Currency example."""

import os

import httpx
from kagent.core import KAgentConfig
from kagent.langgraph import KAgentCheckpointer
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from currency.tools import get_exchange_rate

SYSTEM_INSTRUCTION = (
    "You answer currency exchange questions. Use get_exchange_rate for rates; never invent rates. "
    "Report the source currency, target currency, date and rate. If the tool fails, explain the failure. "
    "Ask for missing currency information. Do not perform financial transactions."
)


def build_graph(config: KAgentConfig):
    model = ChatOpenAI(
        model=os.environ["OPENAI_MODEL"],
        temperature=0,
        timeout=60,
        max_retries=1,
        base_url=os.getenv("OPENAI_BASE_URL"),
    )
    checkpointer = KAgentCheckpointer(client=httpx.AsyncClient(base_url=config.url), app_name=config.app_name)
    return create_react_agent(
        model=model,
        tools=[tool(get_exchange_rate)],
        checkpointer=checkpointer,
        prompt=SYSTEM_INSTRUCTION,
    )
