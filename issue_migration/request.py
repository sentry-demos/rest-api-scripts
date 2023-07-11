import requests
import os
from dotenv import load_dotenv

def request(url, method, payload = None):
    load_dotenv()
    try:
        token = os.environ["SAAS_AUTH_TOKEN"] if "sentry.io" in url else os.environ["ON_PREM_AUTH_TOKEN"]
        headers = {
                "Content-Type": "application/json",
            }
        if method == "GET":
            headers["Authorization"] = "Bearer " + token
            return requests.get(url, headers = headers)
        elif method == "POST":
            return requests.post(url, json = payload)
        elif method == "PUT":
            headers["Authorization"] = "Bearer " + token
            return requests.put(url, json = payload, headers = headers)
    except Exception as e:
        raise Exception(f'Could not make request to {url} - Reason: {str(e)}')
