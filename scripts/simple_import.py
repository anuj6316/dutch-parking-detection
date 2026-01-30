#!/usr/bin/env python3
"""
Simple Label Studio import using API
"""

import json
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

# Label Studio configuration
LABEL_STUDIO_URL = "http://localhost:8080"
USERNAME = "admin"
PASSWORD = "admin"
PROJECT_NAME = "Parking Dataset - 195 Tasks"


def create_project():
    """Create a new Label Studio project"""

    auth = HTTPBasicAuth(USERNAME, PASSWORD)

    # Read labeling config
    config_file = Path("scripts/labelstudio-config.xml")
    with open(config_file, "r") as f:
        labeling_config = f.read()

    # Create new project
    print(f"Creating new project: {PROJECT_NAME}")

    create_data = {
        "title": PROJECT_NAME,
        "description": "Parking detection dataset with 195 tasks and polygon annotations",
        "label_config": labeling_config,
    }

    response = requests.post(
        f"{LABEL_STUDIO_URL}/api/projects", auth=auth, json=create_data
    )

    if response.status_code == 201:
        project = response.json()
        print(f"✅ Project created successfully!")
        print(f"   Project ID: {project['id']}")
        print(f"   Project Title: {project['title']}")
        return project["id"]
    elif response.status_code == 200:
        projects = response.json()
        if isinstance(projects, list):
            # Check if project already exists
            for project in projects:
                # Get project details
                details = requests.get(
                    f"{LABEL_STUDIO_URL}/api/projects/{project}", auth=auth
                ).json()
                if details.get("title") == PROJECT_NAME:
                    print(f"✅ Project already exists!")
                    print(f"   Project ID: {details.get('id')}")
                    return details.get("id")
        print(f"❌ Could not find or create project")
        return None
    else:
        print(f"❌ Failed to create project")
        print(f"   Status code: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def import_tasks(project_id):
    """Import tasks into the project"""

    auth = HTTPBasicAuth(USERNAME, PASSWORD)

    # Read JSON tasks with relative URLs
    JSON_FILE = Path("scripts/labelstudio-import-relative.json")
    with open(JSON_FILE, "r") as f:
        tasks = json.load(f)

    print(f"\nImporting {len(tasks)} tasks into project {project_id}...")

    # Import tasks
    response = requests.post(
        f"{LABEL_STUDIO_URL}/api/projects/{project_id}/import",
        auth=auth,
        json=tasks,
        headers={"Content-Type": "application/json"},
    )

    if response.status_code in [200, 201]:
        result = response.json()
        print(f"✅ Tasks imported successfully!")
        if isinstance(result, dict) and "task_count" in result:
            print(f"   Tasks imported: {result['task_count']}")
        print(f"   Response: {result}")
    else:
        print(f"❌ Failed to import tasks")
        print(f"   Status code: {response.status_code}")
        print(f"   Response: {response.text}")


def main():
    print("=" * 60)
    print("Label Studio API Import")
    print("=" * 60)
    print(f"URL: {LABEL_STUDIO_URL}")

    # Create project
    project_id = create_project()

    if project_id:
        # Import tasks
        import_tasks(project_id)

        print("\n" + "=" * 60)
        print("Import complete!")
        print(f"Open Label Studio: {LABEL_STUDIO_URL}")
        print("=" * 60)
    else:
        print("\n❌ Could not create project. Please check Label Studio is running.")


if __name__ == "__main__":
    main()
