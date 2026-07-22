import sys
from unittest.mock import patch

import pytest

from cli import main
from github import update_pr_title


def test_update_pr_title_calls_gh():
    with patch("github.run_gh") as run_gh:
        update_pr_title("owner/repo", 42, "[MOT-323] Improve retry handling")

    run_gh.assert_called_once_with(
        "owner/repo",
        "pr",
        "edit",
        "42",
        "--title",
        "[MOT-323] Improve retry handling",
    )


def test_update_pr_title_rejects_blank_title():
    with pytest.raises(ValueError, match="PR title is empty"):
        update_pr_title("owner/repo", 42, "  ")


def test_update_title_command(capsys):
    argv = [
        "zajec",
        "update-title",
        "--repo",
        "owner/repo",
        "--pr",
        "42",
        "--title",
        "[MOT-323] Improve retry handling",
    ]
    with patch.object(sys, "argv", argv), patch("cli.update_pr_title") as update:
        main()

    update.assert_called_once_with("owner/repo", 42, "[MOT-323] Improve retry handling")
    assert capsys.readouterr().out == (
        '{"repo":"owner/repo","pr":42,'
        '"title":"[MOT-323] Improve retry handling","updated":true}\n'
    )
