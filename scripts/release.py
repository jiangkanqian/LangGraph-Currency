"""Apply an Agent CR and wait for its controller-owned Deployment to converge."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import yaml


def kubectl(*args, data=None):
    result = subprocess.run(
        ["kubectl", *args],
        input=json.dumps(data) if data is not None else None,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def wait_ready(namespace, name, image, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        agent = json.loads(kubectl("get", "agent", name, "-n", namespace, "-o", "json"))
        deployments = json.loads(kubectl("get", "deployments", "-n", namespace, "-o", "json"))["items"]
        owned = [
            d
            for d in deployments
            if any(owner["uid"] == agent["metadata"]["uid"] for owner in d["metadata"].get("ownerReferences", []))
        ]
        for deployment in owned:
            desired = deployment["spec"].get("replicas", 1)
            status = deployment.get("status", {})
            images = [c["image"] for c in deployment["spec"]["template"]["spec"]["containers"]]
            if (
                image in images
                and desired > 0
                and status.get("observedGeneration", 0) >= deployment["metadata"]["generation"]
                and status.get("updatedReplicas", 0) == desired
                and status.get("availableReplicas", 0) == desired
                and status.get("replicas", 0) == desired
            ):
                print(f"{namespace}/{name}: workload ready with {image}; run A2A smoke next")
                return
        time.sleep(5)
    raise TimeoutError(f"Timed out waiting for {namespace}/{name}; inspect Agent, Deployment and Pod events")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["deploy", "rollback"])
    parser.add_argument("--env", choices=["dev", "staging", "prod"], required=True)
    parser.add_argument("--image", required=True, help="Immutable tag or digest; on rollback use previous image")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    if args.image.endswith(":latest") or ":" not in args.image.rsplit("/", 1)[-1]:
        parser.error("Use a commit tag or digest, not latest or an untagged image")
    if "example.com" in args.image:
        parser.error("Replace the example registry with your real registry")
    manifest = yaml.safe_load(Path(f"deploy/{args.env}/agent.yaml").read_text(encoding="utf-8"))
    namespace, name = manifest["metadata"]["namespace"], manifest["metadata"]["name"]
    previous = kubectl("get", "agent", name, "-n", namespace, "-o", "json", "--ignore-not-found")
    if args.action == "rollback":
        if not previous.strip():
            parser.error("Cannot roll back an Agent that does not exist")
        manifest["spec"] = json.loads(previous)["spec"]
    manifest["spec"]["byo"]["deployment"]["image"] = args.image
    if args.action == "deploy":
        for key in ("OPENAI_MODEL", "OPENAI_BASE_URL"):
            value = os.environ.get(key)
            if not value:
                parser.error(f"Set {key} for the target environment")
            for item in manifest["spec"]["byo"]["deployment"]["env"]:
                if item["name"] == key:
                    item["value"] = value
    manifest["metadata"]["annotations"] = {
        "delivery.example.com/source-revision": os.getenv("GIT_COMMIT", "manual"),
        "delivery.example.com/action": args.action,
    }
    kubectl("apply", "--dry-run=server", "-f", "-", data=manifest)
    if previous.strip():
        Path(".release").mkdir(exist_ok=True)
        Path(f".release/{args.env}-previous.json").write_text(previous, encoding="utf-8")
        print("Previous image:", json.loads(previous)["spec"]["byo"]["deployment"]["image"])
    kubectl("apply", "-f", "-", data=manifest)
    wait_ready(namespace, name, args.image, args.timeout)


if __name__ == "__main__":
    main()
