import requests

API_KEY = "4739f793-f138-4c67-97d2-7abbfc3fc556"
API_URL = "https://free.intelx.io/"

def start_search(term):
    headers = {"x-key": API_KEY}
    data = {
        "term": term,
        "maxresults": 100,
        "media": 0,
        "sort": 2,
        "terminate": []
    }
    try:
        response = requests.post(f"{API_URL}intelligent/search", headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json().get("id")
    except requests.exceptions.RequestException as e:
        print(f"Error starting search: {e}")
        return None

def get_search_results(search_id, limit=100):
    headers = {"x-key": API_KEY}
    params = {"id": search_id, "limit": limit}
    try:
        response = requests.get(f"{API_URL}intelligent/search/result", headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting search results: {e}")
        return None