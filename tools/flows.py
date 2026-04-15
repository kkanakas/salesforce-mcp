import requests

import client
import config


def invoke_flow(flow_api_name: str, inputs: dict) -> dict:
    sf = client.get_client()
    url = f"{config.INSTANCE_URL}/services/data/v62.0/actions/custom/flow/{flow_api_name}"
    headers = {
        "Authorization": f"Bearer {sf.session_id}",
        "Content-Type": "application/json",
    }
    response = requests.post(url, json={"inputs": [inputs]}, headers=headers)
    response.raise_for_status()
    return response.json()
