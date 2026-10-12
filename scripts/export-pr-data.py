#!/usr/bin/env python3
"""Export merged-PR data for scripts/metrics.py using the GitHub CLI (`gh`). Stdlib only.

  export-pr-data.py [--repo OWNER/REPO] [--since YYYY-MM-DD] [--limit 200] > data.json

Finding comments are PR comments carrying `<!-- eng-ai-finding:<lens> -->`; their thumbs up and
down reactions are the precision signal. Not yet run against real GitHub: `gh` is not installed
where this was written, so only the parsing (`pr_record`) is tested.
"""
import argparse
import json
import re
import subprocess
import sys

MARKER = re.compile(r"<!--\s*eng-ai-finding:([\w-]+)\s*-->")


def pr_record(pr, comments):
    findings = []
    for c in comments:
        m = MARKER.search(c.get("body") or "")
        if m:
            reactions = c.get("reactions", {})
            findings.append({"lens": m.group(1), "up": reactions.get("+1", 0), "down": reactions.get("-1", 0)})
    reviews = pr.get("reviews", [])
    return {
        "number": pr["number"],
        "body": pr.get("body") or "",
        "labels": [label["name"] for label in pr.get("labels", [])],
        "changes_requested": sum(1 for r in reviews if r.get("state") == "CHANGES_REQUESTED"),
        "findings": findings,
    }


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"gh {' '.join(args)} failed: {r.stderr.strip()}")
    return json.loads(r.stdout)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    ap.add_argument("--since")
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args(argv)
    repo = ["--repo", args.repo] if args.repo else []
    query = ["pr", "list", "--state", "merged", "--limit", str(args.limit),
             "--json", "number,body,labels,reviews", *repo]
    if args.since:
        query += ["--search", f"merged:>={args.since}"]
    prs = gh(*query)
    slug = args.repo or gh("repo", "view", "--json", "nameWithOwner")["nameWithOwner"]
    records = [pr_record(pr, gh("api", f"repos/{slug}/issues/{pr['number']}/comments", "--paginate")) for pr in prs]
    json.dump({"prs": records}, sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
