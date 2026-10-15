import json

from scripts import release


def test_wait_ignores_stale_ready_and_other_agent(monkeypatch):
    def deployment(uid, image, observed):
        return {
            "metadata": {"generation": 2, "ownerReferences": [{"uid": uid}]},
            "spec": {"replicas": 1, "template": {"spec": {"containers": [{"image": image}]}}},
            "status": {"observedGeneration": observed, "updatedReplicas": 1, "availableReplicas": 1, "replicas": 1},
        }

    polls = iter(
        [
            [deployment("other", "repo:new", 2), deployment("agent", "repo:old", 2)],
            [deployment("agent", "repo:new", 1)],
            [deployment("agent", "repo:new", 2)],
        ]
    )
    sleeps = []

    def kubectl(*args):
        if args[1] == "agent":
            return json.dumps({"metadata": {"uid": "agent"}})
        return json.dumps({"items": next(polls)})

    monkeypatch.setattr(release, "kubectl", kubectl)
    monkeypatch.setattr(release.time, "sleep", lambda seconds: sleeps.append(seconds))
    release.wait_ready("kagent", "currency-dev", "repo:new", 30)
    assert sleeps == [5, 5]
