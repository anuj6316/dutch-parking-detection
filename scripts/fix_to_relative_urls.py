#!/usr/bin/env python3
"""
Convert URLs to relative paths that Label Studio understands
"""

import json
from pathlib import Path

INPUT_FILE = Path("scripts/labelstudio-import.json")
OUTPUT_FILE = Path("scripts/labelstudio-import-relative.json")


def fix_urls():
    with open(INPUT_FILE, "r") as f:
        tasks = json.load(f)

    print(f"Processing {len(tasks)} tasks...")

    for task in tasks:
        old_url = task["data"]["image"]

        # Replace full HTTP URLs with just the path
        # Label Studio will serve these from /label-studio/data/media/
        if old_url.startswith("http://"):
            new_url = old_url.replace("http://172.16.20.161:8080", "")
            task["data"]["image"] = new_url
            print(f"Fixed: {old_url} -> {new_url}")
        elif old_url.startswith("/data/upload/"):
            # Keep as is (already relative)
            pass

    # Save fixed JSON
    with open(OUTPUT_FILE, "w") as f:
        json.dump(tasks, f, indent=2)

    print(f"\nFixed file saved to: {OUTPUT_FILE}")
    print(f"Total tasks: {len(tasks)}")


if __name__ == "__main__":
    fix_urls()
