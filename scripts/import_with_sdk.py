#!/usr/bin/env python3
"""
Import tasks to Label Studio using Python SDK
This approach handles images correctly by Label Studio
"""

import json
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

# Label Studio configuration
LABEL_STUDIO_URL = "http://172.16.20.161:8080"
USERNAME = "admin"
PASSWORD = "admin"
PROJECT_NAME = "Parking Dataset - 195 Tasks"
JSON_FILE = Path("scripts/labelstudio-import.json")


def create_project():
    """Create a new Label Studio project"""

    # First, get list of projects
    auth = HTTPBasicAuth(USERNAME, PASSWORD)

    # Get all projects
    response = requests.get(f"{LABEL_STUDIO_URL}/api/projects", auth=auth)
    projects = response.json()

    # Check if project already exists
    for project in projects:
        if project["title"] == PROJECT_NAME:
            print(f"Project already exists: {project['id']} - {project['title']}")
            return project["id"]

    # Create new project
    print(f"Creating new project: {PROJECT_NAME}")

    # Read labeling config
    config_file = Path("scripts/labelstudio-config.xml")
    with open(config_file, "r") as f:
        labeling_config = f.read()

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
    else:
        print(f"❌ Failed to create project")
        print(f"   Status code: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def import_tasks(project_id):
    """Import tasks into the project"""

    auth = HTTPBasicAuth(USERNAME, PASSWORD)

    # Read JSON tasks
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

    if response.status_code == 200 or response.status_code == 201:
        result = response.json()
        print(f"✅ Tasks imported successfully!")
        if "task_count" in result:
            print(f"   Tasks imported: {result['task_count']}")
        else:
            print(f"   Response: {result}")
    else:
        print(f"❌ Failed to import tasks")
        print(f"   Status code: {response.status_code}")
        print(f"   Response: {response.text}")


def main():
    print("=" * 60)
    print("Label Studio SDK Import")
    print("=" * 60)

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
