import json

from zajecdaemon.models import PRState
from zajecdaemon.state import StateStore


def test_state_store_empty(tmp_path):
    store = StateStore(tmp_path / "state.json")
    assert store.get("owner/repo", 1) is None


def test_state_store_set_and_get(tmp_path):
    store = StateStore(tmp_path / "state.json")
    state = PRState(repo="owner/repo", pr_number=1, pr_url="url", head_sha_seen="abc")
    store.set(state)
    got = store.get("owner/repo", 1)
    assert got is not None
    assert got.head_sha_seen == "abc"


def test_state_store_persistence(tmp_path):
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.set(PRState(repo="owner/repo", pr_number=1, pr_url="url"))
    store.save()

    store2 = StateStore(path)
    got = store2.get("owner/repo", 1)
    assert got is not None
    assert got.pr_number == 1


def test_state_store_remove(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.set(PRState(repo="owner/repo", pr_number=1, pr_url="url"))
    store.remove("owner/repo", 1)
    assert store.get("owner/repo", 1) is None


def test_state_store_remove_nonexistent(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.remove("owner/repo", 99)


def test_state_store_all_open(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.set(PRState(repo="owner/repo", pr_number=1, pr_url="url", is_open=True))
    store.set(PRState(repo="owner/repo", pr_number=2, pr_url="url", is_open=False))
    store.set(PRState(repo="other/repo", pr_number=3, pr_url="url", is_open=True))
    result = store.all_open("owner/repo")
    assert len(result) == 1
    assert result[0].pr_number == 1


def test_state_store_all_for_repo(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.set(PRState(repo="owner/repo", pr_number=1, pr_url="url"))
    store.set(PRState(repo="owner/repo", pr_number=2, pr_url="url", is_open=False))
    store.set(PRState(repo="other/repo", pr_number=3, pr_url="url"))
    result = store.all_for_repo("owner/repo")
    assert len(result) == 2


def test_state_store_atomic_write(tmp_path):
    path = tmp_path / "state.json"
    store = StateStore(path)
    store.set(
        PRState(repo="owner/repo", pr_number=1, pr_url="url", head_sha_seen="sha1")
    )
    store.save()

    data = json.loads(path.read_text())
    assert "owner/repo#1" in data
