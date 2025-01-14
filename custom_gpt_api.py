from flask import Flask, request, jsonify
import os
from PyPDF2 import PdfReader

app = Flask(__name__)

# Ensure the "CustomGPT_files" directory exists
if not os.path.exists("CustomGPT_files"):
    os.makedirs("CustomGPT_files")
    print("Created missing 'CustomGPT_files' directory.")

# Define your custom API key
CUSTOM_API_KEY = os.getenv("CUSTOM_API_KEY")  # Use environment variable for API key

# Function to process user queries with CustomGPT logic
def custom_gpt(query):
    folder_path = "CustomGPT_files"  # Folder containing your PDFs
    response = "No relevant content found."

    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            print(f"Processing file: {filename}")  # Debug: File being processed
            file_path = os.path.join(folder_path, filename)

            try:
                reader = PdfReader(file_path)
                content = ""
                for page in reader.pages:
                    extracted_text = page.extract_text()
                    content += extracted_text

                # Match query and return a snippet of the matching text
                if query.lower() in content.lower():
                    start_index = content.lower().find(query.lower())
                    snippet = content[start_index:start_index + 200]  # Return 200 characters around the match
                    response = f"Found in {filename}: {snippet}..."
                    break
            except Exception as e:
                response = f"Error reading {filename}: {e}"

    return response

# Root route
@app.route('/')
def home():
    return "Welcome to the Custom GPT API! Use /upload to upload files and /chat to query them."

# Define the API route with API key validation
@app.route('/chat', methods=['POST'])
def chat():
    # Validate the API key
    api_key = request.headers.get('Authorization')
    if api_key != CUSTOM_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    # Process the query
    data = request.json
    user_message = data.get('message', '')
    gpt_response = custom_gpt(user_message)  # Call the CustomGPT logic
    return jsonify({"reply": gpt_response})

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the file to the "CustomGPT_files" directory
    file.save(os.path.join("CustomGPT_files", file.filename))
    return jsonify({"message": f"Uploaded {file.filename} successfully"}), 200

@app.route('/list', methods=['GET'])
def list_files():
    files = os.listdir("CustomGPT_files")
    return jsonify({"files": files})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
