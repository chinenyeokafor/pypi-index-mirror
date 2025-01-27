import requests

RSTUF_API_BASE_URL = "https://repository-service-tuf.github.io/api/v1"
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
    if response.status_code == 200:
        print(f"Successfully added {len(artifacts)} artifacts.")
    else:
        print(f"Error adding artifacts: {response.status_code}, {response.text}")


def send_remove_requests(paths):
    payload = {"artifacts": paths}
    response = requests.post(ARTIFACTS_DELETE_URL, json=payload)

    if response.status_code == 200:
        print(f"Successfully removed {len(paths)} artifacts.")
    else:
        print(f"Error removing artifacts: {response.status_code}, {response.text}")
