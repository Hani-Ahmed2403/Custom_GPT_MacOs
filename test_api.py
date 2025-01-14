import requests

url = "http://127.0.0.1:5000/chat"
headers = {
    "Authorization": os.getenv("TEST_API_KEY"),  # Use environment variable
    "Content-Type": "application/json"
}
data = {"message": "search term"}

response = requests.post(url, headers=headers, json=data)
print(response.json())
