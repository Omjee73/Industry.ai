"""Export the current OpenCode session transcript to AI_CHAT_HISTORY.md.

The export is written directly from OpenCode's local SQLite database
(~/.local/share/opencode/opencode.db) — no network and no other tool needed.

Usage:
    python backend/scripts/export_chat_history.py [--out AI_CHAT_HISTORY.md]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
SESSION_ID = "ses_e0c5b5fd9ffeiTlRdI2AJ4vMgC"


def _clip(text: str, limit: int = 6000) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… [truncated, {len(text) - limit} chars omitted]"


def _extract_message(data: str, row_type: str) -> list[str]:
    """Turn one session_message row into markdown blocks."""
    blocks: list[str] = []
    d = json.loads(data)
    kind = row_type
    if kind == "user":
        text = d.get("text") or d.get("metadata", {}).get("displayText", "")
        blocks.append("### User\n\n" + _clip(text))
        return blocks
    if kind == "system":
        blocks.append("### System notice\n\n" + _clip(d.get("text", "")))
        return blocks
    if kind == "assistant":
        for part in d.get("content", []) or []:
            if not isinstance(part, dict):
                continue
            ptype = part.get("type")
            if ptype == "reasoning":
                blocks.append("### Reasoning\n\n" + _clip(part.get("text", ""), 4000))
            elif ptype == "text":
                blocks.append("### Response\n\n" + _clip(part.get("text", "")))
            elif ptype == "tool":
                name = part.get("name", "?")
                state = part.get("state", {}) or {}
                blocks.append(f"### Tool: `{name}`")
                blocks.append("**Input:**")
                blocks.append("```json")
                blocks.append(_clip(json.dumps(state.get("input", {}), indent=2, default=str), 3000))
                blocks.append("```")
                blocks.append("**Output:**")
                out_parts = state.get("content", []) or []
                out_text = "\n".join(p.get("text", "") for p in out_parts if isinstance(p, dict))
                blocks.append("```text")
                blocks.append(_clip(out_text, 4000))
                blocks.append("```")
                status = state.get("status")
                if status:
                    blocks.append(f"(status: {status})")
        return blocks
    blocks.append(f"### [{kind} message]")
    blocks.append(_clip(json.dumps(d, indent=2, default=str)[:2000]))
    return blocks


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the OpenCode session transcript.")
    parser.add_argument(
        "--out", default=str(Path(__file__).resolve().parents[2] / "AI_CHAT_HISTORY.md")
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: OpenCode database not found at {DB_PATH}")
        return 1

    con = sqlite3.connect(str(DB_PATH))
    rows = con.execute(
        "SELECT seq, type, data FROM session_message WHERE session_id = ? ORDER BY seq",
        (SESSION_ID,),
    ).fetchall()

    header = f"""# AI Chat History — PCB Missing Component Detection (Task B)

- **Session:** `{SESSION_ID}` ("PCB Missing Component Detection")
- **Exported:** {datetime.now().strftime("%Y-%m-%d %H:%M")} (from the local OpenCode database)
- **Messages:** {len(rows)}

> This file is an export of the complete OpenCode conversation that built this project,
> starting from the very first prompt of the session. Tool outputs are bounded per entry
> for readability; the session itself is the source of truth.

---

"""

    chunks: list[str] = []
    for seq, mtype, data in rows:
        blocks = _extract_message(data, mtype)
        body = "\n\n".join(b for b in blocks if b.strip())
        chunks.append(f"## #{seq} — {mtype}\n\n{body}\n")

    out = header + "\n".join(chunks)
    Path(args.out).write_text(out, encoding="utf-8")
    print(f"Wrote {len(chunks)} messages to {args.out} ({len(out)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
