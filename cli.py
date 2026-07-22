import argparse
import json
import sys

from github import (
    fetch_comments,
    fetch_pr_meta,
    fetch_review_comments,
    fetch_reviews,
    publish_comment,
    update_pr_title,
)
from normalize import format_context


def main() -> None:
    parser = argparse.ArgumentParser(prog="zajec")
    subparsers = parser.add_subparsers(dest="command")

    ctx_parser = subparsers.add_parser("get-context", help="Fetch PR context as JSON")
    ctx_parser.add_argument("--repo", required=True, help="owner/repo")
    ctx_parser.add_argument("--pr", type=int, required=True, help="PR number")

    pub_parser = subparsers.add_parser(
        "publish-comment", help="Publish a comment to PR"
    )
    pub_parser.add_argument("--repo", required=True, help="owner/repo")
    pub_parser.add_argument("--pr", type=int, required=True, help="PR number")
    pub_parser.add_argument("--body-file", required=True, help="Path to markdown file")

    title_parser = subparsers.add_parser("update-title", help="Update a PR title")
    title_parser.add_argument("--repo", required=True, help="owner/repo")
    title_parser.add_argument("--pr", type=int, required=True, help="PR number")
    title_parser.add_argument("--title", required=True, help="New PR title")

    args = parser.parse_args()

    if args.command == "get-context":
        try:
            pr_data = fetch_pr_meta(args.repo, args.pr)
            comments = fetch_comments(args.repo, args.pr)
            reviews = fetch_reviews(args.repo, args.pr)
            review_comments = fetch_review_comments(args.repo, args.pr)
            result = format_context(pr_data, comments, reviews, review_comments)
            print(result)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "publish-comment":
        try:
            publish_comment(args.repo, args.pr, args.body_file)
            print(json.dumps({"repo": args.repo, "pr": args.pr, "published": True}))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "update-title":
        try:
            update_pr_title(args.repo, args.pr, args.title)
            result = {
                "repo": args.repo,
                "pr": args.pr,
                "title": args.title,
                "updated": True,
            }
            print(json.dumps(result, separators=(",", ":")))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
