import requests

url = "https://custom-gpt-nfo8.onrender.com/chat"
headers = {
    "Authorization": "YOUR_API_KEY",  # Replace with your actual API key
    "Content-Type": "application/json"
}
data = {"message": "search term"}  # Replace with your query

response = requests.post(url, headers=headers, json=data)
print(response.json())
