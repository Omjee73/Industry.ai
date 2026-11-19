"""Fetch the DeepPCB dataset repo README (canonical dataset) for research facts."""
from __future__ import annotations

from pathlib import Path

import urllib.request

OUT = Path(r"C:\Users\gomje\OneDrive\Documents\Default Project\docs_research_facts.txt")


def fetch(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": "pcb-inspector-research"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return f"ERROR: {e}"


def main() -> int:
    for branch in ("main", "master"):
        url = f"https://raw.githubusercontent.com/tangsanli5201/DeepPCB/{branch}/README.md"
        body = fetch(url)
        if body and not body.startswith("ERROR"):
            print(f"[DeepPCB README] {url} (branch {branch}), {len(body)} chars")
            # print first 3000 chars for facts
            print(body[:3000])
            OUT.write_text(OUT.read_text(encoding='utf-8', errors='replace') + f"\n\n[DeepPCB README {url}]\n{body[:5000]}\n", encoding="utf-8")
            return 0
        else:
            print(f"[DeepPCB README] {url}: {str(body)[:100]}")
    print("Not found on any branch.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
