from unittest.mock import AsyncMock, patch

import pytest

from zajecdaemon.models import PRState, Task
from zajecdaemon.poller import (
    Poller,
    _is_merge_commit,
    _latest_non_merge_sha,
    _latest_zajec_comment_id,
)
from zajecdaemon.queueing import QueueManager
from zajecdaemon.state import StateStore


class TestLatestZajecCommentId:
    def test_no_comments(self):
        assert _latest_zajec_comment_id([]) == 0

    def test_no_matching_comments(self):
        comments = [{"id": 1, "body": "hello"}, {"id": 2, "body": "world"}]
        assert _latest_zajec_comment_id(comments) == 0

    def test_matching_comment(self):
        comments = [{"id": 10, "body": "@zajec review"}]
        assert _latest_zajec_comment_id(comments) == 10

    def test_highest_matching_id(self):
        comments = [
            {"id": 5, "body": "@zajec first"},
            {"id": 10, "body": "normal comment"},
            {"id": 15, "body": "@zajec second"},
        ]
        assert _latest_zajec_comment_id(comments) == 15

    def test_prefix_with_whitespace(self):
        comments = [{"id": 1, "body": "  @zajec review"}]
        assert _latest_zajec_comment_id(comments) == 1

    def test_prefix_in_middle(self):
        comments = [{"id": 1, "body": "please @zajec review"}]
        assert _latest_zajec_comment_id(comments) == 0


class TestIsMergeCommit:
    def test_single_parent(self):
        commit = {"sha": "abc", "parents": [{"sha": "def"}]}
        assert _is_merge_commit(commit) is False

    def test_two_parents(self):
        commit = {"sha": "abc", "parents": [{"sha": "def"}, {"sha": "ghi"}]}
        assert _is_merge_commit(commit) is True

    def test_no_parents_key(self):
        commit = {"sha": "abc"}
        assert _is_merge_commit(commit) is False


class TestLatestNonMergeSha:
    def test_empty_list(self):
        assert _latest_non_merge_sha([]) is None

    def test_all_non_merge(self):
        commits = [{"sha": "aaa", "parents": [{"sha": "000"}]}]
        assert _latest_non_merge_sha(commits) == "aaa"

    def test_latest_is_merge(self):
        commits = [
            {"sha": "aaa", "parents": [{"sha": "000"}]},
            {"sha": "bbb", "parents": [{"sha": "000"}, {"sha": "111"}]},
        ]
        assert _latest_non_merge_sha(commits) == "aaa"

    def test_all_merge(self):
        commits = [
            {"sha": "bbb", "parents": [{"sha": "000"}, {"sha": "111"}]},
        ]
        assert _latest_non_merge_sha(commits) is None


