from datetime import datetime, timezone

from zajecdaemon.models import PRState, Task


def test_pr_state_key():
    s = PRState(
        repo="owner/repo", pr_number=42, pr_url="https://github.com/owner/repo/pull/42"
    )
    assert s.key == "owner/repo#42"


def test_pr_state_defaults():
    s = PRState(repo="owner/repo", pr_number=1, pr_url="url")
    assert s.is_open is True
    assert s.head_sha_seen == ""
    assert s.head_sha_processed == ""
    assert s.last_zajec_comment_id_seen == 0
    assert s.last_zajec_comment_id_processed == 0
    assert s.last_session_id == ""
    assert s.last_run_at is None
    assert s.last_run_status == ""
    assert s.ci_status == ""
    assert s.ci_trigger_comment_id is None


def test_task_defaults():
    t = Task(
        repo="owner/repo",
        pr_number=5,
        pr_url="url",
        head_sha="abc123",
        enqueued_at=datetime.now(timezone.utc),
    )
    assert t.trigger_comment_id is None


def test_task_with_comment_id():
    t = Task(
        repo="owner/repo",
        pr_number=5,
        pr_url="url",
        head_sha="abc123",
        trigger_comment_id=99,
        enqueued_at=datetime.now(timezone.utc),
    )
    assert t.trigger_comment_id == 99


def test_pr_state_serialization_roundtrip():
    s = PRState(
        repo="owner/repo",
        pr_number=7,
        pr_url="url",
        head_sha_seen="sha1",
        last_zajec_comment_id_seen=42,
    )
    data = s.model_dump(mode="json")
    s2 = PRState(**data)
    assert s2 == s
