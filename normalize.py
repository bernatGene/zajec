import json


def format_context(
    pr_data: dict,
    comments: list,
    reviews: list,
    review_comments: list,
) -> str:
    result = {
        "pr": {
            "number": pr_data["number"],
            "title": pr_data["title"],
            "body": pr_data["body"],
            "url": pr_data["url"],
            "state": pr_data["state"],
            "author": pr_data["author"]["login"] if pr_data.get("author") else None,
            "base_ref": pr_data["baseRefName"],
            "head_ref": pr_data["headRefName"],
        },
        "comments": [],
    }

    for c in comments:
        result["comments"].append(
            {
                "kind": "issue_comment",
                "id": c["id"],
                "author": c["user"]["login"],
                "created_at": c["created_at"],
                "body": c["body"],
            }
        )

    for r in reviews:
        result["comments"].append(
            {
                "kind": "review",
                "id": r["id"],
                "author": r["user"]["login"],
                "created_at": r["submitted_at"],
                "state": r["state"],
                "body": r["body"],
            }
        )

    for rc in review_comments:
        result["comments"].append(
            {
                "kind": "review_comment",
                "id": rc["id"],
                "author": rc["user"]["login"],
                "created_at": rc["created_at"],
                "path": rc["path"],
                "line": rc.get("line"),
                "body": rc["body"],
            }
        )

    result["comments"].sort(key=lambda x: x["created_at"])
    return json.dumps(result, indent=2)
