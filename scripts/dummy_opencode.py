#!/usr/bin/env python3
"""Dummy opencode CLI for testing the runner.

Simulates opencode's JSON-stream output format. Behavior is controlled
via the DUMMY_OUTCOME environment variable:

  success         - normal completion (default)
  forbidden_once  - emits a forbidden-command block, then succeeds on resume
  forbidden_always- always emits a forbidden-command block
  failure         - emits an error and exits non-zero
"""

import argparse
import json
import os
import sys
import uuid


def main() -> None:
    parser = argparse.ArgumentParser(description="Dummy opencode CLI")
    sub = parser.add_subparsers(dest="command")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("prompt")
    run_parser.add_argument("--agent", default="codereview")
    run_parser.add_argument("--format", default="text", dest="fmt")
    run_parser.add_argument("-s", "--session", default=None)

    args = parser.parse_args()

    if args.command != "run":
        parser.print_help()
        sys.exit(1)

    outcome = os.environ.get("DUMMY_OUTCOME", "success")
    session_id = args.session or f"sess_{uuid.uuid4().hex[:8]}"
    is_resume = args.session is not None

    print(json.dumps({"type": "session_start", "sessionID": session_id}))

    if outcome == "success" or (outcome == "forbidden_once" and is_resume):
        print(
            json.dumps(
                {
                    "type": "assistant",
                    "content": "Review complete.",
                    "sessionID": session_id,
                }
            )
        )
        print(
            json.dumps(
                {
                    "type": "step_finish",
                    "reason": "stop",
                    "sessionID": session_id,
                }
            )
        )
    elif outcome == "forbidden_once" and not is_resume:
        print(
            json.dumps(
                {
                    "type": "tool_use",
                    "tool": "bash",
                    "state": {
                        "status": "error",
                        "error": "permission denied: command not allowed",
                    },
                    "sessionID": session_id,
                }
            )
        )
        print(
            json.dumps(
                {
                    "type": "step_finish",
                    "reason": "tool-calls",
                    "sessionID": session_id,
                }
            )
        )
    elif outcome == "forbidden_always":
        print(
            json.dumps(
                {
                    "type": "tool_use",
                    "tool": "bash",
                    "state": {
                        "status": "error",
                        "error": "permission denied: command not allowed",
                    },
                    "sessionID": session_id,
                }
            )
        )
        print(
            json.dumps(
                {
                    "type": "step_finish",
                    "reason": "tool-calls",
                    "sessionID": session_id,
                }
            )
        )
    elif outcome == "failure":
        print(
            json.dumps(
                {
                    "type": "error",
                    "message": "something went wrong",
                    "sessionID": session_id,
                }
            )
        )
        sys.exit(1)
    else:
        print(
            json.dumps(
                {
                    "type": "step_finish",
                    "reason": "stop",
                    "sessionID": session_id,
                }
            )
        )


if __name__ == "__main__":
    main()
