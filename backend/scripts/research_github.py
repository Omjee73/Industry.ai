"""Query the GitHub API for relevant PCB projects/datasets; save full JSON + compact summary."""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://api.github.com/search/repositories"

QUERIES = [
    "DeepPCB dataset PCB defect detection",
    "PCB defect detection OpenCV missing component",
    "PCB visual inspection OpenCV",
]

OUT = Path(r"C:\Users\gomje\OneDrive\Documents\Default Project\docs_github_search.json")


def search(q: str, per_page: int = 10):
    url = f"{BASE}?{urllib.parse.urlencode({'q': q, 'per_page': per_page, 'sort': 'stars'})}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "pcb-inspector-research", "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def compact(items):
    for it in items:
        desc = it.get("description") or "(no description)"
        created = (it.get("created_at") or "?")[:10]
        print(f"- [{it['full_name']}](https://github.com/{it['full_name']}) stars {it.get('stargazers_count', 0)} - {desc} [{created}]")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    all_results = {}
    for q in QUERIES:
        data = search(q)
        all_results[q] = data
        print(f"\n### Query: {q!r} (total {data.get('total_count')})")
        compact(data.get("items", []))
    OUT.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"\nFull results saved to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
