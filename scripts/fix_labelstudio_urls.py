#!/usr/bin/env python3
"""
Fix Label Studio image URLs to use full HTTP URLs
"""

import json
from pathlib import Path

HOST_IP = "172.16.20.161"
PORT = "8080"
INPUT_FILE = Path("scripts/labelstudio-import.json")
OUTPUT_FILE = Path("scripts/labelstudio-import-fixed.json")


def fix_urls():
    with open(INPUT_FILE, "r") as f:
        tasks = json.load(f)

    print(f"Processing {len(tasks)} tasks...")

    for task in tasks:
        old_url = task["data"]["image"]

        # Replace /data/upload/ with full URL
        if old_url.startswith("/data/upload/"):
            new_url = f"http://{HOST_IP}:{PORT}{old_url}"
            task["data"]["image"] = new_url
            print(f"Fixed: {old_url} -> {new_url}")

    # Save fixed JSON
    with open(OUTPUT_FILE, "w") as f:
        json.dump(tasks, f, indent=2)

    print(f"\nFixed file saved to: {OUTPUT_FILE}")
    print(f"Total tasks: {len(tasks)}")


if __name__ == "__main__":
    fix_urls()
