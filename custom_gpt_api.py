from flask import Flask, request, jsonify
import os
from PyPDF2 import PdfReader

app = Flask(__name__)

# Define your custom API key
CUSTOM_API_KEY = os.getenv( "CUSTOM_API_KEY")  # Use environment v

# Function to process user queries with CustomGPT logic
def custom_gpt(query):
    folder_path = "CustomGPT_files"  # Folder containing your PDFs
    response = "No relevant content found."

    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)

            try:
                reader = PdfReader(file_path)
                content = ""
                for page in reader.pages:
                    content += page.extract_text()

                if query.lower() in content.lower():
                    response = f"Found in {filename}: {content}"
                    break
            except Exception as e:
                response = f"Error reading {filename}: {e}"

    return response

# Define the API route with API key validation
@app.route('/chat', methods=['POST'])
def chat():
    # Validate the API key
    api_key = request.headers.get('Authorization')
    if api_key != CUSTOM_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401


    # Process the query if the API key is valid
    data = request.json
    user_message = data.get('message', '')
    gpt_response = custom_gpt(user_message)  # Call the CustomGPT logic
    return jsonify({"reply": gpt_response})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
