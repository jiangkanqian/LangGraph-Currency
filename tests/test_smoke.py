import pytest

from scripts.smoke import validate_result


@pytest.mark.parametrize(
    "body",
    [
        {"error": {"code": -1}},
        {},
        {"result": {"kind": "task", "status": {"state": "failed"}}},
        {"result": {"kind": "message", "parts": []}},
    ],
)
def test_smoke_rejects_failures(body):
    with pytest.raises(RuntimeError):
        validate_result(body)


def test_smoke_accepts_completed_task():
    assert validate_result(
        {
            "result": {
                "kind": "task",
                "status": {"state": "completed"},
                "artifacts": [{"parts": [{"kind": "text", "text": "USD EUR 0.9"}]}],
            }
        }
    )
