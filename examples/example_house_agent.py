import requests

BASE_URL = "http://localhost:8000"

def get_health():
    response = requests.get(f"{BASE_URL}/health", timeout=10)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    print(get_health())
