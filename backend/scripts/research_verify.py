"""Verify doc URLs and search for the canonical DeepPCB dataset repo/paper."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(r"C:\Users\gomje\OneDrive\Documents\Default Project\docs_research_facts.txt")


def fetch(url: str, timeout: int = 30, user_agent: bool = True) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": "pcb-inspector-research"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return f"ERROR: {e}"


def search_github(q: str, per_page: int = 10):
    url = f"https://api.github.com/search/repositories?{urllib.parse.urlencode({'q': q, 'per_page': per_page, 'sort': 'stars'})}"
    req = urllib.request.Request(url, headers={"User-Agent": "pcb-inspector-research", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main() -> int:
    lines: list[str] = []

    # 1. scikit-image metrics page (SSIM)
    for url in [
        "https://scikit-image.org/docs/stable/api/skimage.metrics.html",
        "https://scikit-image.org/docs/stable/api/skimage.metrics.html#skimage.metrics.structural_similarity_index_measure",
    ]:
        body = fetch(url)
        if body and not body.startswith("ERROR"):
            has_ssim = "structural_similarity_index_measure" in body or "structural_similarity" in body
            lines.append(f"[skimage metrics page] {url} -> 200 OK, mentions structural_similarity: {has_ssim}")
            break
        else:
            lines.append(f"[skimage metrics page] {url} -> {body[:120]}")

    # 2. OpenCV calib3d group (findHomography, estimateAffinePartial2D)
    body = fetch("https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html")
    if body and not body.startswith("ERROR"):
        has_fh = "findHomography" in body
        lines.append(f"[OpenCV calib3d] https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html -> 200 OK, mentions findHomography: {has_fh}")
    else:
        lines.append(f"[OpenCV calib3d] ERROR: {str(body)[:120]}")

    # 3. OpenCV ORB class page
    for url in [
        "https://docs.opencv.org/4.x/db/d27/classcv_1_1ORB.html",
        "https://docs.opencv.org/4.x/d7/d15/classcv_1_1ORB.html",
    ]:
        body = fetch(url)
        if body and not body.startswith("ERROR") and "ORB" in body:
            lines.append(f"[OpenCV ORB] {url} -> 200 OK")
            break

    # 4. GitHub search for canonical DeepPCB dataset repo / paper
    for q in ["DeepPCB dataset", "tangsanli5201/DeepPCB", "DeepPCB PCB defect detection paper"]:
        try:
            data = search_github(q)
            items = data.get("items", [])[:8]
            lines.append(f"\n[GitHub] q={q!r} total={data.get('total_count')}")
            for it in items:
                desc = re.sub(r"\s+", " ", it.get("description") or "")[:140]
                lines.append(f"  - {it['full_name']} (stars {it.get('stargazers_count')}) - {desc}")
        except Exception as e:
            lines.append(f"[GitHub] q={q!r} ERROR: {e}")

    text = "\n".join(lines)
    print(text)
    OUT.write_text(text, encoding="utf-8")
    print(f"\nSaved to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
