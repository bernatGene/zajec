import asyncio
import json
from typing import Any


async def run_gh_async(repo: str, *args: str) -> str:
    cmd = ["gh", "--repo", repo] + list(args)
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode().strip()
        if proc.returncode < 0 or not err:
            raise asyncio.CancelledError()
        raise RuntimeError(f"gh failed: {err}")
    return stdout.decode()


async def run_gh_api_async(
    api_path: str, *args: str, paginate: bool = True
) -> str:
    cmd = ["gh", "api", api_path, *args]
    if paginate:
        cmd.append("--paginate")
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode().strip()
        if proc.returncode < 0 or not err:
            raise asyncio.CancelledError()
        raise RuntimeError(f"gh api failed: {err}")
    return stdout.decode()


async def list_open_prs(repo: str) -> list[dict[str, Any]]:
    output = await run_gh_async(
        repo, "pr", "list", "--state", "open", "--json", "number,title,url,headRefName"
    )
    return json.loads(output) if output.strip() else []


async def fetch_pr_meta(repo: str, pr_number: int) -> dict[str, Any]:
    return json.loads(
        await run_gh_async(
            repo,
            "pr",
            "view",
            str(pr_number),
            "--json",
            "number,title,body,url,state,headRefOid,headRefName",
        )
    )


async def fetch_comments(repo: str, pr_number: int) -> list[dict[str, Any]]:
    output = await run_gh_api_async(f"repos/{repo}/issues/{pr_number}/comments")
    return json.loads(output) if output.strip() else []


async def fetch_pr_commits(repo: str, pr_number: int) -> list[dict[str, Any]]:
    output = await run_gh_api_async(f"repos/{repo}/pulls/{pr_number}/commits")
    return json.loads(output) if output.strip() else []


async def fetch_check_runs(repo: str, sha: str) -> list[dict[str, Any]]:
    output = await run_gh_api_async(f"repos/{repo}/commits/{sha}/check-runs")
    data = json.loads(output)
    return data.get("check_runs", [])


async def post_comment(repo: str, pr_number: int, body: str) -> int:
    output = await run_gh_api_async(
        f"repos/{repo}/issues/{pr_number}/comments",
        "-X",
        "POST",
        "-f",
        f"body={body}",
        paginate=False,
    )
    return int(json.loads(output).get("id", 0))


async def update_comment(repo: str, comment_id: int, body: str) -> None:
    await run_gh_api_async(
        f"repos/{repo}/issues/comments/{comment_id}",
        "-X",
        "PATCH",
        "-f",
        f"body={body}",
        paginate=False,
    )


async def delete_comment(repo: str, comment_id: int) -> None:
    await run_gh_api_async(
        f"repos/{repo}/issues/comments/{comment_id}",
        "-X",
        "DELETE",
        paginate=False,
    )
