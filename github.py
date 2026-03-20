import json
import subprocess
from pathlib import Path


def run_gh(repo: str, *args: str) -> str:
    cmd = ["gh", "--repo", repo] + list(args)
    result = subprocess.run_gh(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh failed: {result.stderr}")
    return result.stdout


def fetch_pr_meta(repo: str, pr_number: int) -> dict:
    return json.loads(
        run_gh(
            repo,
            "pr",
            "view",
            str(pr_number),
            "--json",
            "number,title,body,url,state,author,baseRefName,headRefName",
        )
    )


def fetch_comments(repo: str, pr_number: int) -> list:
    output = run_gh(
        repo, "api", f"repos/{repo}/issues/{pr_number}/comments", "--paginate"
    )
    return json.loads(output) if output.strip() else []


def fetch_reviews(repo: str, pr_number: int) -> list:
    output = run_gh(
        repo, "api", f"repos/{repo}/pulls/{pr_number}/reviews", "--paginate"
    )
    return json.loads(output) if output.strip() else []


def fetch_review_comments(repo: str, pr_number: int) -> list:
    output = run_gh(
        repo, "api", f"repos/{repo}/pulls/{pr_number}/comments", "--paginate"
    )
    return json.loads(output) if output.strip() else []


def publish_comment(repo: str, pr_number: int, body_file: str) -> None:
    path = Path(body_file)
    if not path.exists():
        raise FileNotFoundError(f"Comment file not found: {body_file}")
    content = path.read_text()
    if not content.strip():
        raise ValueError("Comment file is empty")
    run_gh(repo, "pr", "comment", str(pr_number), "--body-file", str(path))
