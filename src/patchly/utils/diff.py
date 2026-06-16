from __future__ import annotations

import re


def parse_diff(diff_text: str) -> list[dict]:
    files = []
    current = None

    for line in diff_text.split("\n"):
        m = re.match(r"^\+\+\+ b/(.+)", line)
        if m:
            current = {"path": m.group(1), "hunks": []}
            files.append(current)
            continue
        m = re.match(r"^@@ -(\d+),\d+ \+(\d+),\d+ @@", line)
        if m and current is not None:
            current["hunks"].append({
                "old_start": int(m.group(1)),
                "new_start": int(m.group(2)),
                "lines": [],
            })
            continue
        if current is not None and current["hunks"]:
            current["hunks"][-1]["lines"].append(line)

    return files


def extract_changed_files(diff_text: str) -> list[str]:
    paths = []
    for line in diff_text.split("\n"):
        m = re.match(r"^\+\+\+ b/(.+)", line)
        if m:
            paths.append(m.group(1))
    return paths
