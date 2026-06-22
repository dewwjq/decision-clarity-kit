#!/usr/bin/env python3
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REPO = os.environ.get("METRICS_REPO", "dewwjq/decision-clarity-kit")
TAG = os.environ.get("METRICS_RELEASE_TAG", "sample-v0.1")
OUTPUT = Path(os.environ.get("METRICS_OUTPUT", "metrics/daily.csv"))
API_ROOT = "https://api.github.com"


def github_json(path):
    request = urllib.request.Request(API_ROOT + path)
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def find_release():
    releases = github_json(f"/repos/{REPO}/releases")
    for release in releases:
        if release.get("tag_name") == TAG:
            return release
    raise SystemExit(f"Release tag not found: {TAG}")


def count_issues(label):
    label_query = urllib.parse.quote(label)
    issues = github_json(f"/repos/{REPO}/issues?state=all&labels={label_query}&per_page=100")
    return len([issue for issue in issues if "pull_request" not in issue])


def existing_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main():
    release = find_release()
    assets = {asset["name"]: asset["download_count"] for asset in release.get("assets", [])}
    row = {
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "release_tag": TAG,
        "sample_en_downloads": str(assets.get("decision-reset-sample-v0.1.zip", 0)),
        "sample_zh_downloads": str(assets.get("decision-reset-sample-zh-v0.1.zip", 0)),
        "early_access_issues": str(count_issues("early-access")),
    }

    rows = existing_rows(OUTPUT)
    if rows:
        last = rows[-1]
        comparable = ["sample_en_downloads", "sample_zh_downloads", "early_access_issues"]
        if all(last.get(key) == row[key] for key in comparable):
            print(json.dumps({"status": "unchanged", "row": row}, indent=2))
            return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        if not rows:
            writer.writeheader()
        writer.writerow(row)
    print(json.dumps({"status": "appended", "row": row, "output": str(OUTPUT)}, indent=2))
    return 0


if __name__ == "__main__":
    import urllib.parse

    sys.exit(main())
