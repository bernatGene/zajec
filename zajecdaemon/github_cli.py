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


async def run_gh_api_async(api_path: str) -> str:
    cmd = ["gh", "api", api_path, "--paginate"]
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