class TestPoller:
    def _make_state(self, tmp_path, states=None):
        path = tmp_path / "state.json"
        store = StateStore(path)
        for s in states or []:
            store.set(s)
        store.save()
        return StateStore(path)

    @pytest.mark.asyncio
    async def test_new_pr_enqueued(self, tmp_path):
        state = self._make_state(tmp_path)
        qm = QueueManager()
        poller = Poller(state, qm)
        enqueued = []

        async def capture(task: Task):
            enqueued.append(task)

        with (
            patch(
                "zajecdaemon.poller.list_open_prs", new_callable=AsyncMock
            ) as mock_list,
            patch(
                "zajecdaemon.poller.fetch_pr_meta", new_callable=AsyncMock
            ) as mock_meta,
        ):
            mock_list.return_value = [
                {
                    "number": 42,
                    "title": "Test",
                    "url": "http://pr/42",
                    "headRefName": "branch",
                }
            ]
            mock_meta.return_value = {
                "number": 42,
                "title": "Test",
                "url": "http://pr/42",
                "headRefOid": "sha1",
                "headRefName": "branch",
                "state": "open",
            }

            await poller.poll_repo("owner/repo", capture)

        assert len(enqueued) == 1
        assert enqueued[0].pr_number == 42
        assert enqueued[0].head_sha == "sha1"
        assert enqueued[0].trigger_comment_id is None

        got = state.get("owner/repo", 42)
        assert got is not None
        assert got.head_sha_seen == "sha1"

    @pytest.mark.asyncio
    async def test_existing_pr_no_change(self, tmp_path):
        initial = PRState(
            repo="owner/repo",
            pr_number=42,
            pr_url="http://pr/42",
            head_sha_seen="sha1",
            head_sha_processed="sha1",
            last_zajec_comment_id_seen=0,
            last_zajec_comment_id_processed=0,
        )
        state = self._make_state(tmp_path, [initial])
        qm = QueueManager()
        poller = Poller(state, qm)
        enqueued = []

        async def capture(task: Task):
            enqueued.append(task)

        with (
            patch(
                "zajecdaemon.poller.list_open_prs", new_callable=AsyncMock
            ) as mock_list,
            patch(
                "zajecdaemon.poller.fetch_pr_meta", new_callable=AsyncMock
            ) as mock_meta,
            patch(
                "zajecdaemon.poller.fetch_comments", new_callable=AsyncMock
            ) as mock_comments,
        ):
            mock_list.return_value = [
                {
                    "number": 42,
                    "title": "Test",
                    "url": "http://pr/42",
                    "headRefName": "branch",
                }
            ]
            mock_meta.return_value = {
                "number": 42,
                "title": "Test",
                "url": "http://pr/42",
                "headRefOid": "sha1",
                "headRefName": "branch",
                "state": "open",
            }
            mock_comments.return_value = []

            await poller.poll_repo("owner/repo", capture)

        assert len(enqueued) == 0

    @pytest.mark.asyncio
    async def test_zajec_comment_trigger(self, tmp_path):
        initial = PRState(
            repo="owner/repo",
            pr_number=42,
            pr_url="http://pr/42",
            head_sha_seen="sha1",
        )
        state = self._make_state(tmp_path, [initial])
        qm = QueueManager()
        poller = Poller(state, qm)
        enqueued = []

        async def capture(task: Task):
            enqueued.append(task)

        with (
            patch(
                "zajecdaemon.poller.list_open_prs", new_callable=AsyncMock
            ) as mock_list,
            patch(
                "zajecdaemon.poller.fetch_pr_meta", new_callable=AsyncMock
            ) as mock_meta,
            patch(
                "zajecdaemon.poller.fetch_comments", new_callable=AsyncMock
            ) as mock_comments,
        ):
            mock_list.return_value = [
                {
                    "number": 42,
                    "title": "Test",
                    "url": "http://pr/42",
                    "headRefName": "branch",
                }
            ]
            mock_meta.return_value = {
                "number": 42,
                "title": "Test",
                "url": "http://pr/42",
                "headRefOid": "sha1",
                "headRefName": "branch",
                "state": "open",
            }
            mock_comments.return_value = [{"id": 100, "body": "@zajec review"}]

            await poller.poll_repo("owner/repo", capture)

        assert len(enqueued) == 1
        assert enqueued[0].trigger_comment_id == 100
        assert state.get("owner/repo", 42).last_zajec_comment_id_seen == 100

    @pytest.mark.asyncio
    async def test_new_commit_trigger(self, tmp_path):
        initial = PRState(
            repo="owner/repo",
            pr_number=42,
            pr_url="http://pr/42",
            head_sha_seen="sha1",
        )
        state = self._make_state(tmp_path, [initial])
        qm = QueueManager()
        poller = Poller(state, qm)
        enqueued = []

        async def capture(task: Task):
            enqueued.append(task)

        with (
            patch(
                "zajecdaemon.poller.list_open_prs", new_callable=AsyncMock
            ) as mock_list,
            patch(
                "zajecdaemon.poller.fetch_pr_meta", new_callable=AsyncMock
            ) as mock_meta,
            patch(
                "zajecdaemon.poller.fetch_comments", new_callable=AsyncMock
            ) as mock_comments,
            patch(
                "zajecdaemon.poller.fetch_pr_commits", new_callable=AsyncMock
            ) as mock_commits,
        ):
            mock_list.return_value = [
                {
                    "number": 42,
                    "title": "Test",
                    "url": "http://pr/42",
                    "headRefName": "branch",
                }
            ]
            mock_meta.return_value = {
                "number": 42,
                "title": "Test",
                "url": "http://pr/42",
                "headRefOid": "sha2",
                "headRefName": "branch",
                "state": "open",
            }
            mock_comments.return_value = []
            mock_commits.return_value = [{"sha": "sha2", "parents": [{"sha": "sha1"}]}]

            await poller.poll_repo("owner/repo", capture)

        assert len(enqueued) == 1
        assert enqueued[0].head_sha == "sha2"

    @pytest.mark.asyncio
    async def test_merge_commit_ignored(self, tmp_path):
        initial = PRState(
            repo="owner/repo",
            pr_number=42,
            pr_url="http://pr/42",
            head_sha_seen="sha1",
        )
        state = self._make_state(tmp_path, [initial])
        qm = QueueManager()
        poller = Poller(state, qm)
        enqueued = []

        async def capture(task: Task):
            enqueued.append(task)

        with (
            patch(
                "zajecdaemon.poller.list_open_prs", new_callable=AsyncMock
            ) as mock_list,
            patch(
                "zajecdaemon.poller.fetch_pr_meta", new_callable=AsyncMock
            ) as mock_meta,
            patch(
                "zajecdaemon.poller.fetch_comments", new_callable=AsyncMock
            ) as mock_comments,
            patch(
                "zajecdaemon.poller.fetch_pr_commits", new_callable=AsyncMock
            ) as mock_commits,
        ):
            mock_list.return_value = [
                {
                    "number": 42,
                    "title": "Test",
                    "url": "http://pr/42",
                    "headRefName": "branch",
                }
            ]
            mock_meta.return_value = {
                "number": 42,
                "title": "Test",
                "url": "http://pr/42",
                "headRefOid": "sha_merge",
                "headRefName": "branch",
                "state": "open",
            }
            mock_comments.return_value = []
            mock_commits.return_value = [
                {"sha": "sha_merge", "parents": [{"sha": "sha1"}, {"sha": "sha2"}]}
            ]

            await poller.poll_repo("owner/repo", capture)

        assert len(enqueued) == 0
        assert state.get("owner/repo", 42).head_sha_seen == "sha_merge"

    @pytest.mark.asyncio
    async def test_closed_pr_marked(self, tmp_path):
        initial = PRState(
            repo="owner/repo",
            pr_number=42,
            pr_url="http://pr/42",
            head_sha_seen="sha1",
            is_open=True,
        )
        state = self._make_state(tmp_path, [initial])
        qm = QueueManager()
        poller = Poller(state, qm)
        enqueued = []

        async def capture(task: Task):
            enqueued.append(task)

        with patch(
            "zajecdaemon.poller.list_open_prs", new_callable=AsyncMock
        ) as mock_list:
            mock_list.return_value = []

            await poller.poll_repo("owner/repo", capture)

        assert state.get("owner/repo", 42).is_open is False
        assert len(enqueued) == 0

    @pytest.mark.asyncio
    async def test_duplicate_enqueue_prevented(self, tmp_path):
        state = self._make_state(tmp_path)
        qm = QueueManager()
        qm.set_running("owner/repo", 42)
        poller = Poller(state, qm)
        enqueued = []

        async def capture(task: Task):
            enqueued.append(task)

        with (
            patch(
                "zajecdaemon.poller.list_open_prs", new_callable=AsyncMock
            ) as mock_list,
            patch(
                "zajecdaemon.poller.fetch_pr_meta", new_callable=AsyncMock
            ) as mock_meta,
        ):
            mock_list.return_value = [
                {
                    "number": 42,
                    "title": "Test",
                    "url": "http://pr/42",
                    "headRefName": "branch",
                }
            ]
            mock_meta.return_value = {
                "number": 42,
                "title": "Test",
                "url": "http://pr/42",
                "headRefOid": "sha1",
                "headRefName": "branch",
                "state": "open",
            }

            await poller.poll_repo("owner/repo", capture)

        assert len(enqueued) == 0
