from zajecdaemon.queueing import PRStatus, QueueManager


def test_initial_status_is_idle():
    qm = QueueManager()
    assert qm.get_status("owner/repo", 1) == PRStatus.IDLE


def test_should_enqueue_idle():
    qm = QueueManager()
    assert qm.should_enqueue("owner/repo", 1) is True


def test_should_enqueue_queued():
    qm = QueueManager()
    qm.should_enqueue("owner/repo", 1)
    qm.set_running("owner/repo", 1)
    assert qm.should_enqueue("owner/repo", 1) is False


def test_should_enqueue_running_sets_rerun():
    qm = QueueManager()
    qm.set_running("owner/repo", 1)
    assert qm.should_enqueue("owner/repo", 1) is False
    assert qm.check_rerun("owner/repo", 1) is True


def test_set_running_and_idle():
    qm = QueueManager()
    qm.set_running("owner/repo", 1)
    assert qm.get_status("owner/repo", 1) == PRStatus.RUNNING
    qm.set_idle("owner/repo", 1)
    assert qm.get_status("owner/repo", 1) == PRStatus.IDLE


def test_set_idle_clears_rerun():
    qm = QueueManager()
    qm.set_running("owner/repo", 1)
    qm.should_enqueue("owner/repo", 1)
    assert qm.check_rerun("owner/repo", 1) is True
    qm.set_idle("owner/repo", 1)
    assert qm.check_rerun("owner/repo", 1) is False


def test_check_rerun_false_when_not_set():
    qm = QueueManager()
    assert qm.check_rerun("owner/repo", 1) is False


def test_check_rerun_clears_flag():
    qm = QueueManager()
    qm.set_running("owner/repo", 1)
    qm.should_enqueue("owner/repo", 1)
    assert qm.check_rerun("owner/repo", 1) is True
    assert qm.check_rerun("owner/repo", 1) is False


def test_different_prs_are_independent():
    qm = QueueManager()
    qm.set_running("owner/repo", 1)
    assert qm.get_status("owner/repo", 2) == PRStatus.IDLE
    assert qm.should_enqueue("owner/repo", 2) is True


def test_rerun_after_idle_re_enqueues():
    qm = QueueManager()
    assert qm.should_enqueue("owner/repo", 1) is True
    qm.set_running("owner/repo", 1)
    assert qm.should_enqueue("owner/repo", 1) is False
    rerun = qm.check_rerun("owner/repo", 1)
    assert rerun is True
    qm.set_idle("owner/repo", 1)
    assert qm.should_enqueue("owner/repo", 1) is True
