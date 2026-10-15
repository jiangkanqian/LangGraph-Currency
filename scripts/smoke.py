"""A2A smoke: health, discovery and one completed currency task (requires a real runtime)."""

import argparse
import json
import uuid

import httpx


def validate_result(body):
    if body.get("error"):
        raise RuntimeError(f"A2A error: {body['error']}")
    result = body.get("result", {})
    if result.get("kind") == "task":
        if result.get("status", {}).get("state") != "completed":
            raise RuntimeError("A2A task did not complete")
        parts = [part for artifact in result.get("artifacts", []) for part in artifact.get("parts", [])]
    elif result.get("kind") == "message":
        parts = result.get("parts", [])
    else:
        raise RuntimeError("Missing A2A task/message result")
    text = " ".join(p.get("text", "") for p in parts)
    if not text.strip():
        raise RuntimeError("A2A result has no text")
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Direct Agent service URL, not the Kagent UI")
    parser.add_argument("--discovery-only", action="store_true")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    with httpx.Client(timeout=120) as client:
        client.get(f"{base}/health").raise_for_status()
        card = client.get(f"{base}/.well-known/agent-card.json")
        card.raise_for_status()
        assert card.json().get("skills"), "No Agent skills advertised"
        if args.discovery_only:
            print("Health and A2A discovery passed (no model/tool invocation)")
            return
        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Use get_exchange_rate to get the latest USD to EUR rate."}],
                },
                "configuration": {"blocking": True},
            },
        }
        response = client.post(f"{base}/", json=request)
        response.raise_for_status()
        print(json.dumps({"answer": validate_result(response.json())}, ensure_ascii=False))
        print("A2A completion passed; inspect traces/evaluations to verify tool use and factual correctness")


if __name__ == "__main__":
    main()
