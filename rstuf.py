import requests
import json
import configparser
import os

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'config.ini'))

RSTUF_API_BASE_URL = config.get("settings", "RSTUF_API_BASE_URL")
ARTIFACTS_ADD_URL = f"{RSTUF_API_BASE_URL}/artifacts"
ARTIFACTS_DELETE_URL = f"{RSTUF_API_BASE_URL}/artifacts/delete"

def send_add_requests(artifacts):
    payload = {"artifacts": []}

    for artifact in artifacts:
        payload["artifacts"].append({
            "info": {
                "length": artifact["length"],
                "hashes": {artifact["hash_algorithm"]: artifact["hash"]},
                "custom": {"key": "value"},
            },
            "path": artifact["path"],
        })

    response = requests.post(ARTIFACTS_ADD_URL, json=payload)
    if response.status_code == 202:
        task_id = json.loads(response.text).get("data", {}).get("task_id")
        print(f"Successfully submitted {len(artifacts)} artifacts to be added.(Task ID: {task_id})")
    else:
        print(f"Error adding artifacts: {response.status_code}, {response.text}")


def send_remove_requests(paths):
    payload = {"artifacts": paths}
    response = requests.post(ARTIFACTS_DELETE_URL, json=payload)

    if response.status_code == 202:
        task_id = json.loads(response.text).get("data", {}).get("task_id")
        print(f"Successfully submitted {len(paths)} artifacts to be removed. (Task ID: {task_id})")
    else:
        print(f"Error removing artifacts: {response.status_code}, {response.text}")
